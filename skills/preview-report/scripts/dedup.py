"""フレーム間引き（ピクセル差分 dedup）。

crv (claude-real-video) の頭脳だけを移植したもの。板書スクショの列から
「視覚的に新しいフレーム」だけを残す。知覚ハッシュではなく、ダウンスケール
RGB の実ピクセル差分でフレームを比較する（べた塗り・明度だけの変化に強い）。
比較は直近 window 枚の採用フレームに対して行うので、A-B-A の往復
（人物が横切って元の板書に戻る）でも同じ板書を二重採用しない。

用途は2つ:
  1. cdp_seek.split_and_capture_adaptive が「板書が動いた谷間」を判定する頭脳。
  2. 撮り終えたフレームフォルダの後処理（静止区間の重複を _dup/ へ退避）。

削除はしない。重複は out_dir/_dup/ へ移動する（非破壊・元に戻せる）。
PIL が無い環境ではフレームをそのまま素通しする（クラッシュしない）。
"""
from __future__ import annotations
import argparse
import glob
import os
import shutil
import sys
from io import BytesIO
from pathlib import Path

try:
    import numpy as np
except ImportError:  # numpy はこの環境では入っている想定。無ければ pct_diff で明示エラー。
    np = None

# crv 準拠のデフォルト。size=16 の 16x16 に潰し、tol を超える色差の画素割合を diff とする。
SIZE = 16
TOL = 25            # 1画素が「変わった」とみなす色差（チャンネル最大差）
THRESHOLD = 8.0     # この% を超えて画素が変われば「新しいフレーム」= 採用
WINDOW = 4          # 直近何枚の採用フレームと比べるか
MAX_FRAMES = 150    # dedup 後の上限。超えたら時間軸で均等間引き
EXTS = ("png", "jpg", "jpeg")


def _load_rgb(img_source, size: int = SIZE):
    """path でも bytes でも受け取り、(size,size,3) の int16 配列を返す。
    PIL 不在なら None。"""
    try:
        from PIL import Image
    except ImportError:
        return None
    if isinstance(img_source, (bytes, bytearray)):
        im = Image.open(BytesIO(img_source))
    else:
        im = Image.open(img_source)
    im = im.convert("RGB").resize((size, size))
    if np is not None:
        return np.asarray(im, dtype=np.int16)
    # numpy 無しフォールバック（遅いが動く）: ネストした list
    px = list(im.getdata())
    return [px[r * size:(r + 1) * size] for r in range(size)]


def frame_sig(path: str, size: int = SIZE):
    """PNG/JPG のパスからダウンスケール RGB 署名を作る。PIL 不在なら None。"""
    return _load_rgb(path, size)


def frame_sig_from_bytes(data: bytes, size: int = SIZE):
    """CDP の captureScreenshot が返す PNG バイト列から署名を作る（ディスク往復不要）。"""
    return _load_rgb(data, size)


def pct_diff(a, b, tol: int = TOL) -> float:
    """2署名間で、色差（RGBチャンネルの最大絶対差）が tol を超える画素の割合(%)。
    a,b が None（PIL不在）なら 100.0（=常に別物扱い）で安全側に倒す。"""
    if a is None or b is None:
        return 100.0
    if np is not None:
        changed = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2) > tol
        return 100.0 * float(changed.mean())
    # numpy 無しフォールバック
    total = 0
    changed = 0
    for ra, rb in zip(a, b):
        for pa, pb in zip(ra, rb):
            total += 1
            if max(abs(pa[0] - pb[0]), abs(pa[1] - pb[1]), abs(pa[2] - pb[2])) > tol:
                changed += 1
    return 100.0 * changed / total if total else 0.0


def dedup_dir(frames_dir: str, threshold: float = THRESHOLD, window: int = WINDOW,
              max_frames: int = MAX_FRAMES, exts=EXTS, tol: int = TOL,
              dry_run: bool = False, dup_subdir: str = "_dup") -> dict:
    """frames_dir の画像を時系列（ファイル名昇順）で走査し、直近 window 枚の採用
    フレームに対して threshold% 以上変化したものだけ残す。重複は dup_subdir/ へ移動。

    フレーム名は秒数を含む（例 at00123s.png / split10_03_of_10_at0456s.png）ので、
    ファイル名昇順 ≒ 時間昇順。リネームはしない（時刻情報を保つ）。

    返り値: {kept:[...], dropped:[...], records:[...], pil: bool}
    """
    files = []
    for e in exts:
        files.extend(glob.glob(os.path.join(frames_dir, f"*.{e}")))
    files = sorted(set(files))

    try:
        from PIL import Image  # noqa: F401
        pil_ok = True
    except ImportError:
        pil_ok = False
    if not pil_ok or not files:
        # 判定できない → 全部そのまま残す（安全側）
        return {"kept": files, "dropped": [], "records": [], "pil": pil_ok}

    kept: list[str] = []
    recent: list = []      # 直近 window 枚の署名
    records: list[dict] = []
    dup_dir = os.path.join(frames_dir, dup_subdir)

    for f in files:
        sig = frame_sig(f)
        dist = min((pct_diff(sig, k, tol) for k in recent), default=None)
        is_new = dist is None or dist > threshold
        rec = {"name": os.path.basename(f), "dist": None if dist is None else round(dist, 2),
               "kept": is_new}
        if is_new:
            kept.append(f)
            recent.append(sig)
            if len(recent) > window:
                recent.pop(0)
        else:
            if not dry_run:
                os.makedirs(dup_dir, exist_ok=True)
                shutil.move(f, os.path.join(dup_dir, os.path.basename(f)))
        records.append(rec)

    dropped = [r["name"] for r in records if not r["kept"]]

    # 上限超過なら dedup 後に時間軸で均等間引き（生存フレームを動画全体に散らす）
    if len(kept) > max_frames:
        step = len(kept) / max_frames
        keep_idx = {int(i * step) for i in range(max_frames)}
        survivors = []
        for i, f in enumerate(kept):
            if i in keep_idx:
                survivors.append(f)
            else:
                if not dry_run:
                    os.makedirs(dup_dir, exist_ok=True)
                    shutil.move(f, os.path.join(dup_dir, os.path.basename(f)))
                dropped.append(os.path.basename(f))
                for r in records:
                    if r["name"] == os.path.basename(f):
                        r["kept"] = False
                        r["capped"] = True
        kept = survivors

    return {"kept": kept, "dropped": dropped, "records": records, "pil": True}


def _main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="dedup.py",
        description="フレームフォルダから重複板書を _dup/ へ退避する（crvピクセル差分）")
    ap.add_argument("frames_dir", help="*.png/*.jpg の入ったフォルダ")
    ap.add_argument("--threshold", type=float, default=THRESHOLD,
                    help=f"新フレーム採用の変化率%% (既定 {THRESHOLD})")
    ap.add_argument("--window", type=int, default=WINDOW,
                    help=f"直近何枚と比較するか (既定 {WINDOW})")
    ap.add_argument("--max-frames", type=int, default=MAX_FRAMES,
                    help=f"dedup 後の上限枚数 (既定 {MAX_FRAMES})")
    ap.add_argument("--tol", type=int, default=TOL, help=f"画素変化の色差閾値 (既定 {TOL})")
    ap.add_argument("--dry-run", action="store_true", help="移動せず結果だけ表示")
    a = ap.parse_args(argv)

    d = os.path.abspath(a.frames_dir)
    if not os.path.isdir(d):
        print(f"[!] not a directory: {d}", file=sys.stderr)
        return 2
    res = dedup_dir(d, threshold=a.threshold, window=a.window,
                    max_frames=a.max_frames, tol=a.tol, dry_run=a.dry_run)
    if not res["pil"]:
        print("[!] PIL 不在: 間引きせず全フレームを残しました")
        return 0
    tag = "(dry-run) " if a.dry_run else ""
    print(f"{tag}kept {len(res['kept'])} / dropped {len(res['dropped'])}  in {d}")
    for r in res["records"]:
        mark = "keep" if r["kept"] else ("CAP " if r.get("capped") else "dup ")
        print(f"  {mark} {r['name']}  dist={r['dist']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

"""OneDrive ファイルロック回避付きの保存パス決定（shared-doc-rules §3）＋命名規則の検査（§1）。

Word/Excel で開かれたファイルへの上書きは PermissionError になるため、
ロック時はバージョン番号を +1 した別名を返す。
使い方: from safe_save_path import safe_save_path / またはロジックを転記。

命名規則（§1）に反する名前は、保存先を決める前に ValueError で止める:
  - ファイル名に「最終版」「完成版」「final」（大文字小文字は問わない）が入っている
  - 拡張子の前が `_v{N}`（時刻付きなら `_v{N}_HHMMSS`）で終わっていない
  ただし環境変数 SAFE_SAVE_EXEMPT_DIRS に書いたフォルダ（チームの共有フォルダなど、
  別の命名規則に従う場所）の配下は検査しない。フォルダ名の一部を「;」区切りで書く。
検査だけしたいときは check_file_name(path) を呼ぶ（問題なければ何も返さない）。
"""
import os
import re

# §1 の共有フォルダの例外。環境変数 SAFE_SAVE_EXEMPT_DIRS にフォルダ名の一部を「;」区切りで書く
# （例: "サークル共有;ゼミ共有"）。フォルダ名の一部で判定する（区切り文字の違いに左右されない）。既定は例外なし
EXEMPT_ENV = "SAFE_SAVE_EXEMPT_DIRS"


def exempt_marks():
    """命名規則を検査しないフォルダ名（の一部）のリストを返す。"""
    raw = os.environ.get(EXEMPT_ENV, "")
    marks = []
    for m in raw.split(";"):
        m = m.strip()
        if m:
            marks.append(m)
    return marks

# 「final」は英単語として入っている時だけ（finally / finals などは別の語なので拾わない）
FORBIDDEN = re.compile(r"最終版|完成版|(?<![A-Za-z])final(?![A-Za-z])", re.IGNORECASE)

# 拡張子を除いた名前の末尾。時刻（OneDriveロック回避用）は版の後ろに付く（§1 タイムスタンプ）
VERSION_TAIL = re.compile(r"_v(\d+)(_\d{6})?$")


def check_file_name(path: str) -> None:
    """命名規則に反していたら ValueError を投げる。例外に登録したフォルダの配下は検査しない。"""
    for mark in exempt_marks():
        if mark in path:
            return
    stem = os.path.splitext(os.path.basename(path))[0]
    m = FORBIDDEN.search(stem)
    if m:
        raise ValueError(
            f"ファイル名に「{m.group(0)}」が入っている: {os.path.basename(path)}"
            "（shared-doc-rules §1: 最終版・完成版・final は使わず _v{N} で版を上げる）")
    if not VERSION_TAIL.search(stem):
        raise ValueError(
            f"ファイル名が _v{{N}} で終わっていない: {os.path.basename(path)}"
            "（shared-doc-rules §1: {種別}_{タイトル}_v{N}.{拡張子}。例: 企画書_ハッカソン2026_v1.docx）")


def safe_save_path(base_path: str) -> str:
    """ロック回避付きの保存パスを返す（先に命名規則を検査する）"""
    check_file_name(base_path)

    if not os.path.exists(base_path):
        return base_path

    # 書き込みテスト
    try:
        with open(base_path, "a"):
            pass
        return base_path
    except PermissionError:
        # 既存のバージョン番号を検出してインクリメント（時刻が付いていたら外す）
        name, ext = os.path.splitext(base_path)
        match = VERSION_TAIL.search(name)
        if match:
            current_v = int(match.group(1))
            name = name[: match.start()]
        else:
            # 例外フォルダの配下は版の無い名前もある
            current_v = 0

        for v in range(current_v + 1, current_v + 100):
            new_path = f"{name}_v{v}{ext}"
            if not os.path.exists(new_path):
                return new_path

        raise RuntimeError("バージョン番号の上限に達しました")

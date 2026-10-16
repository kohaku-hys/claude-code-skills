# -*- coding: utf-8 -*-
"""ローカル Whisper（faster-whisper）で音声を文字起こしする。APIキー不要・ネット不要。

usage: py transcribe_local.py <音声ファイル> <出力txt> [--model large-v3] [--cpu] [--prompt "授業名・用語"]

- 既定は GPU（CUDA, float16）。GPU が使えなければ CPU（int8）に自動で落とす
- CUDA の DLL は pip の nvidia-cublas-cu12 / nvidia-cudnn-cu12 から読む（Windows）
  GPU メモリ 6GB で large-v3 が載った（作者の環境）
- 出力は 1 行 1 区間で「[mm:ss] 本文」。transcribe_audio.py が Groq で失敗した時もこれを呼ぶ
- 初回はモデル（large-v3 は約3GB）を Hugging Face から落とす（~/.cache/huggingface）
- 要るもの: pip の faster-whisper
"""
import argparse
import os
import sys
from pathlib import Path


def _add_cuda_dlls():
    """pip で入れた NVIDIA の DLL を読めるようにする（Windows）"""
    try:
        import nvidia
    except ImportError:
        return
    root = Path(nvidia.__path__[0])
    for b in root.glob("*/bin"):
        os.add_dll_directory(str(b))
        os.environ["PATH"] = str(b) + os.pathsep + os.environ.get("PATH", "")


def load_model(model="large-v3", cpu=False):
    _add_cuda_dlls()
    from faster_whisper import WhisperModel
    if not cpu:
        try:
            m = WhisperModel(model, device="cuda", compute_type="float16")
            print(f"GPU で読み込み: {model}", flush=True)
            return m
        except Exception as e:
            print(f"GPU が使えないので CPU にする: {e}", flush=True)
    return WhisperModel(model, device="cpu", compute_type="int8")


def transcribe(audio, out, model="large-v3", cpu=False, prompt=None):
    m = load_model(model, cpu)
    segs, info = m.transcribe(str(audio), language="ja", vad_filter=True, beam_size=5,
                              initial_prompt=prompt)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out, "w", encoding="utf-8") as f:
        for s in segs:
            t = int(s.start)
            f.write(f"[{t // 60:02d}:{t % 60:02d}] {s.text.strip()}\n")
            n += 1
            if n % 50 == 0:
                print(f"  {t // 60}分まで", flush=True)
    print(f"文字起こし完了: {out}（{n}区間）", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("out")
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--prompt", default=None, help="固有名詞などのヒント（授業名・用語）")
    a = ap.parse_args()
    transcribe(a.audio, a.out, a.model, a.cpu, a.prompt)

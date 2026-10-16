"""
MP3 文字起こしスクリプト (Groq API)
usage: py transcribe_audio.py <mp3_path> <output_txt_path>

- Groq Whisper API を使用（高速・無料枠あり）
- 25MB超のファイルは自動的にチャンク分割して処理
- APIキーは環境変数 GROQ_API_KEY。無ければ .env から読む（探す順は下の「.env読み込み」）
- Groq が使えない時（キー未設定・期限切れ・通信不可）は transcribe_local.py（ローカル Whisper）に切り替える
- 要るもの: pip の groq・python-dotenv・pydub、ffmpeg（Python 3.13 以降は pydub 用に audioop-lts も）
"""

import math
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

# ffmpegのパスを明示的に設定（wingetインストール先）
_ffmpeg_dir = os.environ.get("FFMPEG_DIR", "")
if not _ffmpeg_dir:
    _localappdata = os.environ.get("LOCALAPPDATA", "")
    if _localappdata:
        matches = list(Path(_localappdata).glob(
            "Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg-*-full_build/bin",
        ))
        _ffmpeg_dir = str(matches[0]) if matches else ""

if _ffmpeg_dir and Path(_ffmpeg_dir).exists():
    os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ["PATH"]

from pydub import AudioSegment  # noqa: E402 (ffmpegパス設定後にimport)

# .env読み込み。環境変数 GROQ_API_KEY が既にあればそれを使う（load_dotenv は上書きしない）。探す順:
#   1. 環境変数 CLAUDE_WORKSPACE のフォルダの .env（ワークスペースの .env）
#   2. このスクリプトと同じフォルダの .env
_workspace = os.environ.get("CLAUDE_WORKSPACE", "")
if _workspace:
    load_dotenv(Path(_workspace) / ".env")
load_dotenv(Path(__file__).parent / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # 無ければ None
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "whisper-large-v3")
MAX_FILE_SIZE: int = 24 * 1024 * 1024  # 24MB（余裕を持たせる）
CHUNK_DURATION_MS: int = 10 * 60 * 1000  # 10分ごとに分割


def split_audio(mp3_path: str) -> list[str]:
    """大きなMP3ファイルをチャンクに分割する"""
    audio = AudioSegment.from_file(mp3_path)
    duration_ms = len(audio)
    num_chunks = math.ceil(duration_ms / CHUNK_DURATION_MS)

    if num_chunks <= 1:
        return [mp3_path]

    print(f"ファイルを {num_chunks} チャンクに分割中...")
    chunk_paths: list[str] = []
    temp_dir = tempfile.mkdtemp(prefix="transcribe_")

    for i in range(num_chunks):
        start = i * CHUNK_DURATION_MS
        end = min((i + 1) * CHUNK_DURATION_MS, duration_ms)
        chunk = audio[start:end]
        chunk_path = os.path.join(temp_dir, f"chunk_{i:03d}.mp3")
        chunk.export(chunk_path, format="mp3")
        chunk_paths.append(chunk_path)
        print(f"  チャンク {i + 1}/{num_chunks} 作成完了")

    return chunk_paths


def transcribe_chunk(client: Groq, chunk_path: str, chunk_num: int, total: int) -> str:
    """1チャンクをGroq APIで文字起こし"""
    print(f"  文字起こし中 [{chunk_num}/{total}]: {os.path.basename(chunk_path)}")
    with open(chunk_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(chunk_path), f.read()),
            model=WHISPER_MODEL,
            language="ja",
            response_format="text",
        )
    return transcription


def transcribe(mp3_path: str, output_path: str) -> None:
    """MP3ファイルを文字起こしして結果をファイルに保存する"""
    if not GROQ_API_KEY:
        print("エラー: GROQ_API_KEY が設定されていません")
        print("環境変数 GROQ_API_KEY か、ワークスペースの .env（CLAUDE_WORKSPACE）に GROQ_API_KEY を設定してください")
        sys.exit(1)

    client = Groq(api_key=GROQ_API_KEY)
    file_size = os.path.getsize(mp3_path)
    print(f"ファイルサイズ: {file_size / (1024 * 1024):.1f} MB")

    # ファイルサイズに応じて分割判定
    if file_size > MAX_FILE_SIZE:
        chunk_paths = split_audio(mp3_path)
        is_chunked = True
    else:
        chunk_paths = [mp3_path]
        is_chunked = False

    print("Groq Whisper API で文字起こし開始...")
    temp_dir = os.path.dirname(chunk_paths[0]) if is_chunked else None
    try:
        texts = []
        for i, chunk_path in enumerate(chunk_paths):
            text = transcribe_chunk(client, chunk_path, i + 1, len(chunk_paths))
            texts.append(text)
    finally:
        # チャンクの一時ファイルを確実に削除
        if is_chunked and temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
            print("一時ファイルを削除しました")

    full_text = "\n".join(texts)

    # 出力先ディレクトリがなければ作成
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"文字起こし完了: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: py transcribe_audio.py <mp3_path> <output_txt_path>")
        sys.exit(1)

    mp3_path = sys.argv[1]
    output_path = sys.argv[2]

    if not os.path.exists(mp3_path):
        print(f"エラー: ファイルが見つかりません: {mp3_path}")
        sys.exit(1)

    try:
        try:
            transcribe(mp3_path, output_path)
        except (SystemExit, Exception) as e:
            # Groq が使えない（キー未設定・期限切れ・通信不可）時はローカル Whisper に切り替える
            if isinstance(e, SystemExit) and e.code == 0:
                raise
            print(f"Groq で失敗したのでローカル Whisper に切り替えます: {e}")
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import transcribe_local
            transcribe_local.transcribe(mp3_path, output_path)
    except FileNotFoundError as e:
        print(f"エラー: ファイルが見つかりません: {e}")
        sys.exit(1)
    except PermissionError as e:
        print(f"エラー: 権限エラー: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"エラー: {e}")
        traceback.print_exc()
        sys.exit(1)

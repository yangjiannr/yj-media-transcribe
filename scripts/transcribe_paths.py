# -*- coding: utf-8 -*-
"""Batch-transcribe arbitrary media files (not only creator_root/videos/).

Examples:
  python transcribe_paths.py --input clip.mp4
  python transcribe_paths.py --input ./clips --out-dir ./transcripts
  python transcribe_paths.py --input a.mp4 b.wav c.m4a --engine funasr
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

MEDIA_EXTS = {
    ".mp4", ".mkv", ".mov", ".webm", ".avi", ".flv", ".m4v",
    ".wav", ".mp3", ".m4a", ".flac", ".aac", ".ogg", ".wma",
}


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def collect_inputs(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            for child in sorted(p.rglob("*")):
                if child.is_file() and child.suffix.lower() in MEDIA_EXTS:
                    out.append(child)
        elif p.is_file():
            if p.suffix.lower() not in MEDIA_EXTS:
                print(f"[{now()}] SKIP unsupported ext: {p}", file=sys.stderr)
                continue
            out.append(p)
        else:
            print(f"[{now()}] SKIP missing: {p}", file=sys.stderr)
    # de-dupe preserving order
    seen = set()
    uniq = []
    for p in out:
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)
    return uniq


def load_optional_config(path: Path | None) -> dict:
    if not path or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Batch ASR for arbitrary media paths")
    ap.add_argument("--input", nargs="+", required=True, help="files and/or directories")
    ap.add_argument("--out-dir", default="", help="output dir for .txt/.srt (default: beside each file)")
    ap.add_argument("--engine", default="", choices=["", "auto", "funasr", "whisper"])
    ap.add_argument("--whisper-model", default="")
    ap.add_argument("--asr-python", default="", help="python with FunASR/whisper; default=sys.executable")
    ap.add_argument("--ffmpeg-bin", default="", help="directory containing ffmpeg.exe to prepend to PATH")
    ap.add_argument("--config", default="", help="optional JSON (pipeline_config.json keys ok)")
    ap.add_argument("--skip-existing", action="store_true", default=True)
    ap.add_argument("--no-skip-existing", action="store_false", dest="skip_existing")
    ap.add_argument("--hf-endpoint", default="")
    ap.add_argument("--work-dir", default="")
    args = ap.parse_args()

    cfg = load_optional_config(Path(args.config) if args.config else None)
    engine = args.engine or cfg.get("asr_engine") or "auto"
    whisper_model = args.whisper_model or cfg.get("whisper_model") or "medium"
    asr_python = args.asr_python or cfg.get("asr_python") or sys.executable
    ffmpeg_bin = args.ffmpeg_bin or cfg.get("ffmpeg_bin") or ""
    hf_endpoint = args.hf_endpoint or cfg.get("hf_endpoint") or ""
    hf_disable_xet = cfg.get("hf_hub_disable_xet", True)

    if ffmpeg_bin and ffmpeg_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_bin + os.pathsep + os.environ.get("PATH", "")

    transcribe_py = Path(__file__).with_name("transcribe_one.py")
    if not transcribe_py.exists():
        print(f"transcribe_one.py missing next to {__file__}", file=sys.stderr)
        return 2

    media_list = collect_inputs([Path(p) for p in args.input])
    if not media_list:
        print("no media files found", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    work = Path(args.work_dir) if args.work_dir else Path(tempfile.mkdtemp(prefix="asr_batch_"))
    work.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    if hf_endpoint:
        env["HF_ENDPOINT"] = hf_endpoint
    if hf_disable_xet:
        env["HF_HUB_DISABLE_XET"] = "1"

    ok_n = fail_n = skip_n = 0
    print(f"[{now()}] batch start: n={len(media_list)} engine={engine}/{whisper_model}")

    for media in media_list:
        if out_dir:
            txt = out_dir / f"{media.stem}.txt"
            srt = out_dir / f"{media.stem}.srt"
        else:
            txt = media.with_suffix(".txt")
            srt = media.with_suffix(".srt")

        if args.skip_existing and txt.exists() and srt.exists() and txt.stat().st_size > 0 and srt.stat().st_size > 0:
            skip_n += 1
            safe = media.name.encode("ascii", "backslashreplace").decode("ascii")
            print(f"[{now()}] SKIP {safe}")
            continue

        cmd = [
            asr_python,
            str(transcribe_py),
            "--media", str(media),
            "--txt", str(txt),
            "--srt", str(srt),
            "--engine", engine,
            "--whisper-model", whisper_model,
            "--work-dir", str(work),
        ]
        safe = media.name.encode("ascii", "backslashreplace").decode("ascii")
        print(f"[{now()}] ASR {safe}")
        try:
            p = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=7200, env=env,
            )
            out = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
            parsed = None
            for line in reversed(out.splitlines()):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        parsed = json.loads(line)
                        break
                    except Exception:
                        pass
            if parsed and parsed.get("ok"):
                ok_n += 1
                print(f"[{now()}] OK {safe} engine={parsed.get('engine')} segments={parsed.get('segments')}")
            elif parsed and parsed.get("no_speech"):
                fail_n += 1
                print(f"[{now()}] NO_SPEECH {safe}")
            else:
                fail_n += 1
                detail = (parsed or {}).get("error") if parsed else out[-400:]
                print(f"[{now()}] FAIL {safe} {detail}")
        except Exception as e:
            fail_n += 1
            print(f"[{now()}] FAIL {safe} {e}")

    print(f"[{now()}] batch end: ok={ok_n} fail={fail_n} skip={skip_n}")
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

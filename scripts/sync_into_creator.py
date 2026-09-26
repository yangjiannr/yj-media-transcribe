# -*- coding: utf-8 -*-
"""Copy canonical ASR scripts from this skill into a creator_root/scripts/."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

FILES = ("transcribe_one.py", "asr_ordered.py", "transcribe_paths.py")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--creator-root", required=True)
    args = ap.parse_args()

    src_dir = Path(__file__).resolve().parent
    dest = Path(args.creator_root) / "scripts"
    dest.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        src = src_dir / name
        if not src.exists():
            print(f"missing {src}")
            return 2
        shutil.copy2(src, dest / name)
        print(f"copied {name} -> {dest / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

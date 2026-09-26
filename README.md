# yj-media-transcribe

音视频 → `.txt` + `.srt`（FunASR 优先，Whisper 兜底）。

从 `yj-douyin-creator-pipeline` / `yj-xhs-creator-pipeline` 抽出的**唯一** ASR 实现源。抓取/下载仍在各自 pipeline。

```text
media files / creator videos/
        │
        ▼
transcribe_one.py  (single)
transcribe_paths.py  (arbitrary batch)
asr_ordered.py  (creator_root + backpressure)
        │
        ▼
*.txt + *.srt
```

## Install

```bash
npx skills add https://github.com/yangjiannr/yj-media-transcribe --skill yj-media-transcribe
```

Or copy this folder into your agent's skills directory.

## Quick start

```text
# 任意文件
python scripts/transcribe_paths.py --input clip.mp4 --out-dir ./transcripts

# creator 目录（与抖音/小红书 pipeline 约定相同）
python scripts/sync_into_creator.py --creator-root F:/downloads/<博主名>
python scripts/asr_ordered.py --creator-root F:/downloads/<博主名>
```

## Layout

```text
yj-media-transcribe/
├── SKILL.md
├── config.example.json
├── references/asr.md
└── scripts/
    ├── transcribe_one.py
    ├── transcribe_paths.py
    ├── asr_ordered.py
    └── sync_into_creator.py
```

Sibling: `yj-edu-transcript-to-skills` consumes finished transcripts; it does not run ASR.  
Pipelines that call this skill: `yj-douyin-creator-pipeline`, `yj-xhs-creator-pipeline`.

## License

MIT for this skill text and scripts. Media you transcribe remains under your own rights / platform ToS.

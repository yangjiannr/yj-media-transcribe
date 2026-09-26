---
name: yj-media-transcribe
description: >-
  Transcribe audio/video to .txt + timed .srt via FunASR (primary) or Whisper
  (fallback). Use whenever the user asks to 转写/ASR/字幕/口播转文字、音视频转 txt、
  FunASR、Whisper、transcribe mp4/wav/mp3, or only needs ASR on existing media —
  including a creator folder videos/→transcripts/ OR arbitrary files/folders.
  For Douyin/XHS crawl+download+transcribe end-to-end, prefer
  yj-douyin-creator-pipeline / yj-xhs-creator-pipeline (they call this skill for ASR).
---

# yj-media-transcribe

把音视频转成**纯文本 `.txt` + 带时间轴 `.srt`**。不负责抓取/下载；抖音/小红书全链路请用对应 pipeline skill，它们的转写步骤应调用本 skill。

## Modes

| 模式 | 用户给什么 | 做什么 |
|------|------------|--------|
| `creator` | 已有 `<creator_root>/`（含 `videos/`） | `asr_ordered.py`：mtime 顺序 + 背压 + `asr.lock` → `transcripts/` |
| `paths` | 单个/多个文件，或任意目录 | `transcribe_paths.py` / `transcribe_one.py` → 旁路或 `--out-dir` |
| `one` | 一个文件 + 明确输出路径 | `transcribe_one.py --media … --txt … --srt …` |

## Always do first

1. Read `references/asr.md`（引擎选择、时间轴、无口播检测、HF 镜像）。
2. Confirm input mode (`creator` / `paths` / `one`).
3. Confirm FFmpeg on PATH（或 config 里的 `ffmpeg_bin`）与 ASR Python（FunASR venv 优先）。
4. Before bulk, offer a **quality preview**: 转 1–3 个最短文件，让用户看 `.txt`/`.srt` 再全量。
5. Do not claim done until outputs exist and（creator 模式）未转写队列清空或用户叫停。

## Defaults

Copy `config.example.json` keys into `<creator_root>/pipeline_config.json` or pass CLI flags.

| Key | Typical |
|-----|---------|
| `asr_engine` | `auto`（FunASR → Whisper） |
| `whisper_model` | `medium` |
| `ffmpeg_bin` | 本机 FFmpeg `bin` |
| `asr_python` | FunASR venv 的 `python.exe` |
| `hf_endpoint` | `https://hf-mirror.com` |
| `hf_hub_disable_xet` | `true` |

Why FunASR first: Chinese 口播通常更准。Whisper 适合英文 / 中英混杂。两条路径都要保留。

## Scripts

| Script | Role |
|--------|------|
| `scripts/transcribe_one.py` | 单文件 → txt+srt（`--media` / `--video`） |
| `scripts/transcribe_paths.py` | 任意文件/目录批量 |
| `scripts/asr_ordered.py` | creator 布局：下载完成顺序 + 背压，可与下载进程并行 |
| `scripts/sync_into_creator.py` | 把本 skill 的 ASR 脚本拷进 `<creator_root>/scripts/` |

Prefer these over ad-hoc one-offs. When a creator pipeline deploys scripts, **copy from this skill**（overwrite `transcribe_one.py` / `asr_ordered.py`）.

## Workflow — creator folder

Layout expected:

```text
<creator_root>/
  videos/*.mp4
  transcripts/     # same stem .txt + .srt
  logs/            # asr.lock, transcript_success/failed.log
  work/
  scripts/
  pipeline_config.json
```

```text
# deploy ASR scripts from this skill
python <skill>/scripts/sync_into_creator.py --creator-root <path>

# preview one short
python scripts/transcribe_one.py --media videos/<short>.mp4 \
  --txt transcripts/<stem>.txt --srt transcripts/<stem>.srt --engine funasr

# full ordered worker (parallel with downloader OK)
python scripts/asr_ordered.py --creator-root <path>
# 中断收尾：--min-downloaded 0 --pause-remaining 0
```

## Workflow — arbitrary paths

```text
# one file → beside it
python scripts/transcribe_paths.py --input D:/clips/talk.mp4

# folder → dedicated out dir
python scripts/transcribe_paths.py --input D:/clips --out-dir D:/clips/transcripts

# mix + config
python scripts/transcribe_paths.py --input a.wav b.mp4 --out-dir ./out \
  --config path/to/pipeline_config.json --engine auto
```

Supported extensions: mp4/mkv/mov/webm/avi + wav/mp3/m4a/flac/aac/ogg（见 `transcribe_paths.py`）。

## Transcription rules

- Prefer FunASR; on failure/unavailable → Whisper.
- FunASR **must** use `sentence_timestamp=True` so SRT has real cues（见 `references/asr.md`）.
- Reject “success” if a multi-minute file yields a single ~1s SRT cue.
- Skip if both txt+srt already exist and non-empty（除非用户要求重转）.
- `no_speech`（纯配乐/无口播）记失败日志但属预期，不是环境坏了。
- Windows 控制台打印文件名要 ascii-safe（emoji 文件名会 GBK 崩掉整条批量）.

## Progress reporting

Report: pending/done counts、recent FAIL / no_speech、lock PID、当前文件 `size_mb=`。  
结果打开 `transcripts/` 或 `--out-dir`。

## Relation to other skills

| Skill | Boundary |
|-------|----------|
| `yj-douyin-creator-pipeline` | 抓取 + 下载；转写 → **本 skill** |
| `yj-xhs-creator-pipeline` | 同上（小红书） |
| `yj-edu-transcript-to-skills` | 吃现成 `transcripts/` 蒸馏 skill；**不**读视频 |

## Safety

个人学习用途；勿对无权处理的媒体做批量转写。模型首次下载体积大（ModelScope / HF），确认磁盘与网络即可。

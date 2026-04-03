---
name: content-extractor
description: Multi-modal content extraction — video transcription, image OCR, article cleaning, gallery synthesis. Read this to know WHEN and HOW to use content-extractor.
---

# Content Extractor

Multi-modal content extraction engine. Converts raw multimedia from content-downloader into structured text for downstream rewriting and analysis.

## When to Use

Use `content-extractor` when the user has **downloaded content directories** and wants to **extract text/meaning**.

| User says | Action |
|-----------|--------|
| "这个视频说了什么" / "transcribe this content" | `content-extractor extract <dir>` |
| "提取这批内容" / "extract all of these" | `content-extractor extract-batch <parent-dir>` |
| "把这个 mp4 转文字" (bare file) | `content-extractor extract ./video.mp4` |

## When NOT to Use

| User wants | Use instead |
|------------|-------------|
| Download a video from URL | `content-downloader` |
| Quick video-only transcription | `videocut transcribe` (faster, no analysis) |
| Rewrite content for a platform | `content-rewriter` |
| Edit a video | `videocut` |

## Input

Accepts two input types:

### 1. Content directory (from content-downloader)

```bash
content-extractor extract ./output/douyin/user/video123/
```

Must contain `content_item.json` with `content_type` field that routes to the correct adapter.

### 2. Bare media file (auto-wrapped)

```bash
content-extractor extract ./my-video.mp4
```

Supported: `.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`, `.flv`, `.m4v`, `.mp3`, `.wav`, `.m4a`, `.aac`, `.ogg`, `.flac`

Auto-creates a temporary wrapper directory with synthetic `content_item.json`.

## Output

Five files per extracted item:

| File | Description |
|------|-------------|
| `transcript.json` | Timestamped transcription with per-segment confidence |
| `analysis.json` | Topics, viewpoints, sentiment, takeaways |
| `structured_text.md` | Human-readable research brief |
| `extractor_output.json` | Rewriter-compatible handoff format |
| `extraction_status.json` | Degradation signaling (ok/degraded per component) |

The `extractor_output.json` is the handoff contract consumed by `content-rewriter`.

## CLI Reference

```bash
# Extract single content directory or bare file
content-extractor extract <path> [OPTIONS]

# Batch extract all subdirectories
content-extractor extract-batch <parent-dir> [OPTIONS]
```

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--whisper-model` | `turbo` | Whisper model size (tiny/base/small/medium/large/turbo) |
| `--force` | False | Re-extract already processed items |

## Architecture

```
Input (ContentItem dir or bare file)
  → Loader (validate content_item.json)
    → Router (content_type → adapter)
      → Adapter.extract()
        ├── VideoExtractor: FFmpeg → faster-whisper → hallucination check
        ├── ImageExtractor: Claude vision (OCR + description)
        ├── ArticleExtractor: trafilatura HTML → Markdown
        └── GalleryExtractor: per-image Claude vision → narrative synthesis
      → LLM Analysis (topics, viewpoints, sentiment, takeaways)
        → Atomic Output Writer (5 files)
```

### Adapters

| Content Type | Adapter | AI Required | Notes |
|-------------|---------|-------------|-------|
| `video` | VideoExtractor | Whisper + Claude | Hallucination detection (confidence, rate, repetition) |
| `image` | ImageExtractor | Claude vision | Single-call OCR + visual description |
| `article` | ArticleExtractor | None | trafilatura HTML cleaning (F1=0.96) |
| `gallery` | GalleryExtractor | Claude vision | Per-image analysis + narrative synthesis |

## Dependencies

- Python 3.13+
- FFmpeg (system, for audio extraction)
- faster-whisper (local Whisper, ~1.6GB model)
- Claude API access (via CLI Proxy API at localhost:8317, or `ANTHROPIC_API_KEY`)

## Failure Modes

| Failure | Behavior |
|---------|----------|
| Invalid content_item.json | `ContentItemInvalidError` with missing fields |
| Unsupported content_type | `UnsupportedContentTypeError` with supported list |
| Whisper hallucination detected | Segment marked `is_suspicious`, extraction continues |
| LLM analysis failure | Analysis marked `degraded` in status.json, extraction continues |
| Already extracted | Skip (unless `--force`); `.extraction_complete` marker |

## Pipeline Position

```
content-downloader → content-extractor → content-rewriter → [publish]
```

This capability sits between download and rewriting. It transforms raw media into structured text.

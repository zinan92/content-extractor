# Research: Phase 5 — Video Core

**Phase:** 05-video-core
**Researched:** 2026-03-30
**Scope:** FFmpeg audio extraction + faster-whisper transcription with timestamps

## Overview

Phase 5 implements the VideoExtractor adapter: extract audio from video files via FFmpeg subprocess, transcribe with faster-whisper (CTranslate2 backend), and return timestamped transcript segments conforming to the existing `Transcript` / `TranscriptSegment` Pydantic models.

This phase depends only on Phase 1 (foundation). No LLM infrastructure needed — faster-whisper runs locally.

## Key Technical Decisions

### 1. FFmpeg Audio Extraction

**Approach:** `subprocess.run()` calling `ffmpeg` directly. No Python wrapper library.

**Command:**
```bash
ffmpeg -i <input_video> -vn -acodec pcm_s16le -ar 16000 -ac 1 -f wav <output.wav>
```

Key flags:
- `-vn` — discard video stream
- `-acodec pcm_s16le` — 16-bit PCM (what faster-whisper expects internally)
- `-ar 16000` — 16kHz sample rate (Whisper's native rate)
- `-ac 1` — mono (Whisper processes mono only)
- `-f wav` — force WAV output container

**Validation steps (per PITFALLS.md Pitfall 5):**
1. Run `ffprobe -v error -select_streams a -show_entries stream=codec_name,sample_rate,duration -of json <video>` to check audio stream exists before extraction
2. Verify output WAV file size > 0 bytes
3. Capture and log FFmpeg stderr (critical warnings about codec issues)
4. Handle "no audio stream" explicitly: return early with `audio_unavailable` quality indicator

**Codec coverage from Douyin/XHS:**
- MP4/AAC (most common)
- MP4/H.265+AAC
- MOV containers (XHS iOS uploads)
- WebM/Opus (rare but possible)

FFmpeg handles all of these natively. The `-acodec pcm_s16le` flag forces re-encoding to WAV regardless of source codec.

### 2. faster-whisper Integration

**Library:** `faster-whisper>=1.2,<2` (CTranslate2 4.7.1 backend, Python 3.13 compatible)

**Model initialization:**
```python
from faster_whisper import WhisperModel

model = WhisperModel(
    model_size_or_path="turbo",  # default, overridable via config.whisper_model
    device="auto",               # auto-detects CPU/CUDA
    compute_type="int8",         # low memory on Apple Silicon
)
```

**Transcription call:**
```python
segments, info = model.transcribe(
    audio_path,
    language="zh",                        # explicit Chinese (VID-03)
    initial_prompt="以下是普通话的句子。",  # bias toward Simplified Chinese (PITFALLS Pitfall 2)
    condition_on_previous_text=False,      # break hallucination cascade (PITFALLS Pitfall 1)
    beam_size=5,
    vad_filter=True,                       # built-in Silero VAD (basic filtering)
    vad_parameters={"min_silence_duration_ms": 500},
)
```

**Note on `language` parameter:** We set `language="zh"` explicitly rather than relying on auto-detection. Auto-detection on short clips or clips with background music is unreliable for Chinese content. The caller can override this via config if needed for non-Chinese content.

**Note on `condition_on_previous_text=False`:** This is the single most important anti-hallucination setting. Without it, one hallucinated segment cascades into a stream of fabricated text. The tradeoff is slightly less coherent segment boundaries, which is acceptable for our use case (downstream LLM analysis will smooth text anyway).

### 3. Turbo Model as Default (VID-05)

**Model string:** `"turbo"` — faster-whisper resolves this to `deepdml/faster-whisper-large-v3-turbo-ct2` from HuggingFace.

**Why turbo:**
- Distilled from large-v3: similar accuracy, 8x faster
- ~1.6GB model size vs ~3GB for large-v3
- INT8 on CPU: fast enough for batch processing without GPU

**Model switching via `--whisper-model`:** Already supported in `ExtractorConfig.whisper_model` (default `"turbo"`). Valid values: `"tiny"`, `"base"`, `"small"`, `"medium"`, `"large-v3"`, `"turbo"`, or a HuggingFace model path.

### 4. Timestamp + Confidence Output (VID-04)

Each faster-whisper segment provides:
- `segment.start` — start time in seconds (float)
- `segment.end` — end time in seconds (float)
- `segment.text` — transcribed text
- `segment.avg_logprob` — average log probability (negative; closer to 0 = more confident)
- `segment.no_speech_prob` — probability that segment is non-speech

**Confidence mapping:** Convert `avg_logprob` to a 0-1 confidence score:
```python
import math
confidence = math.exp(segment.avg_logprob)  # logprob to probability
```
This maps logprob -0.0 to 1.0 (perfect), -0.7 to ~0.5 (moderate), -2.0 to ~0.13 (low).

**Filtering:** Skip segments where `no_speech_prob > 0.6` (Whisper's default threshold). These are likely hallucinations on silence.

### 5. Output Mapping to Existing Models

The existing `TranscriptSegment` and `Transcript` models (from Phase 1) already match:

```python
TranscriptSegment(text=..., start=..., end=..., confidence=...)
Transcript(content_id=..., content_type="video", language="zh", segments=(...), full_text=...)
```

The `ExtractionResult` wraps `Transcript` in its `transcript` field. `QualityMetadata` captures overall confidence (average across segments), word count, and processing time.

### 6. Module Architecture

```
src/content_extractor/
    adapters/
        video.py          # VideoExtractor (replace stub)
    video/
        __init__.py
        ffmpeg.py         # extract_audio(), probe_audio_stream()
        transcribe.py     # transcribe_audio() using faster-whisper
```

Separating FFmpeg and transcription into `video/` subpackage keeps each module focused (<200 lines). `video.py` adapter orchestrates both.

## Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| FFmpeg not installed on system | LOW (dev machines have it) | Check at import time, clear error message |
| Model download on first run (~1.6GB) | CERTAIN | Log a message, faster-whisper handles download automatically |
| Apple Silicon memory pressure with int8 | LOW | faster-whisper int8 uses ~2GB for turbo; well within 8GB+ machines |
| Chinese script mixing (Simplified/Traditional) | MEDIUM | `initial_prompt` biases Simplified; full normalization deferred to Phase 6 |

## Dependencies to Add

```toml
# In pyproject.toml dependencies
"faster-whisper>=1.2,<2",
```

## Test Strategy

- **Unit tests:** Mock `subprocess.run` for FFmpeg, mock `WhisperModel` for transcription. Test segment-to-model mapping, confidence calculation, error handling.
- **Integration test (optional, manual):** Run against a real short video file to verify end-to-end. Not in CI (requires FFmpeg + model download).

## Sources

- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper) — API reference, VAD filter docs
- [deepdml/faster-whisper-large-v3-turbo-ct2](https://huggingface.co/deepdml/faster-whisper-large-v3-turbo-ct2) — turbo model
- PITFALLS.md Pitfalls 1, 2, 5 — hallucination, script mixing, FFmpeg failures
- STACK.md — faster-whisper selection rationale

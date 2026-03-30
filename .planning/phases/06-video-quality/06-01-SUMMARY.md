---
phase: 06-video-quality
plan: 01
subsystem: video
tags: [ffmpeg, loudnorm, vad, whisper, audio-normalization]

# Dependency graph
requires:
  - phase: 05-video-core
    provides: FFmpeg audio extraction and faster-whisper transcription modules
provides:
  - normalize_audio() function with loudnorm filter in ffmpeg.py
  - TranscriptionResult frozen dataclass with speech_ratio from VAD
  - Speech-ratio gating in VideoExtractor (skip <10% speech)
  - Non-fatal normalization fallback in VideoExtractor pipeline
affects: [06-video-quality, 09-cli-library]

# Tech tracking
tech-stack:
  added: []
  patterns: [non-fatal-fallback, vad-speech-ratio-gating]

key-files:
  created: []
  modified:
    - src/content_extractor/video/ffmpeg.py
    - src/content_extractor/video/transcribe.py
    - src/content_extractor/adapters/video.py
    - tests/test_ffmpeg.py
    - tests/test_transcribe.py
    - tests/test_video_extractor.py

key-decisions:
  - "normalize_audio uses loudnorm=I=-16:TP=-1.5:LRA=11 (EBU R128 standard)"
  - "TranscriptionResult frozen dataclass wraps segments + speech_ratio + duration"
  - "Normalization failure is non-fatal: falls back to unnormalized audio with warning"
  - "Speech ratio < 0.10 gates transcription: returns confidence=0.0 with low_speech_ratio metadata"

patterns-established:
  - "Non-fatal FFmpeg step: try/except FFmpegError with warning log and fallback"
  - "Speech ratio gating: early return with metadata flag for downstream awareness"

requirements-completed: [VID-02, VID-06]

# Metrics
duration: 4min
completed: 2026-03-30
---

# Phase 6 Plan 01: Volume Normalization and VAD Speech-Ratio Summary

**FFmpeg loudnorm volume normalization and VAD speech-ratio gating with non-fatal fallback pipeline**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-30T06:51:58Z
- **Completed:** 2026-03-30T06:56:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added normalize_audio() to ffmpeg.py using loudnorm filter (I=-16, TP=-1.5, LRA=11) with atomic tmp file pattern
- Changed transcribe_audio() return type from bare tuple to TranscriptionResult with speech_ratio computed from VAD metadata
- Wired normalization and speech-ratio gating into VideoExtractor pipeline with graceful fallback

## Task Commits

Each task was committed atomically:

1. **Task 1: Add normalize_audio and TranscriptionResult with speech_ratio** - `c09258d` (feat)
2. **Task 2: Wire normalization and speech-ratio gating into VideoExtractor** - `20e2def` (feat)

## Files Created/Modified
- `src/content_extractor/video/ffmpeg.py` - Added normalize_audio() with loudnorm filter
- `src/content_extractor/video/transcribe.py` - Added TranscriptionResult dataclass, updated return type
- `src/content_extractor/adapters/video.py` - Added normalization step and speech-ratio gating
- `tests/test_ffmpeg.py` - 6 new tests for normalize_audio
- `tests/test_transcribe.py` - 2 new tests for speech_ratio, updated existing for new return type
- `tests/test_video_extractor.py` - 2 new tests for normalization fallback and low speech ratio

## Decisions Made
- Used EBU R128 loudnorm parameters (I=-16, TP=-1.5, LRA=11) as industry standard
- Non-fatal normalization: FFmpegError caught and logged, pipeline continues with unnormalized audio
- Speech ratio threshold 0.10 (10%) matches plan spec; stores ratio as string in platform_metadata

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Volume normalization and speech-ratio gating ready for hallucination detection (Plan 06-02)
- TranscriptionResult provides speech_ratio needed by hallucination heuristics

---
*Phase: 06-video-quality*
*Completed: 2026-03-30*

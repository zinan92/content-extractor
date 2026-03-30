---
phase: 05-video-core
plan: 01
subsystem: video
tags: [ffmpeg, faster-whisper, transcription, audio-extraction, subprocess]

requires:
  - phase: 01-foundation
    provides: Pydantic models (TranscriptSegment, Transcript, QualityMetadata), ExtractorConfig
provides:
  - FFmpeg audio probing and extraction module (video/ffmpeg.py)
  - faster-whisper transcription module with anti-hallucination settings (video/transcribe.py)
  - AudioProbeResult, FFmpegError, TranscriptionError types
affects: [05-02, video-quality]

tech-stack:
  added: [faster-whisper, ffmpeg-subprocess]
  patterns: [frozen-dataclass-for-results, module-level-model-cache, atomic-file-write]

key-files:
  created:
    - src/content_extractor/video/__init__.py
    - src/content_extractor/video/ffmpeg.py
    - src/content_extractor/video/transcribe.py
    - tests/test_ffmpeg.py
    - tests/test_transcribe.py
  modified: []

key-decisions:
  - "frozen dataclass (not Pydantic) for AudioProbeResult -- lightweight internal type, not serialized"
  - "Module-level dict cache for WhisperModel instances -- justified by ~5s load time"
  - "math.exp(avg_logprob) clamped to [0,1] for confidence scoring"

patterns-established:
  - "Subprocess wrapper pattern: validate input -> run subprocess -> parse output -> raise custom error"
  - "Model cache pattern: module-level dict with lazy loading for expensive ML models"

requirements-completed: [VID-01, VID-03, VID-04, VID-05]

duration: 4min
completed: 2026-03-30
---

# Phase 05 Plan 01: FFmpeg + Whisper Modules Summary

**FFmpeg audio extraction (probe + extract to 16kHz WAV) and faster-whisper transcription with zh language, VAD filter, and no_speech_prob filtering**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-30T06:12:04Z
- **Completed:** 2026-03-30T06:16:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- FFmpeg module with probe_audio_stream (ffprobe JSON parsing) and extract_audio (atomic WAV extraction)
- Transcription module wrapping faster-whisper with anti-hallucination settings (condition_on_previous_text=False, vad_filter, no_speech filtering)
- 20 unit tests all passing with fully mocked subprocess and WhisperModel

## Task Commits

Each task was committed atomically:

1. **Task 1: FFmpeg audio extraction module** - `56f9b99` (feat)
2. **Task 2: faster-whisper transcription module** - `f231da6` (feat)

_Both tasks followed TDD: RED (import error) -> GREEN (all tests pass)_

## Files Created/Modified
- `src/content_extractor/video/__init__.py` - Package init for video subpackage
- `src/content_extractor/video/ffmpeg.py` - AudioProbeResult, FFmpegError, probe_audio_stream, extract_audio
- `src/content_extractor/video/transcribe.py` - TranscriptionError, transcribe_audio with model caching
- `tests/test_ffmpeg.py` - 10 tests for probe and extract (mocked subprocess)
- `tests/test_transcribe.py` - 10 tests for transcription (mocked WhisperModel)

## Decisions Made
- Used frozen dataclass (not Pydantic) for AudioProbeResult since it is an internal type not serialized to JSON
- Module-level dict cache for WhisperModel instances to avoid ~5s reload per transcription call
- Confidence scoring via math.exp(avg_logprob) clamped to [0.0, 1.0]

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed faster-whisper before tests could run**
- **Found during:** Task 2 (transcription module)
- **Issue:** faster-whisper not yet in virtualenv, import failed at test collection
- **Fix:** Ran pip install faster-whisper>=1.2,<2
- **Files modified:** None (runtime dependency, pyproject.toml update deferred to Plan 05-02)
- **Verification:** All 10 transcribe tests pass
- **Committed in:** f231da6 (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor -- dependency install was planned for 05-02 but needed earlier for test collection.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- FFmpeg and transcription modules ready for VideoExtractor adapter (Plan 05-02)
- All exports match the interfaces specified in Plan 05-02
- faster-whisper installed but not yet in pyproject.toml (Plan 05-02 Task 2)

---
*Phase: 05-video-core*
*Completed: 2026-03-30*

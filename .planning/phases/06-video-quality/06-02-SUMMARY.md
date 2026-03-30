---
phase: 06-video-quality
plan: 02
subsystem: video
tags: [hallucination-detection, whisper, confidence, ngram, vad]

# Dependency graph
requires:
  - phase: 06-video-quality
    provides: TranscriptionResult with speech_ratio, normalize_audio pipeline
provides:
  - Hallucination detection module with per-segment and transcript-level heuristics
  - is_suspicious field on TranscriptSegment for per-segment flagging
  - hallucination_warnings field on QualityMetadata for transcript-level warnings
  - All-suspicious confidence halving in VideoExtractor
affects: [09-cli-library]

# Tech tracking
tech-stack:
  added: []
  patterns: [hallucination-heuristics, immutable-model-copy-update]

key-files:
  created:
    - src/content_extractor/video/hallucination.py
    - tests/test_hallucination.py
  modified:
    - src/content_extractor/models.py
    - src/content_extractor/adapters/video.py
    - tests/test_video_extractor.py
    - tests/test_models.py

key-decisions:
  - "Confidence threshold 0.4 for suspicious segments"
  - "CJK chars/sec > 6.0 flags impossibly fast speech as suspicious"
  - "Character 4-grams with threshold 3 for CJK repetition detection"
  - "All-suspicious transcript halves average confidence"

patterns-established:
  - "Pydantic model_copy(update={}) for immutable field updates on frozen models"
  - "Heuristic-based quality scoring: multiple independent checks producing warning tuple"

requirements-completed: [VID-07]

# Metrics
duration: 4min
completed: 2026-03-30
---

# Phase 6 Plan 02: Hallucination Detection Summary

**Per-segment suspicion flags and transcript-level hallucination warnings via confidence, speed, and repetition heuristics**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-30T06:56:00Z
- **Completed:** 2026-03-30T07:01:42Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Created hallucination.py with three exported functions: check_segment_suspicious, detect_repeated_ngrams, check_transcript_hallucinations
- Added is_suspicious field to TranscriptSegment and hallucination_warnings to QualityMetadata
- Wired hallucination guard into VideoExtractor: segments flagged, warnings populated, all-suspicious confidence halved

## Task Commits

Each task was committed atomically:

1. **Task 1: Create hallucination detection module and update models** - `1a7f53a` (feat)
2. **Task 2: Wire hallucination guard into VideoExtractor** - `f985d4f` (feat)

## Files Created/Modified
- `src/content_extractor/video/hallucination.py` - New module with 3 exported heuristic functions
- `src/content_extractor/models.py` - Added is_suspicious to TranscriptSegment, hallucination_warnings to QualityMetadata
- `src/content_extractor/adapters/video.py` - Wired hallucination checks after transcription
- `tests/test_hallucination.py` - 15 tests covering each heuristic edge case
- `tests/test_models.py` - 5 tests for new model fields
- `tests/test_video_extractor.py` - 3 tests for flagging, warnings, confidence halving

## Decisions Made
- Confidence < 0.4 threshold for suspicious (balances false positives vs catches hallucinations)
- CJK chars/sec > 6.0 threshold (native speakers average ~4 chars/sec, 6 is impossibly fast)
- Character 4-grams for CJK repetition (word-level n-grams don't work well for Chinese)
- All-suspicious halves confidence rather than zeroing it (preserves some signal)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functionality is fully wired.

## Next Phase Readiness
- Video quality phase complete: normalization, VAD gating, and hallucination detection all active
- Ready for Phase 7 (Gallery), Phase 8 (LLM Analysis), or Phase 9 (CLI)

---
*Phase: 06-video-quality*
*Completed: 2026-03-30*

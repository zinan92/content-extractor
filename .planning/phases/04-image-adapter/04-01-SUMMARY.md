---
phase: 04-image-adapter
plan: 01
subsystem: extraction
tags: [claude-vision, ocr, pillow, image-processing, chinese-text]

# Dependency graph
requires:
  - phase: 01-models-config
    provides: ExtractionResult, MediaDescription, QualityMetadata, ExtractorConfig
  - phase: 03-llm-infra
    provides: create_claude_client for Anthropic API access
provides:
  - ImageExtractor adapter satisfying Extractor Protocol
  - Reusable vision module (preprocess_image, describe_image, VisionResponse)
  - Shared text_utils module (_detect_language, _compute_word_count)
affects: [07-gallery-adapter, 08-llm-analysis]

# Tech tracking
tech-stack:
  added: [Pillow]
  patterns: [vision-api-call, image-preprocessing-base64, error-isolation-per-image]

key-files:
  created:
    - src/content_extractor/vision.py
    - src/content_extractor/text_utils.py
  modified:
    - src/content_extractor/adapters/image.py
    - src/content_extractor/adapters/article.py
    - tests/test_image_extractor.py
    - tests/conftest.py
    - tests/test_extract.py
    - tests/test_router.py
    - pyproject.toml

key-decisions:
  - "Use create_claude_client from Phase 3 LLM infra instead of raw anthropic.Anthropic()"
  - "Extract text_utils from article adapter for shared language detection and word counting"
  - "Error isolation per-image: one bad image produces empty MediaDescription, does not fail extraction"

patterns-established:
  - "Vision call pattern: preprocess_image -> describe_image -> VisionResponse for reuse by gallery adapter"
  - "Image preprocessing: resize to max 1568px, convert unsupported formats to JPEG, handle RGBA->RGB"
  - "Per-image error isolation: try/except per file with fallback MediaDescription(confidence=0.0)"

requirements-completed: [IMG-01, IMG-02, IMG-03]

# Metrics
duration: 6min
completed: 2026-03-30
---

# Phase 04 Plan 01: Image Adapter Summary

**ImageExtractor with Claude vision OCR + visual description, Chinese text support, and reusable vision module**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-30T06:23:10Z
- **Completed:** 2026-03-30T06:29:10Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Vision module with image preprocessing (resize, format conversion, base64) and Claude vision API call
- ImageExtractor adapter producing ExtractionResult with OCR text, visual descriptions, and confidence scores
- Shared text_utils module extracted from article adapter for language detection and CJK word counting
- 137 tests pass at 95% coverage with all API calls mocked

## Task Commits

Each task was committed atomically:

1. **Task 1: Vision module** - `1252cd4` (test) - preprocess_image + describe_image + VisionResponse + 9 tests
2. **Task 2: ImageExtractor adapter** - `2bada31` (feat) - full pipeline integration + text_utils extraction + 7 integration tests

## Files Created/Modified
- `src/content_extractor/vision.py` - Image preprocessing and Claude vision API call module
- `src/content_extractor/text_utils.py` - Shared _detect_language and _compute_word_count
- `src/content_extractor/adapters/image.py` - ImageExtractor implementing Extractor Protocol
- `src/content_extractor/adapters/article.py` - Refactored to import from text_utils
- `tests/test_image_extractor.py` - 16 tests for vision module + ImageExtractor
- `tests/conftest.py` - Added tmp_image_dir and mock_vision_response_json fixtures
- `tests/test_extract.py` - Updated stub tests to use gallery (image is no longer a stub)
- `tests/test_router.py` - Updated stub parametrize to exclude image
- `pyproject.toml` - Added Pillow>=11,<12 dependency

## Decisions Made
- Used create_claude_client from Phase 3 LLM infra for proper token resolution (CLI Proxy API -> env var fallback) instead of raw anthropic.Anthropic()
- Extracted _detect_language and _compute_word_count into text_utils.py to avoid cross-adapter imports while keeping article.py behavior unchanged
- Per-image error isolation: exceptions during individual image processing produce fallback MediaDescription(confidence=0.0) rather than failing the entire extraction

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Image.format lost after resize**
- **Found during:** Task 1 (Vision module tests)
- **Issue:** PIL Image.resize() returns a new Image without .format attribute, causing all resized images to fall through to JPEG conversion
- **Fix:** Captured img.format before any resize operation
- **Files modified:** src/content_extractor/vision.py
- **Verification:** test_large_image_resized passes with correct media_type
- **Committed in:** 1252cd4 (Task 1 commit)

**2. [Rule 1 - Bug] Updated existing stub tests for image adapter**
- **Found during:** Task 2 (Full test suite run)
- **Issue:** test_extract.py and test_router.py expected NotImplementedError from ImageExtractor (it was a stub), but now it's implemented
- **Fix:** Changed stub tests to use gallery content_type (still a stub) instead of image
- **Files modified:** tests/test_extract.py, tests/test_router.py
- **Verification:** All 137 tests pass
- **Committed in:** 2bada31 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all planned functionality is wired and tested.

## Next Phase Readiness
- Vision module (preprocess_image, describe_image) ready for reuse by gallery adapter (Phase 7)
- text_utils module available for any future adapter needing language detection
- ImageExtractor registered in router and fully operational with mocked API

---
*Phase: 04-image-adapter*
*Completed: 2026-03-30*

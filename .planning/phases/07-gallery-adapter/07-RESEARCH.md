# Phase 7: Gallery Adapter — Research

**Researched:** 2026-03-30
**Discovery Level:** 0 (Skip)
**Confidence:** HIGH

## Why Level 0

All building blocks already exist in the codebase:
- `vision.py`: `preprocess_image()` and `describe_image()` — designed for gallery reuse (docstring says so)
- `adapters/image.py`: `ImageExtractor` with per-image error isolation pattern
- `llm.py`: `create_claude_client()` for the synthesis LLM call
- `models.py`: `ExtractionResult`, `MediaDescription`, `QualityMetadata`
- `text_utils.py`: `_detect_language`, `_compute_word_count`
- `config.py`: `ExtractorConfig` with claude_model, claude_max_tokens, claude_temperature

No new libraries. No new external integrations. Pure internal wiring.

## Architecture Decision

### Batching Strategy (GLRY-02)

The Claude vision API accepts multiple images in a single message (multi-image content blocks). Rather than sending N separate API calls (one per image), we batch images into a single `messages.create()` call with multiple image content blocks followed by the text prompt. This:

1. Minimizes API calls (1 call per batch vs N calls)
2. Lets the model see images in context together (better for gallery narrative)
3. Respects rate limits naturally (fewer calls = fewer 429s)

**Batch size limit:** Claude has a per-message size limit. Large galleries (10+ high-res images) may exceed it. Strategy: batch in groups of 5 images, process groups sequentially.

### Narrative Synthesis (GLRY-03)

After getting per-image descriptions, a second LLM call synthesizes them into a coherent gallery narrative. This is a text-only call (no images) that takes the per-image descriptions as input and produces a unified story.

### Error Semantics (D-08)

PROJECT.md D-08 says "gallery-level all-or-nothing." However, REQUIREMENTS.md QUAL-01 says "per-item error isolation -- one failed image in gallery does not fail the whole item." These conflict.

**Resolution:** Follow QUAL-01 (already marked complete, established pattern in ImageExtractor). Per-image failures produce empty MediaDescription(confidence=0.0). Gallery extraction succeeds with partial results. The narrative synthesis works with whatever images succeeded.

## Key Patterns to Reuse

| From | Pattern | How |
|------|---------|-----|
| `vision.py` | `preprocess_image` + `describe_image` | Call per image, same as ImageExtractor |
| `adapters/image.py` | Image file discovery (media_files + glob fallback) | Copy pattern exactly |
| `adapters/image.py` | Per-image try/except with fallback MediaDescription | Same error isolation |
| `text_utils.py` | `_detect_language`, `_compute_word_count` | For quality metadata |
| `llm.py` | `create_claude_client` | For narrative synthesis call |

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/content_extractor/adapters/gallery.py` | Replace stub with full implementation |
| `tests/test_gallery_extractor.py` | New test file |
| `tests/test_extract.py` | Update stub tests (gallery no longer raises NotImplementedError) |
| `tests/test_router.py` | Remove gallery from stub parametrize list |

---
*Research for: Phase 7 Gallery Adapter*
*Researched: 2026-03-30*

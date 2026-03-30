# Phase 1: Foundation & Data Models - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 01-foundation-data-models
**Areas discussed:** Output Schema Design, Config Approach, Error Handling

---

## Output Schema Design

### Q1: How should the three output files divide responsibilities?

| Option | Description | Selected |
|--------|-------------|----------|
| Strict separation | transcript.json = raw text + timestamps; analysis.json = LLM insights; structured_text.md = human-readable combo | ✓ |
| Combined JSON + MD | One extraction.json with everything nested, plus MD | |
| Single file only | One structured_text.md with everything | |

**User's choice:** Strict separation (Recommended)

### Q2: For video transcript.json, what level of detail?

| Option | Description | Selected |
|--------|-------------|----------|
| Segment-level | Segments with start/end timestamps + confidence (~5-30 sec chunks) | �� |
| Word-level | Every word with individual timestamp | |
| Full text only | Complete text, no timestamps | |

**User's choice:** Segment-level (Recommended)

### Q3: How structured should analysis.json be?

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed schema | Predefined fields: topics[], viewpoints[], sentiment{}, takeaways[]. Same for all types | ✓ |
| Flexible per type | Different schemas per content_type | |
| You decide | Claude picks | |

**User's choice:** Fixed schema (Recommended)

### Q4: structured_text.md format?

| Option | Description | Selected |
|--------|-------------|----------|
| Report style | # Title → ## Summary → ## Key Takeaways → ## Full Content → ## Analysis | ✓ |
| Minimal | Title + content + takeaways at bottom | |
| You decide | Claude designs it | |

**User's choice:** Report style (Recommended)

---

## Config Approach

### Q1: How should settings be managed?

| Option | Description | Selected |
|--------|-------------|----------|
| CLI args only | Like content-downloader: --whisper-model, --force, --output-dir. No config file. | ✓ |
| TOML + CLI override | Config file for defaults, CLI args override | |
| Env vars + CLI | Environment variables + CLI flags | |

**User's choice:** CLI args only (Recommended)

### Q2: How should LLM settings be specified?

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded defaults | Sensible defaults baked in. Only --whisper-model exposed. | ✓ |
| All configurable | Expose Claude model, temperature, max tokens as flags | |
| You decide | Claude picks what to expose | |

**User's choice:** Hardcoded defaults (Recommended)

---

## Error Handling

### Q1: When one item in a batch fails, what happens?

| Option | Description | Selected |
|--------|-------------|----------|
| Skip + log | Log error, skip item, continue. Summary at end. | ✓ |
| Skip + save error | Same + write error.json to failed item directory | |
| Fail fast | Stop whole batch on first error | |

**User's choice:** Skip + log (Recommended)

### Q2: If a gallery has 9 images and image #5 fails?

| Option | Description | Selected |
|--------|-------------|----------|
| Partial result | Save 1-4, 6-9. Mark #5 failed. Narrative from available. | |
| All or nothing | Any image fails = whole gallery fails | ✓ |
| You decide | Claude picks | |

**User's choice:** All or nothing
**Notes:** User prefers gallery all-or-nothing to avoid misleading narratives from partial image sets

---

## Claude's Discretion

- Pydantic model field names and nesting
- Adapter Protocol interface design
- Atomic write implementation
- Quality metadata fields

## Deferred Ideas

None

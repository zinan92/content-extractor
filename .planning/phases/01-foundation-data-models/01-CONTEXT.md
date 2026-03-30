# Phase 1: Foundation & Data Models - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Solid data contract and adapter framework that all subsequent adapters plug into. Defines Pydantic models for input (ContentItem loader) and output (transcript, analysis, extraction result). Implements adapter registry with content_type routing, atomic output file writing, idempotent processing, configuration system, and error isolation with quality metadata. No actual extraction logic — just the framework that adapters plug into.

</domain>

<decisions>
## Implementation Decisions

### Output Schema Design
- **D-01:** Strict separation of output files — `transcript.json` (pure raw text + timestamps), `analysis.json` (LLM structured insights), `structured_text.md` (human-readable combo). Each file can exist independently.
- **D-02:** Video transcripts at segment-level — segments with start/end timestamps + confidence. Each segment = one Whisper chunk (~5-30 seconds).
- **D-03:** Fixed analysis schema across all content types — predefined fields: `topics[]`, `viewpoints[]`, `sentiment{}`, `takeaways[]`. Same structure regardless of content_type for easy downstream parsing.
- **D-04:** structured_text.md in report style — `# Title` → `## Summary` → `## Key Takeaways` → `## Full Transcript/Content` → `## Analysis`. Like a research brief.

### Config Approach
- **D-05:** CLI args only, no config file. Mirrors content-downloader's approach. Flags: `--whisper-model`, `--force`, `--output-dir`.
- **D-06:** LLM settings (Claude model, temperature, max tokens) hardcoded as sensible defaults. Only `--whisper-model` exposed for Whisper model selection. Claude model/settings are internal implementation details.

### Error Handling
- **D-07:** Batch-level: skip failed items + log error, continue processing. Summary at end shows all failures.
- **D-08:** Gallery-level: all-or-nothing. If any image in a gallery fails, the whole gallery is marked as failed. Avoids misleading narratives from partial image sets.
- **D-09:** No error.json files — errors are logged to stdout/stderr and included in batch summary.

### Claude's Discretion
- Exact Pydantic model field names and nesting
- Adapter Protocol interface design
- Atomic write implementation (temp file + rename vs write lock)
- Quality metadata fields beyond confidence/language/word_count/processing_time

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Upstream contract (content-downloader)
- `/Users/wendy/work/content-co/content-downloader/content_downloader/models.py` — ContentItem Pydantic model defining the input schema (platform, content_id, content_type, media_files, etc.)
- `/Users/wendy/work/content-co/content-downloader/content_downloader/output.py` — OutputManager defining the directory layout: `{output_dir}/{platform}/{author_id}/{content_id}/`

### Research
- `.planning/research/ARCHITECTURE.md` — Two-layer adapter architecture, component boundaries, data flow
- `.planning/research/STACK.md` — Technology choices: faster-whisper, anthropic SDK, trafilatura, Typer, Rich
- `.planning/research/PITFALLS.md` — Whisper hallucinations, cascading errors, atomic writes
- `.planning/research/FEATURES.md` — Feature dependencies and anti-features

### Project
- `.planning/PROJECT.md` — Constraints (Python 3.13+, CLI Proxy API, output compatibility)
- `.planning/REQUIREMENTS.md` — FOUND-01..06, QUAL-01..04 requirements

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- content-downloader's `ContentItem` Pydantic model — defines the input contract. content-extractor should define its OWN Pydantic model reading from JSON (not importing from content-downloader) to avoid coupling.
- content-downloader's `OutputManager` — establishes the directory layout pattern. Extractor writes to same dirs but different files.

### Established Patterns
- Frozen Pydantic models (`model_config = {"frozen": True}`) — content-downloader uses this for immutability
- Adapter pattern with platform routing — content-downloader routes by platform, extractor routes by content_type
- `pyproject.toml` for project setup — consistent with content-downloader

### Integration Points
- Input: reads `content_item.json` from content-downloader output directories
- Output: writes `transcript.json`, `analysis.json`, `structured_text.md` to same directories
- Must not overwrite or modify existing files (`content_item.json`, `metadata.json`, `media/`)

</code_context>

<specifics>
## Specific Ideas

- Mirror content-downloader's project structure and conventions (pyproject.toml, src layout, frozen Pydantic models)
- Adapter stubs should return `NotImplementedError` — they'll be filled in by subsequent phases
- The output writer should handle the "append to existing ContentItem directory" pattern cleanly

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation-data-models*
*Context gathered: 2026-03-30*

# Phase 8: LLM Analysis - Research

**Date:** 2026-03-30
**Discovery Level:** 0 (Skip)

## Rationale for Level 0

All infrastructure already exists in the codebase:
- `llm.py` provides `create_claude_client()` with token loading, expiry handling, rate-limit retry
- `models.py` already defines `AnalysisResult` (topics, viewpoints, sentiment, takeaways) and `SentimentResult`
- `vision.py` demonstrates the pattern: build prompt, call `client.messages.create()`, parse JSON response
- `output.py` already writes `analysis.json` (currently placeholder) and `structured_text.md` (currently placeholder sections)
- `config.py` has `claude_model`, `claude_max_tokens`, `claude_temperature` fields

No new libraries needed. No new external services. Pure internal work following established patterns.

## Architecture Analysis

### Current State

The extraction pipeline is: `load -> route -> adapter.extract() -> write_extraction_output()`.

Analysis is NOT part of adapter extraction. It is a separate step that runs AFTER extraction, consuming `ExtractionResult.raw_text` (which every adapter produces). Currently:
- `output.py` writes a **placeholder** `AnalysisResult` with empty fields
- `_render_structured_text()` outputs "*Populated by analysis phase.*" for Summary, Key Takeaways, and Analysis sections

### Design for Phase 8

Analysis is a post-extraction step, not an adapter. The flow becomes:

```
adapter.extract() -> ExtractionResult (has raw_text)
                  -> analyze(raw_text) -> AnalysisResult (filled)
                  -> write_extraction_output() (now with real analysis)
```

Key design points:
1. **New module `analysis.py`** -- contains the prompt, LLM call, and response parsing
2. **Modify `extract.py`** -- call `analyze()` between adapter extraction and output writing
3. **Modify `output.py`** -- accept real `AnalysisResult` instead of placeholder; render structured_text.md with actual content
4. **No model changes needed** -- `AnalysisResult` already has the right schema (D-03)

### Prompt Design

Single LLM call returns all analysis dimensions in one structured JSON matching `AnalysisResult`:
- `topics[]` -- main themes/subjects (ANLYS-01)
- `viewpoints[]` -- core arguments/perspectives (ANLYS-02)
- `sentiment{}` -- overall tone + confidence (ANLYS-03)
- `takeaways[]` -- actionable insights (ANLYS-04)

Using the anthropic SDK's native structured output (Pydantic model) would be ideal but the vision module already proves the JSON-prompt-then-parse pattern works. Stick with the established pattern for consistency.

### Integration with Output Writer

`write_extraction_output()` currently:
1. Creates a placeholder `AnalysisResult` internally
2. Renders `structured_text.md` with placeholder sections

After Phase 8:
1. Receives a real `AnalysisResult` from the caller
2. Renders `structured_text.md` with actual summary, takeaways, and analysis

## Sources

- Existing codebase: `llm.py`, `models.py`, `vision.py`, `output.py`, `extract.py`
- Decision D-03: Fixed analysis schema (topics, viewpoints, sentiment, takeaways)
- Decision D-04: structured_text.md report format

# Phase 9: CLI & Library API - Research

**Researched:** 2026-03-30
**Discovery Level:** 0 (Skip)

## Rationale for Level 0

All work follows established patterns:
- Typer and Rich already in `pyproject.toml` dependencies
- `content-extractor` entry point already declared in `[project.scripts]`
- `extract_content()` and `extract_batch()` already exist in `extract.py` with correct signatures
- `__init__.py` already exports `extract_batch`, `extract_content`, `BatchResult`, `BatchError`
- No new external dependencies needed

## Existing Assets

### Entry Point (pyproject.toml)
```toml
[project.scripts]
content-extractor = "content_extractor.cli:main"
```
Module `content_extractor.cli` does not exist yet -- needs to be created.

### Orchestration Functions (extract.py)
- `extract_content(content_dir: Path, config: ExtractorConfig | None) -> ExtractionResult | None`
- `extract_batch(parent_dir: Path, config: ExtractorConfig | None) -> BatchResult`
- `BatchResult(succeeded, failed, total, success_count, failure_count)`
- `BatchError(content_dir, error)`

### Configuration (config.py)
```python
class ExtractorConfig(BaseModel):
    whisper_model: str = "turbo"
    force_reprocess: bool = False
    output_dir: Path | None = None
    # LLM settings -- hardcoded, not CLI-exposed (D-06)
```

### Public API (__init__.py)
Already exports: `extract_batch`, `extract_content`, `BatchResult`, `BatchError`, `load_content_item`, errors.

## CLI Design (from D-05, CONTEXT.md decisions)

### Commands

1. **`content-extractor extract <path>`** (CLI-01)
   - Single ContentItem directory extraction
   - Flags: `--whisper-model` (default: turbo), `--force` (reprocess)
   - Output: prints result summary to stdout

2. **`content-extractor extract-batch <path>`** (CLI-02)
   - Scans directory recursively for content_item.json
   - Flags: same as extract + batch-specific behavior
   - Output: Rich progress bar (CLI-03), error summary at end (CLI-04)

### Typer Pattern

```python
import typer
app = typer.Typer()

@app.command()
def extract(path: Path, whisper_model: str = "turbo", force: bool = False): ...

@app.command()
def extract_batch(path: Path, whisper_model: str = "turbo", force: bool = False): ...

def main():
    app()
```

### Rich Progress Bar (CLI-03)

For batch mode, wrap the iteration with `rich.progress.Progress`:
- Track total items discovered
- Show per-item status (extracting, skipped, failed)
- Display elapsed time

### Error Summary (CLI-04)

At end of batch, if failures > 0, print a Rich table:
- Content dir path
- Error message
- Total: X succeeded, Y failed, Z skipped

## Library API Design (CLI-05)

Already implemented. The public API is:
```python
from content_extractor import extract_content, extract_batch
result = extract_content(Path("/path/to/item"))
batch = extract_batch(Path("/path/to/output"))
```

What's needed: expose `extract` and `extract_batch` as convenience aliases (matching requirement wording), ensure `ExtractionResult` is exported.

## Implementation Plan

Two plans:
1. **Plan 01:** CLI module with Typer (extract + extract-batch commands), Rich progress bar, error summary
2. **Plan 02:** Library API polish (convenience aliases, ExtractionResult export, docstrings) + integration test

## Sources

- Typer docs: https://typer.tiangolo.com/
- Rich Progress: https://rich.readthedocs.io/en/latest/progress.html
- Existing codebase: `src/content_extractor/extract.py`, `config.py`, `__init__.py`

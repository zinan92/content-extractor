# Phase 1: Foundation & Data Models - Research

**Researched:** 2026-03-30
**Domain:** Pydantic data contracts, adapter framework, atomic file I/O, idempotent processing
**Confidence:** HIGH

## Summary

Phase 1 builds the skeleton that all subsequent phases plug into: Pydantic models for input (ContentItem loader) and output (transcript, analysis, extraction result), an adapter registry with content_type routing, atomic output file writing, idempotent processing via completion markers, configuration dataclass, and error isolation with quality metadata. No actual extraction logic -- just the framework.

The upstream contract is well-defined: content-downloader writes `content_item.json` files with a stable 18-field schema (verified against 4 real samples across douyin, xhs, wechat_oa, and x platforms). The extractor defines its OWN Pydantic model mirroring this schema (with `extra="ignore"` for forward compatibility) rather than importing from content-downloader. Output files (`transcript.json`, `analysis.json`, `structured_text.md`) are appended to the same ContentItem directory using atomic temp-file-then-rename writes.

**Primary recommendation:** Build models.py first (all Pydantic schemas), then loader.py, router.py, output.py, config.py in that order. Each file is small (<150 lines), frozen/immutable, and independently testable. Use `.extraction_complete` marker file for idempotency, not output file existence checks.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Strict separation of output files -- `transcript.json` (pure raw text + timestamps), `analysis.json` (LLM structured insights), `structured_text.md` (human-readable combo). Each file can exist independently.
- **D-02:** Video transcripts at segment-level -- segments with start/end timestamps + confidence. Each segment = one Whisper chunk (~5-30 seconds).
- **D-03:** Fixed analysis schema across all content types -- predefined fields: `topics[]`, `viewpoints[]`, `sentiment{}`, `takeaways[]`. Same structure regardless of content_type for easy downstream parsing.
- **D-04:** structured_text.md in report style -- `# Title` -> `## Summary` -> `## Key Takeaways` -> `## Full Transcript/Content` -> `## Analysis`. Like a research brief.
- **D-05:** CLI args only, no config file. Mirrors content-downloader's approach. Flags: `--whisper-model`, `--force`, `--output-dir`.
- **D-06:** LLM settings (Claude model, temperature, max tokens) hardcoded as sensible defaults. Only `--whisper-model` exposed for Whisper model selection.
- **D-07:** Batch-level: skip failed items + log error, continue processing. Summary at end shows all failures.
- **D-08:** Gallery-level: all-or-nothing. If any image in a gallery fails, the whole gallery is marked as failed.
- **D-09:** No error.json files -- errors are logged to stdout/stderr and included in batch summary.

### Claude's Discretion
- Exact Pydantic model field names and nesting
- Adapter Protocol interface design
- Atomic write implementation (temp file + rename vs write lock)
- Quality metadata fields beyond confidence/language/word_count/processing_time

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FOUND-01 | Load and validate ContentItem from `content_item.json` using own Pydantic model (no import from content-downloader) | Upstream ContentItem schema documented with 18 fields; real samples verified across 4 platforms; `extra="ignore"` for forward compatibility |
| FOUND-02 | Route content to correct adapter based on `content_type` field (video/image/article/gallery) | Adapter Protocol pattern from content-downloader base.py; dict-based registry mapping content_type string to adapter class |
| FOUND-03 | Define standardized output Pydantic models for transcript, analysis, and extraction result | D-01/D-02/D-03 lock output schema; frozen Pydantic models with tuple fields for immutability |
| FOUND-04 | Write output files (`transcript.json`, `analysis.json`, `structured_text.md`) to ContentItem directory | Atomic write via temp file + os.rename; orjson for JSON serialization; plain string write for markdown |
| FOUND-05 | Skip already-extracted content by checking output file existence (idempotent); `--force` flag to override | `.extraction_complete` marker file pattern; check marker not individual files; `--force` deletes marker |
| FOUND-06 | Configuration system for Whisper model, LLM settings, and default behaviors | D-05/D-06 lock CLI-args-only approach; frozen dataclass/Pydantic model for config; hardcoded LLM defaults |
| QUAL-01 | Per-item error isolation -- one failed image in gallery does not fail the whole item | D-08 overrides: gallery is all-or-nothing; but per-item in batch mode means one failed ContentItem does not stop the batch (D-07) |
| QUAL-02 | Extraction quality metadata per item (confidence, language, word count, processing time) | QualityMetadata Pydantic model; fields populated by adapters; stored in ExtractionResult |
| QUAL-03 | Atomic file writes -- partial output never left behind on failure | Temp file + rename pattern; cleanup temp files in finally block on failure |
| QUAL-04 | Preserve platform metadata (author, date, engagement metrics) in output | ContentItem fields (author_name, publish_time, likes/comments/shares/collects/views) carried into ExtractionResult |
</phase_requirements>

## Standard Stack

### Core (Phase 1 only)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 | Data models, validation, frozen immutable schemas | Verified installed locally. ConfigDict(frozen=True) for immutability. `extra="ignore"` for forward compat with upstream |
| orjson | 3.10+ | JSON serialization for transcript.json and analysis.json | 10x faster than stdlib json. Native Pydantic model_dump() dict serialization. |
| pytest | 9.0.2 | Test framework | Verified installed locally. |
| ruff | 0.15.7 | Linting + formatting | Verified installed locally. Single tool for lint+format. |

### Supporting (Phase 1 stubs only)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typer | 0.24+ | CLI skeleton | Phase 1 creates minimal CLI entry point; full CLI in Phase 9 |
| rich | 14.3.3 | Console output for errors/warnings | Verified installed locally. Used via typer integration |

**Installation (Phase 1):**
```bash
pip install pydantic orjson typer rich
pip install -e ".[dev]"  # after pyproject.toml created
```

## Architecture Patterns

### Recommended Project Structure (Phase 1 scope)
```
content-extractor/
  pyproject.toml
  src/
    content_extractor/
      __init__.py              # Public API: extract_content(), extract_batch()
      models.py                # ALL Pydantic models (ContentItem, ExtractionResult, TranscriptSegment, AnalysisResult, QualityMetadata)
      config.py                # ExtractorConfig frozen dataclass
      loader.py                # Load + validate content_item.json from directory
      router.py                # content_type -> adapter dispatch registry
      output.py                # Atomic file writer (transcript.json, analysis.json, structured_text.md)
      adapters/
        __init__.py
        base.py                # Extractor Protocol definition
        video.py               # Stub: raise NotImplementedError
        image.py               # Stub: raise NotImplementedError
        article.py             # Stub: raise NotImplementedError
        gallery.py             # Stub: raise NotImplementedError
  tests/
    conftest.py                # Fixtures: sample content_item.json dicts, temp dirs
    test_models.py             # Model creation, validation, serialization, frozen check
    test_loader.py             # Load from dir, missing file, invalid JSON, extra fields ignored
    test_router.py             # Dispatch by content_type, unknown type error
    test_output.py             # Atomic write, idempotency guard, force flag, cleanup on failure
    test_config.py             # Default config, CLI arg override
    fixtures/                  # Sample content_item.json files (copy from content-downloader test-output)
```

### Pattern 1: Upstream ContentItem Mirror Model
**What:** Define own Pydantic model that reads the same JSON shape as content-downloader's ContentItem, but is a separate class with `extra="ignore"`.
**When to use:** Always -- this is the input contract.

```python
from pydantic import BaseModel, ConfigDict, Field

class ContentItem(BaseModel):
    """Mirror of content-downloader's ContentItem. Reads content_item.json."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    platform: str
    content_id: str
    content_type: str  # "video" | "image" | "article" | "gallery"
    title: str
    description: str
    author_id: str
    author_name: str
    publish_time: str
    source_url: str
    media_files: tuple[str, ...] = ()
    cover_file: str | None = None
    metadata_file: str = "metadata.json"
    likes: int = 0
    comments: int = 0
    shares: int = 0
    collects: int = 0
    views: int = 0
    downloaded_at: str
```

**Key design decisions:**
- `tuple[str, ...]` instead of `list[str]` for `media_files` -- frozen model cannot have mutable list
- `extra="ignore"` -- if content-downloader adds new fields, extractor keeps working
- All engagement metrics default to 0 -- some platforms may not provide all metrics

### Pattern 2: Output Schema (Locked by D-01, D-02, D-03)
**What:** Three separate output files, each independently writable. Frozen Pydantic models.

```python
class TranscriptSegment(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    start: float          # seconds
    end: float            # seconds
    confidence: float     # 0.0-1.0

class Transcript(BaseModel):
    """transcript.json schema"""
    model_config = ConfigDict(frozen=True)

    content_id: str
    content_type: str
    language: str
    segments: tuple[TranscriptSegment, ...] = ()
    full_text: str        # concatenation of all segment text
    schema_version: str = "1.0"

class SentimentResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    overall: str          # "positive" | "negative" | "neutral" | "mixed"
    confidence: float

class AnalysisResult(BaseModel):
    """analysis.json schema"""
    model_config = ConfigDict(frozen=True)

    content_id: str
    content_type: str
    topics: tuple[str, ...] = ()
    viewpoints: tuple[str, ...] = ()
    sentiment: SentimentResult | None = None
    takeaways: tuple[str, ...] = ()
    schema_version: str = "1.0"

class QualityMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    confidence: float = 0.0
    language: str = "unknown"
    word_count: int = 0
    processing_time_seconds: float = 0.0

class MediaDescription(BaseModel):
    """Per-media-file extraction result (images, article HTML, etc.)"""
    model_config = ConfigDict(frozen=True)

    file_path: str
    description: str
    ocr_text: str = ""
    confidence: float = 0.0

class ExtractionResult(BaseModel):
    """Aggregate result returned by each adapter."""
    model_config = ConfigDict(frozen=True)

    content_id: str
    content_type: str
    raw_text: str                                    # primary extracted text
    transcript: Transcript | None = None             # video only
    media_descriptions: tuple[MediaDescription, ...] = ()  # image/gallery
    quality: QualityMetadata = QualityMetadata()
    platform_metadata: dict[str, int | str] = {}     # author, engagement metrics carried forward
    schema_version: str = "1.0"
```

### Pattern 3: Adapter Protocol with Registry
**What:** Python Protocol for structural subtyping. Registry is a plain dict.

```python
from typing import Protocol, runtime_checkable
from pathlib import Path

@runtime_checkable
class Extractor(Protocol):
    """Protocol all content type extractors must satisfy."""
    content_type: str

    def extract(self, content_dir: Path, config: ExtractorConfig) -> ExtractionResult:
        """Extract text content from media files in content_dir."""
        ...

# In router.py
_REGISTRY: dict[str, type[Extractor]] = {}

def register(content_type: str, extractor_cls: type[Extractor]) -> None:
    _REGISTRY[content_type] = extractor_cls

def get_extractor(content_type: str) -> Extractor:
    cls = _REGISTRY.get(content_type)
    if cls is None:
        raise UnsupportedContentTypeError(
            f"No extractor registered for content_type={content_type!r}. "
            f"Supported: {sorted(_REGISTRY.keys())}"
        )
    return cls()
```

### Pattern 4: Atomic Output Writer
**What:** Write to `.tmp` file, rename on success. Completion marker for idempotency.

```python
import orjson
from pathlib import Path

def write_json_atomic(path: Path, data: bytes) -> None:
    """Write JSON bytes atomically via temp file + rename."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_bytes(data)
        tmp.rename(path)  # atomic on same filesystem
    except Exception:
        tmp.unlink(missing_ok=True)
        raise

def write_text_atomic(path: Path, text: str) -> None:
    """Write text atomically via temp file + rename."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        tmp.rename(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise

MARKER_FILE = ".extraction_complete"

def is_extracted(content_dir: Path) -> bool:
    return (content_dir / MARKER_FILE).exists()

def mark_complete(content_dir: Path) -> None:
    (content_dir / MARKER_FILE).touch()

def clear_marker(content_dir: Path) -> None:
    (content_dir / MARKER_FILE).unlink(missing_ok=True)
```

### Pattern 5: ContentItem Loader
**What:** Read content_item.json from a directory, validate, return frozen model.

```python
import orjson
from pathlib import Path

def load_content_item(content_dir: Path) -> ContentItem:
    """Load and validate ContentItem from a content directory."""
    item_path = content_dir / "content_item.json"
    if not item_path.exists():
        raise ContentItemNotFoundError(f"No content_item.json in {content_dir}")
    raw = item_path.read_bytes()
    try:
        data = orjson.loads(raw)
    except orjson.JSONDecodeError as e:
        raise ContentItemInvalidError(f"Invalid JSON in {item_path}: {e}") from e
    return ContentItem.model_validate(data)
```

### Pattern 6: ExtractorConfig (D-05, D-06)
**What:** Frozen config object, no config file. CLI args map to constructor params.

```python
from pydantic import BaseModel, ConfigDict

class ExtractorConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    whisper_model: str = "turbo"
    force_reprocess: bool = False
    output_dir: Path | None = None  # override output location (rare)

    # LLM settings -- hardcoded defaults, not exposed to CLI
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 4096
    claude_temperature: float = 0.0
```

### Anti-Patterns to Avoid
- **Importing from content-downloader:** Use JSON as contract. Define own model with `extra="ignore"`.
- **Checking individual output files for idempotency:** Use `.extraction_complete` marker. Individual files may exist from partial runs.
- **Mutable Pydantic models:** Always `frozen=True`. Gallery adapter composes results from multiple image calls -- mutation causes hidden bugs.
- **Config file or YAML:** D-05 locks CLI-args-only. Keep it simple.
- **Error files on disk:** D-09 locks errors to stdout/stderr only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON serialization | Custom dict-to-JSON | `orjson.dumps(model.model_dump())` | Handles datetime, Pydantic types, 10x faster |
| Atomic file write | Custom lock mechanism | Temp file + `Path.rename()` | rename() is atomic on POSIX same-filesystem; no locks needed |
| Input validation | Manual field checks | Pydantic `model_validate()` with `extra="ignore"` | Type coercion, error messages, frozen enforcement all built-in |
| CLI argument parsing | argparse boilerplate | Typer with type hints | Auto-generates help, validates types, matches Pydantic style |

## Common Pitfalls

### Pitfall 1: Mutable Default in Frozen Model
**What goes wrong:** Using `list[str]` in a frozen Pydantic model. The list itself is mutable even if the model is frozen.
**Why it happens:** Pydantic v2 allows `list` in frozen models but won't prevent `model.media_files.append()` at runtime -- it only prevents `model.media_files = [...]`.
**How to avoid:** Use `tuple[str, ...]` for all sequence fields in frozen models. Tuples are inherently immutable.
**Warning signs:** Tests pass but downstream code accidentally mutates shared state.

### Pitfall 2: Partial Write Corruption
**What goes wrong:** Process crashes after writing `transcript.json` but before writing `analysis.json`. On re-run, idempotency guard sees transcript exists and skips the item, leaving it without analysis.
**Why it happens:** Checking individual file existence instead of a completion marker.
**How to avoid:** Use `.extraction_complete` marker. Write all output files, then touch marker. `--force` deletes marker.
**Warning signs:** Items with some output files but not all.

### Pitfall 3: Forward Compatibility Breakage
**What goes wrong:** content-downloader adds a new field to ContentItem. Extractor's Pydantic validation fails because of the unexpected field.
**Why it happens:** Default Pydantic behavior is `extra="forbid"` or raises warnings.
**How to avoid:** Set `extra="ignore"` on the ContentItem mirror model. Unknown fields silently discarded.
**Warning signs:** Validation errors after upstream updates.

### Pitfall 4: QUAL-01 vs D-08 Conflict
**What goes wrong:** QUAL-01 says "one failed image in gallery does not fail the whole item." D-08 says "gallery is all-or-nothing." These appear contradictory.
**Why it happens:** D-08 was an explicit user decision that overrides the general QUAL-01 wording.
**How to avoid:** D-08 wins for gallery specifically. QUAL-01 applies at batch level: one failed ContentItem does not stop the batch. The adapter framework should support both patterns -- the gallery adapter implements all-or-nothing internally, while the batch loop implements skip-and-continue.
**Warning signs:** Inconsistent error handling between content types.

### Pitfall 5: orjson bytes vs str
**What goes wrong:** `orjson.dumps()` returns `bytes`, not `str`. Writing to a text-mode file fails. Mixing with `json.dumps()` (which returns `str`) causes type confusion.
**Why it happens:** orjson is optimized for bytes output.
**How to avoid:** Use `Path.write_bytes()` for JSON files (orjson output). Use `Path.write_text()` for markdown. Never mix orjson with stdlib json in the same codebase.
**Warning signs:** TypeError on file write operations.

## Code Examples

### Real ContentItem JSON (verified from content-downloader test-output)

```json
{
  "platform": "douyin",
  "content_id": "7616648694510652672",
  "content_type": "video",
  "title": "Agent\u67b6\u6784\u9009\u578b...",
  "description": "Agent\u67b6\u6784...",
  "author_id": "59130943719",
  "author_name": "\u6162\u5b66AI",
  "publish_time": "2026-03-13T14:00:00+00:00",
  "source_url": "https://www.iesdouyin.com/share/video/...",
  "media_files": ["media/video.mp4"],
  "cover_file": "media/cover.jpg",
  "metadata_file": "metadata.json",
  "likes": 10943,
  "comments": 217,
  "shares": 1970,
  "collects": 9786,
  "views": 0,
  "downloaded_at": "2026-03-30T02:06:53.588772Z"
}
```

### Platform Variations Observed

| Platform | content_type | media_files pattern | cover_file | publish_time format |
|----------|-------------|---------------------|------------|---------------------|
| douyin | video | `["media/video.mp4"]` | `"media/cover.jpg"` | ISO 8601 with timezone |
| xhs | video | `["media/video.mp4"]` | `null` | ISO 8601 UTC |
| wechat_oa | article | `["media/article.html", "media/img_01.jpg", ...]` | `"media/img_01.jpg"` | Unix timestamp string (`"1774760025"`) |
| x | video | `["media/{id}.mp4", "media/{id}.jpg"]` | `"media/{id}.jpg"` | ISO 8601 UTC |

**Key observation:** `publish_time` is inconsistent -- sometimes ISO 8601, sometimes Unix timestamp as string. The ContentItem model should store it as `str` and not attempt datetime parsing. Downstream can parse as needed.

### structured_text.md Template (D-04)

```markdown
# {title}

**Author:** {author_name} | **Platform:** {platform} | **Published:** {publish_time}
**Engagement:** {likes} likes, {comments} comments, {shares} shares

## Summary

{LLM-generated summary -- populated by analysis phase, placeholder in Phase 1}

## Key Takeaways

{LLM-generated takeaways -- populated by analysis phase}

## Full Transcript/Content

{raw extracted text from adapter}

## Analysis

{LLM-generated analysis -- topics, viewpoints, sentiment}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `class Config` | Pydantic v2 `model_config = ConfigDict(...)` | Pydantic 2.0 (2023) | Use ConfigDict, not inner Config class |
| `json.dumps()` for Pydantic | `model.model_dump_json()` or `orjson.dumps(model.model_dump())` | Pydantic 2.0 | model_dump() replaces .dict(), model_dump_json() replaces .json() |
| `@dataclass` for frozen | `BaseModel` with `frozen=True` | Pydantic 2.0 | Pydantic validates + freezes; dataclass only freezes |
| `setuptools setup.py` | `pyproject.toml` with `[build-system]` | PEP 621 (2021) | All config in pyproject.toml, no setup.py |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml [tool.pytest.ini_options]` -- Wave 0 |
| Quick run command | `pytest tests/ -x --no-header -q` |
| Full suite command | `pytest tests/ --cov=content_extractor --cov-report=term-missing` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOUND-01 | Load ContentItem from JSON, validate, handle missing/invalid | unit | `pytest tests/test_loader.py -x` | Wave 0 |
| FOUND-02 | Route by content_type, error on unknown type | unit | `pytest tests/test_router.py -x` | Wave 0 |
| FOUND-03 | Create output models, serialize to JSON, verify schema | unit | `pytest tests/test_models.py -x` | Wave 0 |
| FOUND-04 | Write output files atomically to correct directory | unit | `pytest tests/test_output.py -x` | Wave 0 |
| FOUND-05 | Skip extracted items, reprocess with --force | unit | `pytest tests/test_output.py::test_idempotency -x` | Wave 0 |
| FOUND-06 | Config defaults, CLI arg override | unit | `pytest tests/test_config.py -x` | Wave 0 |
| QUAL-01 | Batch continues after single item failure | integration | `pytest tests/test_output.py::test_batch_error_isolation -x` | Wave 0 |
| QUAL-02 | QualityMetadata populated in ExtractionResult | unit | `pytest tests/test_models.py::test_quality_metadata -x` | Wave 0 |
| QUAL-03 | No partial files left on failure | unit | `pytest tests/test_output.py::test_atomic_write_failure -x` | Wave 0 |
| QUAL-04 | Platform metadata preserved in output | unit | `pytest tests/test_models.py::test_platform_metadata -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x --no-header -q`
- **Per wave merge:** `pytest tests/ --cov=content_extractor --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `pyproject.toml` -- project definition with pytest config, dependencies, src layout
- [ ] `src/content_extractor/__init__.py` -- package init
- [ ] `tests/conftest.py` -- shared fixtures (sample ContentItem dicts, temp directory factory)
- [ ] `tests/fixtures/` -- sample content_item.json files copied from content-downloader test-output
- [ ] All test files listed above (test_models.py, test_loader.py, test_router.py, test_output.py, test_config.py)

## Open Questions

1. **publish_time format inconsistency**
   - What we know: douyin/xhs/x use ISO 8601; wechat_oa uses Unix timestamp as string
   - What's unclear: Whether this is intentional or a bug in content-downloader
   - Recommendation: Store as `str`, do not parse. Add a helper if needed later.

2. **orjson availability on Python 3.13 + macOS ARM64**
   - What we know: orjson generally supports all major platforms; pydantic is installed and working
   - What's unclear: Exact wheel availability for Python 3.13 on Apple Silicon
   - Recommendation: Try `pip install orjson` first. Fall back to stdlib json with a wrapper if it fails. LOW risk.

3. **structured_text.md generation timing**
   - What we know: D-04 defines the format. Phase 1 has no LLM. Summary/analysis sections will be empty.
   - What's unclear: Should Phase 1 generate a partial structured_text.md with only transcript/content, or defer entirely?
   - Recommendation: Phase 1 output.py should have the template and fill what it can (metadata + raw text). Analysis sections filled by Phase 8.

## Sources

### Primary (HIGH confidence)
- content-downloader `models.py` -- ContentItem schema (18 fields), frozen=True pattern
- content-downloader `output.py` -- OutputManager directory layout: `{platform}/{author_id}/{content_id}/`
- content-downloader `adapters/base.py` -- PlatformAdapter Protocol with `@runtime_checkable`
- content-downloader `test-output/` -- 13 real content_item.json files across 4 platforms
- Pydantic v2 installed locally: 2.12.5

### Secondary (MEDIUM confidence)
- `.planning/research/ARCHITECTURE.md` -- project structure, adapter pattern, data flow
- `.planning/research/PITFALLS.md` -- idempotency races, cascading errors, atomic writes
- `.planning/research/STACK.md` -- orjson, typer, rich recommendations with version verification

### Tertiary (LOW confidence)
- orjson Python 3.13 + ARM64 wheel availability -- not independently verified

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- pydantic 2.12.5, pytest 9.0.2, ruff 0.15.7 all verified locally
- Architecture: HIGH -- patterns directly observed in content-downloader source code and real data
- Pitfalls: HIGH -- QUAL-01/D-08 conflict identified and resolved; atomic write pattern well-established

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable domain -- Pydantic/pytest/orjson APIs unlikely to change)

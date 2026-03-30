# Architecture Patterns

**Domain:** Multimodal content extraction pipeline (video/image/article/gallery)
**Researched:** 2026-03-30
**Confidence:** HIGH

## System Overview

```
+------------------------------------------------------------------+
|                         CLI / Library API                          |
|  content-extractor extract <dir>  |  from content_extractor ...   |
+--------------------------+---------------------------------------+
|                      Orchestrator Layer                            |
|  +---------------+  +--------------+  +------------------------+  |
|  | ContentItem   |  |  Idempotency |  |  Progress / Logging    |  |
|  |   Loader      |  |    Guard     |  |  (Rich)                |  |
|  +------+--------+  +------+-------+  +-----------+------------+  |
+---------|------------------|------------------------|--------------+
|                     Router (content_type dispatch)                 |
|            video | image | article | gallery                      |
+-------------------------------------------------------------------+
|                    Layer 1: Raw Extraction                         |
|  +------------+  +---------------+  +----------+  +------------+  |
|  | Video      |  | Image         |  | Article  |  | Gallery    |  |
|  | (faster-   |  | (Claude       |  | (trafi-  |  | (image +   |  |
|  |  whisper)  |  |  vision)      |  |  latura) |  |  synth)    |  |
|  +-----+------+  +-------+------+  +-----+----+  +------+-----+  |
+--------|------------------|---------------|---------------|--------+
|                    Layer 2: LLM Analysis                          |
|  +-------------------------------------------------------------+  |
|  | Claude Analyzer (themes, viewpoints, sentiment, takeaways)   |  |
|  +-------------------------------------------------------------+  |
+-------------------------------------------------------------------+
|                       Output Writer                               |
|  transcript.json  |  analysis.json  |  structured_text.md         |
|  (appended to same ContentItem directory from content-downloader) |
+-------------------------------------------------------------------+
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| **CLI** | Parse args, batch scan, single-dir mode, --force flag | Typer CLI with Rich progress bars |
| **ContentItem Loader** | Read `content_item.json`, validate with Pydantic, resolve media paths | Own Pydantic model (not imported from content-downloader) |
| **Idempotency Guard** | Skip already-extracted items unless --force | Check for `.extraction_complete` marker file |
| **Router** | Dispatch to correct adapter based on `content_type` field | Simple dict mapping |
| **Video Adapter** | Extract audio from video (FFmpeg subprocess), run faster-whisper with VAD, return timestamped transcript | `faster-whisper` + `ffmpeg` subprocess |
| **Image Adapter** | Load/resize image (Pillow), base64-encode, call Claude Vision API, return text description | `anthropic` SDK + `Pillow` |
| **Article Adapter** | Extract main content from HTML, convert to structured markdown | `trafilatura` (not BeautifulSoup -- purpose-built for content extraction) |
| **Gallery Adapter** | Per-image Claude Vision (batched into single API call) + narrative synthesis | Reuse Image Adapter logic + synthesis prompt |
| **Claude Analyzer** | Structured analysis of extracted text (themes, viewpoints, sentiment, takeaways) | `anthropic` SDK with Pydantic structured output |
| **Output Writer** | Write `transcript.json`, `analysis.json`, `structured_text.md` to ContentItem dir | Atomic writes (tmp file + rename) via `orjson` |

## Recommended Project Structure

```
content-extractor/
  pyproject.toml
  src/
    content_extractor/
      __init__.py              # Public API: extract_content(), extract_batch()
      __main__.py              # python -m content_extractor
      cli.py                   # Typer CLI entry point (thin wrapper)
      models.py                # Pydantic models (ContentItem, ExtractionResult, AnalysisResult, TranscriptSegment)
      config.py                # ExtractorConfig (Pydantic Settings)
      loader.py                # ContentItem loading + validation from directory
      router.py                # content_type -> adapter dispatch registry
      adapters/
        __init__.py
        base.py                # ContentAdapter Protocol definition
        video.py               # faster-whisper transcription adapter
        image.py               # Claude Vision single-image adapter
        article.py             # trafilatura HTML cleanup + markdown structuring
        gallery.py             # Multi-image batch + narrative synthesis
      analysis/
        __init__.py
        analyzer.py            # LLM analysis orchestrator
        prompts.py             # All prompt templates (separated for iterability)
      llm/
        __init__.py
        client.py              # Anthropic client factory (CLI Proxy API token loading)
        vision.py              # Shared image encoding + Claude Vision call
      output.py                # Write transcript.json, analysis.json, structured_text.md
  tests/
    conftest.py                # Fixtures: sample ContentItem dirs, mock LLM responses
    test_models.py
    test_loader.py
    test_router.py
    adapters/
      test_video.py
      test_image.py
      test_article.py
      test_gallery.py
    test_analyzer.py
    test_output.py
    test_cli.py
    fixtures/                  # Sample content_item.json, small test media files
```

**File count estimate:** ~20 source files, ~15 test files. Each under 200 lines.

### Structure Rationale

- **adapters/:** Mirrors content-downloader's adapter pattern. Each content type is isolated; adding a new type means adding one file + registering in router.
- **analysis/:** Separated from extraction because it runs after all adapters. Prompts in their own file so they can be iterated without touching logic.
- **llm/:** Shared LLM infrastructure. Both Vision Adapter and Analyzer need Anthropic client; centralizing avoids duplicate token loading logic.
- **models.py at root:** Single source of truth for data shapes. Downstream consumers import from here.
- **src/ layout:** Using `src/content_extractor/` layout for proper package isolation (prevents accidental imports from project root).

## Architectural Patterns

### Pattern 1: Two-Layer Extraction Pipeline

**What:** Layer 1 (raw extraction) produces text from media. Layer 2 (LLM analysis) produces structured insights from that text. The layers are independent and can run separately.
**When to use:** Always -- this is the core architecture.
**Why:** Enables caching (re-analyze without re-transcribing), testability (test extraction without LLM, test analysis with fixture text), and debugging (inspect raw transcript before analysis).

```python
# Layer 1: Raw extraction (adapter-specific)
extraction: ExtractionResult = adapter.extract(content_item, content_dir)

# Layer 2: LLM analysis (uniform across all types)
analysis: AnalysisResult = analyzer.analyze(extraction.raw_text, content_item)
```

### Pattern 2: Adapter Protocol with Registry

**What:** Each content type implements an `Extractor` protocol. A registry maps `content_type` string to adapter instance. Router does zero logic beyond dispatch.
**When to use:** When you have 4+ content types and expect more.

```python
from typing import Protocol, runtime_checkable
from pathlib import Path

@runtime_checkable
class Extractor(Protocol):
    """Protocol all content type extractors must satisfy."""

    content_type: str

    def extract(self, content_dir: Path) -> ExtractionResult:
        """Extract text content from media files in content_dir."""
        ...

# Router
_REGISTRY: dict[str, type[Extractor]] = {
    "video": VideoExtractor,
    "image": ImageExtractor,
    "article": ArticleExtractor,
    "gallery": GalleryExtractor,
}

def get_extractor(content_type: str) -> Extractor:
    cls = _REGISTRY.get(content_type)
    if cls is None:
        raise UnsupportedContentTypeError(content_type)
    return cls()
```

### Pattern 3: Idempotent Output with Atomic Writes

**What:** Write to temp file, rename on completion. Check `.extraction_complete` marker for idempotency.
**When to use:** Always. Whisper transcription is expensive; re-running should not redo completed work.

```python
def write_output(content_dir: Path, result: ExtractionResult) -> None:
    tmp = content_dir / "transcript.json.tmp"
    final = content_dir / "transcript.json"
    tmp.write_bytes(orjson.dumps(result.model_dump()))
    tmp.rename(final)  # atomic on same filesystem

def mark_complete(content_dir: Path) -> None:
    (content_dir / ".extraction_complete").touch()

def should_process(content_dir: Path, force: bool = False) -> bool:
    if force:
        return True
    return not (content_dir / ".extraction_complete").exists()
```

### Pattern 4: Lazy Singleton for Whisper Model

**What:** Load Whisper model once on first use, reuse across all video extractions in a batch.
**When to use:** Batch processing. Model loading takes 5-10 seconds and ~1.6GB memory.

```python
class VideoExtractor:
    def __init__(self) -> None:
        self._model: WhisperModel | None = None

    def _get_model(self, model_size: str = "turbo") -> WhisperModel:
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                model_size,
                device="cpu",
                compute_type="int8",
            )
        return self._model
```

### Pattern 5: Immutable Result Objects

**What:** ExtractionResult and AnalysisResult are frozen Pydantic models. Adapters create new instances, never mutate.
**When to use:** Always. Prevents hidden side effects when gallery adapter composes results from multiple image adapter calls.

```python
class ExtractionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    content_type: str
    raw_text: str
    transcript_segments: tuple[TranscriptSegment, ...] = ()
    media_descriptions: tuple[MediaDescription, ...] = ()
    language: str = "unknown"
    confidence: float = 0.0
    processing_time_seconds: float = 0.0
```

### Pattern 6: Thin CLI Wrapper

**What:** CLI (Typer) parses args, creates config, calls library, displays output. Zero business logic in CLI layer.
**When to use:** Always. Library is the product. CLI is one interface.

```python
import typer
from rich.console import Console

app = typer.Typer()
console = Console()

@app.command()
def extract(
    path: Path,
    force: bool = False,
    whisper_model: str = "turbo",
) -> None:
    config = ExtractorConfig(force_reprocess=force, whisper_model=whisper_model)
    result = extract_content(path, config)  # library call
    console.print(f"Extracted {result.content_type}: {len(result.raw_text)} chars")
```

## Data Flow

### Single ContentItem Extraction

```
ContentItem directory on disk
    |
    v
[Loader] reads content_item.json -> ContentItem (Pydantic model)
    |
    v
[Idempotency Guard] checks .extraction_complete marker
    |                                    |
    | (missing)                          | (exists, no --force)
    v                                    v
[Router] dispatches by content_type    SKIP (log + continue)
    |
    +--> video:   [FFmpeg extract audio] -> [faster-whisper + VAD] -> transcript segments
    +--> image:   [Pillow load + resize] -> [base64 encode] -> [Claude Vision] -> description
    +--> article: [trafilatura extract]  -> markdown text
    +--> gallery: [batch images in single Claude Vision call] -> [synthesis prompt] -> narrative
    |
    v
[Output Writer] writes transcript.json + structured_text.md (atomic)
    |
    v
[Analyzer] reads extracted text -> [Claude LLM structured output] -> AnalysisResult
    |
    v
[Output Writer] writes analysis.json (atomic)
    |
    v
[Mark Complete] writes .extraction_complete marker
```

### Batch Flow

```
CLI: content-extractor batch /path/to/output
    |
    v
[Scanner] walks {output_dir}/{platform}/{author_id}/{content_id}/
    |
    v
[Filter] only dirs with content_item.json
    |
    v
[Sequential loop with Rich progress bar]:
    for each ContentItem dir:
        Load -> Guard -> Extract -> Analyze -> Write -> Mark Complete
        Log: "[3/47] douyin/author123/video456 -- video -- OK (12.3s)"
```

Note: Sequential processing, not parallel. Whisper saturates CPU on its own; Claude API has rate limits. Parallelism adds complexity for minimal gain in offline batch context.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Coupling Extraction and Analysis

**What:** Run Whisper then immediately feed result to Claude in a single function.
**Why bad:** If analysis prompt changes, must re-transcribe. If Whisper fails, lose partial results. Testing requires both services.
**Instead:** Two distinct layers with filesystem as intermediate. Layer 1 writes transcript.json. Layer 2 reads it.

### Anti-Pattern 2: Importing content-downloader as Dependency

**What:** `from content_downloader.models import ContentItem`
**Why bad:** Creates hard coupling. If content-downloader changes its model, extractor breaks.
**Instead:** Define own ContentItem model that reads content_item.json. Use JSON as contract, not Python class. Set `model_config = {"extra": "ignore"}` so new upstream fields don't break parsing.

### Anti-Pattern 3: Loading Whisper Model Per File

**What:** Call `WhisperModel("turbo")` inside each video extraction.
**Why bad:** Model loading takes 5-10 seconds. In batch of 100 videos, that wastes 8-15 minutes.
**Instead:** Lazy singleton pattern. Load once, reuse across batch.

### Anti-Pattern 4: One API Call Per Gallery Image

**What:** Send each gallery image as separate Claude Vision call.
**Why bad:** 20-image gallery = 20 API calls, hits rate limits, loses gallery context.
**Instead:** Batch images into single API call (Claude supports up to 20 images per message).

### Anti-Pattern 5: Storing Output Outside ContentItem Directory

**What:** Create separate `extractions/` directory tree.
**Why bad:** Downstream needs two paths. Moving/archiving requires syncing two trees.
**Instead:** Append output files to ContentItem directory as PROJECT.md specifies.

## Integration Points

### External Services

| Service | Integration | Notes |
|---------|-------------|-------|
| **faster-whisper (local)** | `WhisperModel("turbo", device="cpu", compute_type="int8")` | Model downloads ~1.6GB on first run. CPU-only on macOS. |
| **Claude Vision API** | `anthropic.Anthropic(api_key=token)` with base64 image content blocks | Token from `~/.cli-proxy-api/claude-*.json`. Max 5MB/image recommended. |
| **Claude Text API** | Same client, text-only messages for analysis | Reuse same client instance. |
| **FFmpeg (system)** | `subprocess.run(["ffmpeg", ...])` for audio extraction | Only system dependency. Extract to WAV (PCM s16le, mono, 16kHz). |

### Internal Boundaries

| Boundary | Communication | Contract |
|----------|---------------|----------|
| content-downloader -> content-extractor | Filesystem (ContentItem directories) | content_item.json schema |
| Layer 1 -> Layer 2 | ExtractionResult Pydantic model | Analysis only sees text, never raw media |
| content-extractor -> downstream | Filesystem (transcript.json, analysis.json, structured_text.md) | JSON schemas defined by Pydantic models |

## Build Order (Dependency Chain)

```
Phase 1: Foundation (no external deps needed for testing)
   models.py -> config.py -> loader.py -> router.py -> output.py -> cli.py (skeleton)

Phase 2: Article Adapter (simplest, proves the pattern)
   adapters/article.py (only needs trafilatura)

Phase 3: LLM Infrastructure + Image Adapter
   llm/client.py -> llm/vision.py -> adapters/image.py

Phase 4: Video Adapter (most complex, independent of LLM)
   adapters/video.py (faster-whisper + FFmpeg + VAD)

Phase 5: Gallery Adapter + Analysis Layer
   adapters/gallery.py (reuses llm/vision.py + synthesis)
   analysis/prompts.py -> analysis/analyzer.py

Phase 6: CLI Polish + Batch Mode
   cli.py (progress bars, error summaries, batch scanning)
```

**Rationale:** Foundation first (everything depends on models). Article adapter proves the pattern without external service deps. LLM client before image/gallery. Video is complex and independent of LLM -- can even parallel with Phase 3. Analysis layer last because it consumes all adapter output.

## Sources

- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper) -- CTranslate2 backend, API reference
- [Anthropic Claude Vision docs](https://platform.claude.com/docs/en/build-with-claude/vision) -- image encoding, constraints
- [trafilatura docs](https://trafilatura.readthedocs.io/en/latest/) -- article extraction API
- [Typer docs](https://typer.tiangolo.com/) -- CLI framework patterns
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) -- configuration management
- content-downloader source code (local) -- adapter pattern, directory structure conventions

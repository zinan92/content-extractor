# Technology Stack

**Project:** content-extractor
**Researched:** 2026-03-30

## Recommended Stack

### Core Runtime

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.13+ | Runtime | Constraint from content-downloader compatibility. Pydantic, CTranslate2, and all key deps now support 3.13. |
| Pydantic | 2.12+ | Data models, validation, serialization | Project constraint. Defines ContentItem, TranscriptSegment, AnalysisResult schemas. Structured output from LLM maps directly to Pydantic models. |
| pytest | 8.x | Testing | Project constraint. Use with pytest-asyncio if any async code needed. |

### Audio/Video Processing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| faster-whisper | 1.2.1 | Speech-to-text transcription | 4x faster than openai-whisper with identical accuracy. CTranslate2 4.7.1 backend now supports Python 3.13 (resolved Feb 2026). INT8 quantization on CPU means fast inference without GPU. Turbo model available via `deepdml/faster-whisper-large-v3-turbo-ct2` on HuggingFace. |
| ffmpeg (system) | 7.x | Audio extraction from video | System dependency. Extract audio track to WAV before feeding to Whisper. No Python wrapper needed -- use `subprocess.run()` with a thin helper function. Simpler than ffmpeg-python or pydub for a single operation (extract audio). |

**Why faster-whisper over openai-whisper:**
- Same Whisper model weights, same accuracy
- 4x faster inference via CTranslate2 C++ backend
- Lower memory usage (INT8 quantization)
- `openai-whisper` pulls in full PyTorch (~2GB); faster-whisper uses CTranslate2 (~200MB)
- Both now support Python 3.13, so compatibility is no longer a differentiator

**Why not ffmpeg-python or pydub:**
We need exactly one FFmpeg operation: extract audio from video to WAV. A 3-line subprocess call is cleaner than adding a dependency. If audio manipulation grows in scope later, add pydub then.

### Image Analysis (LLM Vision)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| anthropic | 0.86+ | Claude API client for vision + text analysis | Official SDK. Supports vision (base64 images), structured output via Pydantic models, streaming. Connects to CLI Proxy API by setting `base_url` to local proxy endpoint. |

**How CLI Proxy API works:**
The project uses `~/.cli-proxy-api/claude-*.json` which provides Anthropic API tokens from the Max plan. The `anthropic` SDK connects by overriding `base_url` and `api_key` from these config files. Zero additional cost.

**Why not instructor or pydantic-ai:**
The `anthropic` SDK natively supports structured output (JSON mode + Pydantic schema). Adding instructor or pydantic-ai is an unnecessary abstraction layer for direct Anthropic API calls. Keep the dependency surface small.

### Article Cleaning & Text Extraction

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| trafilatura | 2.0.0 | HTML to clean text extraction | Purpose-built for article extraction. F1 score 0.960 vs BeautifulSoup's 0.665 on article extraction benchmarks. Strips ads, nav, boilerplate automatically. Outputs clean markdown. Supports Python 3.8-3.13. |

**Why not BeautifulSoup4:**
BS4 is a general HTML parser -- it has no concept of "article body" vs "navigation" vs "ad". Trafilatura uses heuristics to identify the main content automatically. For article cleaning, trafilatura does in one line what BS4 requires 50+ lines of custom logic.

**Why not readability-lxml:**
Trafilatura consistently outperforms readability-lxml in benchmarks and is more actively maintained (2.0.0 released Dec 2024).

### CLI Interface

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| typer | 0.24+ | CLI framework | Built on Click but uses Python type hints for argument definition. Pairs naturally with Pydantic (both type-hint-driven). Less boilerplate than Click. Auto-generates --help. |
| rich | 14.1+ | Terminal output, progress bars, logging | Progress bars for batch processing (track Whisper transcription, image analysis). Colored logging. Typer uses Rich internally already. |

**Why Typer over Click:**
Both are production-ready. Typer generates CLI from function signatures with type hints -- matches the Pydantic-first philosophy of this project. Click requires decorators for every parameter. Typer is built on Click anyway, so Click's ecosystem (plugins, testing) remains available.

**Why not argparse:**
Argparse is stdlib but verbose. For a tool with subcommands (`extract`, `batch`, `analyze`), Typer provides a cleaner DX with auto-completion and better help formatting.

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pillow | 11.x | Image loading, format detection, resizing before vision API | Always -- needed to read image metadata, resize large images before base64 encoding for Claude vision (max 5MB per image). |
| orjson | 3.10+ | Fast JSON serialization | For writing transcript.json and analysis.json. 10x faster than stdlib json. Handles Pydantic model serialization natively. |

### Dev Dependencies

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| pytest | 8.x | Test runner | Project constraint |
| pytest-cov | 5.x | Coverage reporting | 80% coverage target |
| ruff | 0.9+ | Linting + formatting | Single tool replaces flake8 + black + isort. Fast (Rust-based). Industry standard for new Python projects in 2025+. |
| mypy | 1.14+ | Type checking | Pydantic plugin for mypy ensures model validation at type-check time. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Whisper | faster-whisper | openai-whisper | 4x slower, pulls in PyTorch (~2GB), higher memory usage |
| Whisper | faster-whisper | whisper.cpp | C++ binary -- harder to integrate as Python library, less Pythonic API |
| HTML cleaning | trafilatura | BeautifulSoup4 | No content detection heuristics, F1=0.665 vs 0.960 |
| HTML cleaning | trafilatura | readability-lxml | Lower benchmark scores, less actively maintained |
| CLI | typer | click | More boilerplate, decorator-based vs type-hint-based |
| CLI | typer | argparse | Verbose, no auto-completion, poor subcommand UX |
| LLM SDK | anthropic | instructor | Unnecessary abstraction -- anthropic SDK has native structured output |
| LLM SDK | anthropic | pydantic-ai | Multi-provider abstraction we don't need -- we only use Claude |
| Audio extract | subprocess+ffmpeg | pydub | Overkill for single audio extraction operation |
| Audio extract | subprocess+ffmpeg | ffmpeg-python | Unmaintained (last release 2022), adds dependency for 3 lines of code |
| JSON | orjson | stdlib json | 10x slower, no native Pydantic support |
| Formatter | ruff | black+flake8+isort | 3 tools vs 1, ruff is faster and covers all three |

## System Dependencies

```bash
# macOS (Homebrew)
brew install ffmpeg

# Verify
ffmpeg -version
```

FFmpeg is the only system dependency. Everything else is pure Python.

## Installation

```bash
# Core
pip install faster-whisper anthropic trafilatura typer rich Pillow orjson pydantic

# Dev dependencies
pip install -D pytest pytest-cov ruff mypy

# Or with a pyproject.toml (preferred)
pip install -e ".[dev]"
```

## Version Pinning Strategy

Pin major.minor in pyproject.toml, allow patch updates:

```toml
[project]
requires-python = ">=3.13"
dependencies = [
    "faster-whisper>=1.2,<2",
    "anthropic>=0.86,<1",
    "trafilatura>=2.0,<3",
    "typer>=0.24,<1",
    "rich>=14,<15",
    "Pillow>=11,<12",
    "orjson>=3.10,<4",
    "pydantic>=2.12,<3",
]

[project.optional-dependencies]
dev = [
    "pytest>=8,<9",
    "pytest-cov>=5,<6",
    "ruff>=0.9",
    "mypy>=1.14",
]
```

## Confidence Assessment

| Technology | Confidence | Reason |
|------------|------------|--------|
| faster-whisper | HIGH | Verified PyPI version, CTranslate2 Python 3.13 support confirmed via PyPI (4.7.1, Feb 2026), turbo model available on HuggingFace |
| anthropic SDK | HIGH | Verified PyPI 0.86.0 (Mar 2026), vision + structured output confirmed in official docs |
| trafilatura | HIGH | Verified PyPI 2.0.0, benchmark data from official docs, Python 3.13 supported |
| typer | HIGH | Verified PyPI 0.24.1 (Feb 2026), actively maintained by tiangolo |
| rich | HIGH | Verified 14.1.0 (Feb 2026), standard terminal UI library |
| Pillow | MEDIUM | Version not independently verified, but Pillow has supported every Python version historically |
| orjson | MEDIUM | Known fast JSON library, version from training data not independently verified |
| ruff | HIGH | Industry standard, Rust-based, actively maintained |

## Sources

- [faster-whisper PyPI](https://pypi.org/project/faster-whisper/) -- v1.2.1, Python >=3.9
- [CTranslate2 PyPI](https://pypi.org/project/ctranslate2/) -- v4.7.1, Python 3.9-3.14, macOS ARM64 supported
- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper) -- turbo model support confirmed
- [deepdml/faster-whisper-large-v3-turbo-ct2](https://huggingface.co/deepdml/faster-whisper-large-v3-turbo-ct2) -- pre-converted turbo model
- [anthropic PyPI](https://pypi.org/project/anthropic/) -- v0.86.0
- [Claude Vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)
- [trafilatura PyPI](https://pypi.org/project/trafilatura/) -- v2.0.0
- [trafilatura benchmarks](https://trafilatura.readthedocs.io/en/latest/evaluation.html) -- F1=0.960
- [typer PyPI](https://pypi.org/project/typer/) -- v0.24.1
- [rich docs](https://rich.readthedocs.io/en/latest/progress.html) -- v14.1.0
- [Modal: Choosing Whisper variants](https://modal.com/blog/choosing-whisper-variants) -- faster-whisper vs alternatives

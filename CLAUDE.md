<!-- GSD:project-start source:PROJECT.md -->
## Project

**content-extractor**

Content pipeline Step 03: 多模态内容提取器。接收 content-downloader 输出的 ContentItem 目录（视频/图片/文章/gallery），通过 adapter 模式提取结构化文本。视频用本地 Whisper turbo 转录，图片用 Claude vision (CLI Proxy API) 识别，文章做清洗+结构化。输出包含转录文本、结构化分析（主题/观点/情绪/takeaway）和 markdown 格式的完整内容。CLI + Python library 形态，无 HTTP 服务。

**Core Value:** 把原始多媒体内容变成可被下游（curator/rewriter）消费的结构化文本 — 没有 extractor，整条 content pipeline 后面的步骤全都没有输入。

### Constraints

- **Tech stack**: Python 3.13+ / Pydantic / pytest — 与 content-downloader 保持一致
- **LLM 成本**: 必须走 CLI Proxy API，不额外付费
- **Whisper**: 本地运行，默认 turbo 模型 (~1.6GB)，可通过参数切换
- **输出兼容**: 输出目录结构不能破坏 content-downloader 已有的文件布局，新文件追加到 ContentItem 目录中
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

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
- Same Whisper model weights, same accuracy
- 4x faster inference via CTranslate2 C++ backend
- Lower memory usage (INT8 quantization)
- `openai-whisper` pulls in full PyTorch (~2GB); faster-whisper uses CTranslate2 (~200MB)
- Both now support Python 3.13, so compatibility is no longer a differentiator
### Image Analysis (LLM Vision)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| anthropic | 0.86+ | Claude API client for vision + text analysis | Official SDK. Supports vision (base64 images), structured output via Pydantic models, streaming. Connects to CLI Proxy API by setting `base_url` to local proxy endpoint. |
### Article Cleaning & Text Extraction
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| trafilatura | 2.0.0 | HTML to clean text extraction | Purpose-built for article extraction. F1 score 0.960 vs BeautifulSoup's 0.665 on article extraction benchmarks. Strips ads, nav, boilerplate automatically. Outputs clean markdown. Supports Python 3.8-3.13. |
### CLI Interface
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| typer | 0.24+ | CLI framework | Built on Click but uses Python type hints for argument definition. Pairs naturally with Pydantic (both type-hint-driven). Less boilerplate than Click. Auto-generates --help. |
| rich | 14.1+ | Terminal output, progress bars, logging | Progress bars for batch processing (track Whisper transcription, image analysis). Colored logging. Typer uses Rich internally already. |
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
# macOS (Homebrew)
# Verify
## Installation
# Core
# Dev dependencies
# Or with a pyproject.toml (preferred)
## Version Pinning Strategy
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->

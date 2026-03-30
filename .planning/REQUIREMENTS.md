# Requirements: content-extractor

**Defined:** 2026-03-30
**Core Value:** 把原始多媒体内容变成可被下游消费的结构化文本

## v1 Requirements

### Foundation

- [ ] **FOUND-01**: Load and validate ContentItem from `content_item.json` using own Pydantic model (no import from content-downloader)
- [ ] **FOUND-02**: Route content to correct adapter based on `content_type` field (video/image/article/gallery)
- [ ] **FOUND-03**: Define standardized output Pydantic models for transcript, analysis, and extraction result
- [ ] **FOUND-04**: Write output files (`transcript.json`, `analysis.json`, `structured_text.md`) to ContentItem directory
- [ ] **FOUND-05**: Skip already-extracted content by checking output file existence (idempotent); `--force` flag to override
- [ ] **FOUND-06**: Configuration system for Whisper model, LLM settings, and default behaviors

### Article Extraction

- [ ] **ARTC-01**: Clean HTML content using trafilatura, output structured markdown
- [ ] **ARTC-02**: Preserve article structure (headings, lists, emphasis) in markdown output
- [ ] **ARTC-03**: Extract article metadata (author, date, word count) from cleaned content

### LLM Infrastructure

- [ ] **LLM-01**: Load CLI Proxy API token from `~/.cli-proxy-api/claude-*.json` (access_token field)
- [ ] **LLM-02**: Fall back to `ANTHROPIC_API_KEY` env var if CLI Proxy API token not found (for CI)
- [ ] **LLM-03**: Handle token expiration gracefully with clear error message
- [ ] **LLM-04**: Rate limit awareness — respect API limits, back off on 429 responses

### Image Extraction

- [ ] **IMG-01**: Send image to Claude vision for OCR + visual description in a single call
- [ ] **IMG-02**: Handle Chinese text overlays common on Xiaohongshu images
- [ ] **IMG-03**: Return structured result with `ocr_text`, `visual_description`, and `confidence`

### Video Extraction

- [ ] **VID-01**: Extract audio from video using FFmpeg (handle various codecs from Douyin/XHS)
- [ ] **VID-02**: Run VAD (Voice Activity Detection) preprocessing to filter non-speech segments
- [ ] **VID-03**: Transcribe audio using faster-whisper with explicit language parameter
- [ ] **VID-04**: Output timestamped transcript segments with confidence scores
- [ ] **VID-05**: Default to turbo model, support `--whisper-model` flag for model selection
- [ ] **VID-06**: Audio preprocessing — volume normalization before transcription
- [ ] **VID-07**: Detect and flag low-confidence transcriptions (hallucination guard)

### Gallery Extraction

- [ ] **GLRY-01**: Extract each image in gallery using Image adapter
- [ ] **GLRY-02**: Batch images into minimal API calls to respect rate limits
- [ ] **GLRY-03**: Synthesize per-image descriptions into coherent gallery narrative via LLM

### LLM Analysis

- [ ] **ANLYS-01**: Analyze extracted text to identify main themes/topics
- [ ] **ANLYS-02**: Extract core viewpoints/arguments from content
- [ ] **ANLYS-03**: Assess emotional tone/sentiment of content
- [ ] **ANLYS-04**: Generate actionable takeaways from content
- [ ] **ANLYS-05**: Output structured `analysis.json` with all analysis dimensions
- [ ] **ANLYS-06**: Generate human-readable `structured_text.md` combining transcript + analysis

### CLI & Library

- [ ] **CLI-01**: Single-item extraction: `content-extractor extract /path/to/content_item/`
- [ ] **CLI-02**: Batch extraction: `content-extractor extract-batch /path/to/output_dir/`
- [ ] **CLI-03**: Progress bar for batch mode (Rich/tqdm)
- [ ] **CLI-04**: Error summary at end of batch run
- [ ] **CLI-05**: Python library API: `extract(path) -> ExtractionResult` and `extract_batch(dir) -> list[ExtractionResult]`

### Quality & Reliability

- [ ] **QUAL-01**: Per-item error isolation — one failed image in gallery does not fail the whole item
- [ ] **QUAL-02**: Extraction quality metadata per item (confidence, language, word count, processing time)
- [ ] **QUAL-03**: Atomic file writes — partial output never left behind on failure
- [ ] **QUAL-04**: Preserve platform metadata (author, date, engagement metrics) in output

## v2 Requirements

### Enhanced Video

- **VID-V2-01**: Keyframe extraction (2-3 frames) for visual context alongside transcript
- **VID-V2-02**: Speaker diarization for multi-speaker content (podcast/interview)

### Enhanced Analysis

- **ANLYS-V2-01**: Content-type-specific analysis prompts (different for tutorial vs opinion vs news)
- **ANLYS-V2-02**: Cross-reference analysis with platform engagement metrics

### Operational

- **OPS-V2-01**: Structured logging with configurable verbosity
- **OPS-V2-02**: Export extraction statistics (success rate, avg time, model usage)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time streaming transcription | All source content already downloaded — offline batch is simpler |
| HTTP API / FastAPI service | Pipeline uses Python imports directly; HTTP adds unnecessary overhead |
| Translation (Chinese<>English) | Translation belongs in content-rewriter, not extraction |
| Custom fine-tuned Whisper model | Marginal improvement over large-v3; massive maintenance cost |
| PDF/document extraction | Target platforms produce video/image/article/gallery only |
| Full video frame analysis | Extremely expensive; cover + metadata sufficient for short-form |
| Content categorization/tagging | Blurs extraction/curation boundary; curator's job |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1: Foundation & Data Models | Pending |
| FOUND-02 | Phase 1: Foundation & Data Models | Pending |
| FOUND-03 | Phase 1: Foundation & Data Models | Pending |
| FOUND-04 | Phase 1: Foundation & Data Models | Pending |
| FOUND-05 | Phase 1: Foundation & Data Models | Pending |
| FOUND-06 | Phase 1: Foundation & Data Models | Pending |
| QUAL-01 | Phase 1: Foundation & Data Models | Pending |
| QUAL-02 | Phase 1: Foundation & Data Models | Pending |
| QUAL-03 | Phase 1: Foundation & Data Models | Pending |
| QUAL-04 | Phase 1: Foundation & Data Models | Pending |
| ARTC-01 | Phase 2: Article Adapter | Pending |
| ARTC-02 | Phase 2: Article Adapter | Pending |
| ARTC-03 | Phase 2: Article Adapter | Pending |
| LLM-01 | Phase 3: LLM Infrastructure | Pending |
| LLM-02 | Phase 3: LLM Infrastructure | Pending |
| LLM-03 | Phase 3: LLM Infrastructure | Pending |
| LLM-04 | Phase 3: LLM Infrastructure | Pending |
| IMG-01 | Phase 4: Image Adapter | Pending |
| IMG-02 | Phase 4: Image Adapter | Pending |
| IMG-03 | Phase 4: Image Adapter | Pending |
| VID-01 | Phase 5: Video Core | Pending |
| VID-03 | Phase 5: Video Core | Pending |
| VID-04 | Phase 5: Video Core | Pending |
| VID-05 | Phase 5: Video Core | Pending |
| VID-02 | Phase 6: Video Quality | Pending |
| VID-06 | Phase 6: Video Quality | Pending |
| VID-07 | Phase 6: Video Quality | Pending |
| GLRY-01 | Phase 7: Gallery Adapter | Pending |
| GLRY-02 | Phase 7: Gallery Adapter | Pending |
| GLRY-03 | Phase 7: Gallery Adapter | Pending |
| ANLYS-01 | Phase 8: LLM Analysis | Pending |
| ANLYS-02 | Phase 8: LLM Analysis | Pending |
| ANLYS-03 | Phase 8: LLM Analysis | Pending |
| ANLYS-04 | Phase 8: LLM Analysis | Pending |
| ANLYS-05 | Phase 8: LLM Analysis | Pending |
| ANLYS-06 | Phase 8: LLM Analysis | Pending |
| CLI-01 | Phase 9: CLI & Library API | Pending |
| CLI-02 | Phase 9: CLI & Library API | Pending |
| CLI-03 | Phase 9: CLI & Library API | Pending |
| CLI-04 | Phase 9: CLI & Library API | Pending |
| CLI-05 | Phase 9: CLI & Library API | Pending |

**Coverage:**
- v1 requirements: 39 total
- Mapped to phases: 39 (across 9 phases)
- Unmapped: 0

---
*Requirements defined: 2026-03-30*
*Last updated: 2026-03-30 after roadmap creation (9-phase structure)*

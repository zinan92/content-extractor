# Feature Research

**Domain:** Multimodal content extraction pipeline (video/image/article/gallery to structured text)
**Researched:** 2026-03-30
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features that the downstream pipeline (content-curator, content-rewriter) requires to function. Missing these breaks the pipeline.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Video audio transcription (Whisper) | Core purpose — most content from Douyin/XHS is video | MEDIUM | Use faster-whisper (CTranslate2 backend) for 4x speed over vanilla Whisper with same accuracy. Turbo model for speed, large-v3 for quality fallback |
| Timestamped transcript segments | Downstream needs to locate moments in video; essential for clip extraction | LOW | faster-whisper provides segment-level timestamps out of the box. Word-level via WhisperX if needed later |
| Chinese + English language support | Target platforms (Douyin, XHS, WeChat OA) are primarily Chinese; X/Twitter is English | MEDIUM | Whisper large-v3/turbo handles Mandarin well but not perfectly. Must specify `language="zh"` explicitly rather than relying on auto-detect — auto-detect sometimes misidentifies dialect or outputs Traditional when Simplified expected |
| Image text extraction (OCR via Claude vision) | XHS posts are image-heavy with text overlays; WeChat articles have embedded images | MEDIUM | Claude vision handles Chinese OCR well. Send image before text prompt. Request structured output format explicitly |
| Image visual description | Gallery/image posts need context beyond just OCR — what is shown, product, scene | LOW | Single Claude vision call can do both OCR + description together. Keep prompts specific |
| Article HTML cleaning + structuring | WeChat OA articles come as messy HTML with ads, tracking, formatting cruft | LOW | Trafilatura is the clear winner — best mean F1 (0.937), all-Python, outputs Markdown/JSON/XML. No browser needed |
| Standardized output format | Downstream consumers need predictable schema to parse | MEDIUM | Pydantic models for transcript.json + analysis.json + structured_text.md per ContentItem |
| Idempotent processing | Re-running on same content must not duplicate or corrupt; essential for pipeline reliability | LOW | Check for output files existence before processing. Skip if present, process if missing. `--force` flag to override |
| CLI entry point (single item + batch) | Operator needs to run extraction manually during development and debugging | LOW | Click or Typer CLI. Two modes: `extract /path/to/content_item/` and `extract-batch /path/to/output_dir/` |
| Python library interface | Other pipeline steps import directly; no HTTP overhead | LOW | Public API: `extract(content_item_path) -> ExtractionResult` and `extract_batch(output_dir) -> List[ExtractionResult]` |
| Error handling + partial results | One failed image in a gallery of 20 should not fail the whole item | MEDIUM | Per-item and per-media-file error isolation. Return partial results with error annotations. Never silently swallow failures |
| Content type routing (adapter pattern) | Different content types (video/image/article/gallery) need different extraction strategies | LOW | Adapter registry keyed on `ContentItem.content_type`. Clean separation of concerns |

### Differentiators (Competitive Advantage)

Features that make this extractor more useful than a naive "run Whisper + dump text" approach. These create value for the curator/rewriter downstream.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| LLM structured analysis layer | Extract themes, key arguments, sentiment, actionable takeaways — not just raw text. This is what turns "transcription" into "intelligence" | HIGH | Claude via CLI Proxy API. Separate from extraction so raw transcript is always available even if analysis fails. Cost ~zero with Max plan |
| Metadata preservation + enrichment | Carry forward platform metadata (author, date, engagement metrics) alongside extracted content | LOW | Read content_item.json, merge into output. Downstream curator needs this for ranking |
| Gallery narrative synthesis | For multi-image posts (common on XHS), synthesize individual image descriptions into a coherent narrative | MEDIUM | After per-image Claude vision, one more LLM call to synthesize. XHS "photo essay" posts lose all meaning without this |
| Configurable Whisper model selection | Different quality/speed tradeoffs for different use cases (quick scan vs archival quality) | LOW | CLI flag `--whisper-model turbo|large-v3|small`. Default turbo. Config file override |
| Extraction quality metadata | Confidence scores, language detected, word count, processing time — lets curator filter low-quality extractions | LOW | Add to output JSON. Whisper provides language probability; track processing duration; count tokens |
| Resume/checkpoint for batch processing | Large batch runs (1000+ items) should be resumable after interruption | LOW | Idempotency already handles this — incomplete items (missing output files) get reprocessed on next run |
| Progress reporting for batch mode | Operator needs visibility into batch processing status | LOW | tqdm progress bar for CLI. Callback interface for library usage |
| Audio preprocessing (noise reduction, normalization) | Douyin/XHS videos often have background music competing with speech | HIGH | FFmpeg audio extraction with volume normalization. Optional noise reduction via noisereduce library. Significant quality improvement for music-heavy short videos |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time streaming transcription | Sounds faster, more modern | Adds massive complexity (WebSocket, chunking, partial results). All source content is already downloaded — offline batch is simpler and more reliable | Batch processing with progress reporting. Speed comes from faster-whisper, not streaming |
| Speaker diarization (who said what) | Useful for podcast/interview content | WhisperX adds this but is poorly maintained. Adds pyannote dependency (heavy). Most Douyin/XHS content is single-speaker | Defer entirely. If needed later, add as optional WhisperX adapter. Do not make it core |
| Full video frame-by-frame analysis | Extract visual information from every frame | Extremely expensive (API calls per frame), slow, mostly redundant for short-form content. A 60s video at 1fps = 60 vision API calls | Extract cover image + 2-3 keyframes max. Use video metadata (title, description) for context |
| Translation (Chinese to English or vice versa) | Bilingual pipeline seems useful | Translation is a rewriting concern, not extraction. Mixing concerns makes both harder. Whisper translate mode loses Chinese original | Extract in original language only. Translation belongs in content-rewriter step |
| Custom fine-tuned Whisper model | Better accuracy for Chinese content | Training data collection, GPU requirements, ongoing maintenance. Marginal improvement over large-v3 for general Mandarin | Use large-v3 with explicit language parameter. Fine-tune only if accuracy becomes a proven blocker |
| HTTP API / FastAPI service | "Everything should be a service" | Pipeline steps call each other via Python imports. HTTP adds latency, deployment complexity, error handling overhead — all for zero benefit in this architecture | Python library with clean public API. Import directly |
| Automatic content categorization/tagging | Seems useful to tag content during extraction | Blurs boundary between extraction and curation. Curator downstream has full context (all items) to make relative judgments | Keep extraction focused on text extraction + basic analysis. Categorization is curator's job |
| PDF/document extraction | "While we're extracting content..." | Scope creep. Target platforms produce video/image/article/gallery, not PDFs. Different problem domain entirely | Out of scope. Build separately if ever needed |

## Feature Dependencies

```
[Content type routing (adapter pattern)]
    |
    |---> [Video adapter: Whisper transcription]
    |         |---> [Timestamped segments]
    |         |---> [Audio preprocessing] (optional, enhances)
    |
    |---> [Image adapter: Claude vision OCR + description]
    |
    |---> [Article adapter: Trafilatura cleaning]
    |
    |---> [Gallery adapter: per-image vision + narrative synthesis]
              |---> requires [Image adapter]
              |---> requires [LLM structured analysis] (for synthesis)

[Standardized output format (Pydantic models)]
    |---> required by ALL adapters (they output to this schema)
    |---> required by [LLM structured analysis] (input + output)

[LLM structured analysis]
    |---> requires raw text from ANY adapter (runs after extraction)
    |---> requires [CLI Proxy API connection]

[Idempotent processing]
    |---> requires [Standardized output format] (checks for output files)

[CLI entry point]
    |---> requires [Content type routing]
    |---> requires [Idempotent processing]

[Python library interface]
    |---> requires [Content type routing]
    |---> same core logic as CLI, different entry point

[Metadata preservation]
    |---> independent, reads content_item.json
    |---> enhances ALL adapter outputs
```

### Dependency Notes

- **Gallery adapter requires Image adapter:** Gallery is multiple images processed individually, then synthesized. Reuse image extraction logic.
- **LLM analysis requires raw extraction:** Analysis runs on extracted text, not raw media. Must complete extraction first.
- **Standardized output is foundational:** Define Pydantic models before implementing any adapter. Everything flows through these schemas.
- **CLI and library share core logic:** CLI is a thin wrapper around the library. Build library first, CLI second.

## MVP Definition

### Launch With (v1)

Minimum to unblock the pipeline — curator/rewriter need input.

- [ ] Pydantic output models (transcript.json, analysis.json, structured_text.md schemas) — everything depends on this
- [ ] Content type router + adapter registry — dispatch to correct handler
- [ ] Video adapter with faster-whisper (turbo model, Chinese + English) — most content is video
- [ ] Image adapter with Claude vision (OCR + description) — XHS image posts are common
- [ ] Article adapter with Trafilatura — WeChat OA articles
- [ ] Idempotent processing (skip existing, --force to override) — safe batch runs
- [ ] CLI for single item and batch scan — operational necessity
- [ ] Python library public API — downstream import

### Add After Validation (v1.x)

Features to add once the core pipeline is running end-to-end with real content.

- [ ] LLM structured analysis layer (themes, sentiment, takeaways) — add after confirming raw extraction quality is sufficient
- [ ] Gallery adapter with narrative synthesis — add when XHS gallery posts prove to be a significant portion of content
- [ ] Audio preprocessing (normalization, noise reduction) — add when Douyin music-overlay videos produce bad transcripts
- [ ] Extraction quality metadata (confidence, language, timing) — add when curator needs to filter by quality
- [ ] Configurable Whisper model selection — add when operator needs quality/speed tradeoff control

### Future Consideration (v2+)

- [ ] Speaker diarization (via WhisperX or alternative) — only if interview/podcast content becomes a priority
- [ ] Keyframe extraction from video — only if video visual context proves necessary for curator decisions
- [ ] Batch parallelism (multiprocessing) — only if batch processing speed becomes a bottleneck at scale

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Pydantic output models | HIGH | LOW | P1 |
| Content type router | HIGH | LOW | P1 |
| Video adapter (faster-whisper) | HIGH | MEDIUM | P1 |
| Image adapter (Claude vision) | HIGH | MEDIUM | P1 |
| Article adapter (Trafilatura) | HIGH | LOW | P1 |
| Idempotent processing | HIGH | LOW | P1 |
| CLI entry point | HIGH | LOW | P1 |
| Python library API | HIGH | LOW | P1 |
| Error handling + partial results | HIGH | MEDIUM | P1 |
| Metadata preservation | MEDIUM | LOW | P2 |
| LLM structured analysis | HIGH | HIGH | P2 |
| Gallery adapter + synthesis | MEDIUM | MEDIUM | P2 |
| Audio preprocessing | MEDIUM | MEDIUM | P2 |
| Quality metadata | MEDIUM | LOW | P2 |
| Progress reporting (tqdm) | LOW | LOW | P2 |
| Configurable Whisper models | LOW | LOW | P3 |
| Batch parallelism | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch — pipeline is broken without these
- P2: Should have, add after core works end-to-end with real content
- P3: Nice to have, add when specific need arises

## Competitor / Reference Feature Analysis

| Feature | BibiGPT/QClaw | Generic Whisper CLI | Trafilatura | Our Approach |
|---------|---------------|---------------------|-------------|--------------|
| Video transcription | Cloud API, 30+ platforms | Local Whisper, any audio | N/A | Local faster-whisper, optimized for CN/EN |
| Image OCR | Limited | N/A | N/A | Claude vision (high quality Chinese OCR) |
| Article extraction | URL-based summary | N/A | Best-in-class HTML to text | Trafilatura for cleaning, Claude for analysis |
| Structured output | Summary text only | Raw transcript | Markdown/JSON/XML | Pydantic-typed JSON + Markdown + analysis |
| Gallery handling | Not supported | N/A | N/A | Per-image extraction + narrative synthesis |
| Batch processing | Per-URL only | Single file | Supports batch | Directory-based batch with idempotency |
| LLM analysis | Built-in (cloud) | None | None | Claude structured analysis (themes, sentiment) |
| Offline/local | No (cloud service) | Yes | Yes | Yes (Whisper local, Claude via CLI Proxy) |
| Cost | Paid API | Free | Free | Free (Max plan CLI Proxy) |

## Sources

- [Choosing between Whisper variants (Modal)](https://modal.com/blog/choosing-whisper-variants) — faster-whisper vs WhisperX vs insanely-fast-whisper comparison
- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper) — CTranslate2-based Whisper, 4x faster
- [WhisperX PyPI](https://pypi.org/project/whisperx/) — forced alignment + diarization (declining maintenance)
- [Claude Vision docs](https://platform.claude.com/docs/en/build-with-claude/vision) — image understanding best practices
- [Claude OCR cookbook](https://platform.claude.com/cookbook/multimodal-how-to-transcribe-text) — document transcription patterns
- [Trafilatura GitHub](https://github.com/adbar/trafilatura) — web content extraction, best F1 score
- [Trafilatura evaluation](https://trafilatura.readthedocs.io/en/latest/evaluation.html) — benchmark comparison with Readability and others
- [Whisper Chinese recognition discussion](https://community.openai.com/t/whispers-chinese-recognition/192789) — Mandarin accuracy considerations
- [Idempotent data pipelines (Prefect)](https://www.prefect.io/blog/the-importance-of-idempotent-data-pipelines-for-resilience) — patterns for reliable batch processing

---
*Feature research for: multimodal content extraction pipeline*
*Researched: 2026-03-30*

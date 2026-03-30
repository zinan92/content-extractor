# Roadmap: content-extractor

## Overview

Transform raw multimedia content (video/image/article/gallery) from content-downloader into structured text consumable by downstream curator and rewriter. The journey starts with data models and the adapter framework, proves the pattern with the simplest adapter (article), builds LLM infrastructure, adds progressively complex media adapters (image, video core, video quality, gallery), layers on structured analysis, and finishes with CLI/library polish. Each phase delivers a verifiable capability that builds on the previous.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation & Data Models** - Pydantic models, adapter registry, output writer, config, error isolation
- [ ] **Phase 2: Article Adapter** - HTML cleaning with trafilatura, proves adapter pattern end-to-end
- [ ] **Phase 3: LLM Infrastructure** - CLI Proxy API client, token loading, fallback, rate limiting
- [ ] **Phase 4: Image Adapter** - Claude vision OCR + visual description for single images
- [ ] **Phase 5: Video Core** - FFmpeg audio extraction + faster-whisper transcription with timestamps
- [ ] **Phase 6: Video Quality** - VAD preprocessing, volume normalization, hallucination guard
- [ ] **Phase 7: Gallery Adapter** - Multi-image extraction with batching + narrative synthesis
- [ ] **Phase 8: LLM Analysis** - Structured analysis layer (themes, viewpoints, sentiment, takeaways)
- [ ] **Phase 9: CLI & Library API** - Typer CLI with batch mode, progress bars, error summaries, Python library API

## Phase Details

### Phase 1: Foundation & Data Models
**Goal**: A solid data contract and adapter framework that all subsequent adapters plug into
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, FOUND-06, QUAL-01, QUAL-02, QUAL-03, QUAL-04
**Success Criteria** (what must be TRUE):
  1. A ContentItem can be loaded from any valid `content_item.json` and invalid files produce clear errors
  2. Content routes to the correct adapter stub based on content_type (video/image/article/gallery)
  3. Output files (transcript.json, analysis.json, structured_text.md) are written atomically to the ContentItem directory
  4. Re-running extraction on already-processed content skips it; `--force` re-processes it
  5. Per-item errors are isolated -- a failing item does not abort the batch and quality metadata is recorded
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md -- Project scaffold, Pydantic models (input + output), ContentItem loader
- [x] 01-02-PLAN.md -- Adapter Protocol, stub adapters, router registry, atomic output writer
- [ ] 01-03-PLAN.md -- ExtractorConfig, extract/extract_batch orchestration, error isolation

### Phase 2: Article Adapter
**Goal**: Articles are cleaned and structured into markdown, proving the adapter pattern end-to-end with zero external service dependencies
**Depends on**: Phase 1
**Requirements**: ARTC-01, ARTC-02, ARTC-03
**Success Criteria** (what must be TRUE):
  1. An article ContentItem with raw HTML produces clean structured markdown preserving headings, lists, and emphasis
  2. Article metadata (author, date, word count) is extracted and included in the output
  3. Running extraction on an article directory produces all three output files (transcript.json, analysis.json placeholder, structured_text.md)
**Plans**: TBD

Plans:
- [ ] 02-01: TBD

### Phase 3: LLM Infrastructure
**Goal**: A reliable Claude API client that loads tokens, handles failures, and respects rate limits -- used by all LLM-dependent adapters
**Depends on**: Phase 1
**Requirements**: LLM-01, LLM-02, LLM-03, LLM-04
**Success Criteria** (what must be TRUE):
  1. CLI Proxy API token is loaded from `~/.cli-proxy-api/claude-*.json` and used for API calls
  2. When no CLI Proxy token exists, `ANTHROPIC_API_KEY` env var is used as fallback
  3. Expired tokens produce a clear error message (not a cryptic API failure)
  4. API calls back off on 429 responses and retry without crashing
**Plans**: TBD

Plans:
- [ ] 03-01: TBD

### Phase 4: Image Adapter
**Goal**: Single images are described via Claude vision with OCR and visual description in one call
**Depends on**: Phase 1, Phase 3
**Requirements**: IMG-01, IMG-02, IMG-03
**Success Criteria** (what must be TRUE):
  1. An image ContentItem produces a structured result with `ocr_text`, `visual_description`, and `confidence`
  2. Chinese text overlays (common on Xiaohongshu images) are correctly recognized in OCR output
  3. Image extraction output integrates into the standard output files (transcript.json contains image description)
**Plans**: TBD

Plans:
- [ ] 04-01: TBD

### Phase 5: Video Core
**Goal**: Video content is transcribed into timestamped text segments using FFmpeg + faster-whisper
**Depends on**: Phase 1
**Requirements**: VID-01, VID-03, VID-04, VID-05
**Success Criteria** (what must be TRUE):
  1. Audio is extracted from video files of various codecs (Douyin/XHS formats) via FFmpeg
  2. Transcription produces timestamped segments with confidence scores using faster-whisper
  3. Default model is turbo; `--whisper-model` flag switches to other models (e.g., large-v3)
  4. Video extraction output integrates into the standard transcript.json format
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD

### Phase 6: Video Quality
**Goal**: Transcription quality is hardened against hallucinations and poor audio through preprocessing and confidence scoring
**Depends on**: Phase 5
**Requirements**: VID-02, VID-06, VID-07
**Success Criteria** (what must be TRUE):
  1. Non-speech segments (music, silence) are filtered via VAD before transcription
  2. Audio volume is normalized before transcription to handle quiet recordings
  3. Low-confidence transcriptions are flagged with a hallucination warning in the output metadata
**Plans**: TBD

Plans:
- [ ] 06-01: TBD

### Phase 7: Gallery Adapter
**Goal**: Multi-image galleries are extracted with batched API calls and synthesized into a coherent narrative
**Depends on**: Phase 4
**Requirements**: GLRY-01, GLRY-02, GLRY-03
**Success Criteria** (what must be TRUE):
  1. Each image in a gallery is individually described using the Image adapter
  2. Images are batched into minimal API calls to stay within rate limits
  3. Per-image descriptions are synthesized into a coherent gallery narrative via LLM
**Plans**: TBD

Plans:
- [ ] 07-01: TBD

### Phase 8: LLM Analysis
**Goal**: Extracted text (from any content type) is analyzed for themes, viewpoints, sentiment, and actionable takeaways
**Depends on**: Phase 3
**Requirements**: ANLYS-01, ANLYS-02, ANLYS-03, ANLYS-04, ANLYS-05, ANLYS-06
**Success Criteria** (what must be TRUE):
  1. Extracted text is analyzed to produce structured themes, core viewpoints, and sentiment assessment
  2. Actionable takeaways are generated from content
  3. Analysis output is written as structured `analysis.json` with all dimensions
  4. A human-readable `structured_text.md` combining transcript and analysis is generated
**Plans**: TBD

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD

### Phase 9: CLI & Library API
**Goal**: Users can extract content via CLI commands or Python imports with full operational visibility
**Depends on**: Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, Phase 6, Phase 7, Phase 8
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, CLI-05
**Success Criteria** (what must be TRUE):
  1. `content-extractor extract /path/to/item/` extracts a single ContentItem
  2. `content-extractor extract-batch /path/to/output/` scans and extracts all ContentItems with a progress bar
  3. Batch mode shows an error summary at the end listing all failed items
  4. Python code can `from content_extractor import extract, extract_batch` and call them programmatically
**Plans**: TBD

Plans:
- [ ] 09-01: TBD
- [ ] 09-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9

Note: Phases 2, 3, and 5 all depend only on Phase 1 and could theoretically run in parallel.
Phase 4 depends on 1+3. Phase 6 depends on 5. Phase 7 depends on 4. Phase 8 depends on 3. Phase 9 depends on all.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Data Models | 0/3 | Not started | - |
| 2. Article Adapter | 0/1 | Not started | - |
| 3. LLM Infrastructure | 0/1 | Not started | - |
| 4. Image Adapter | 0/1 | Not started | - |
| 5. Video Core | 0/2 | Not started | - |
| 6. Video Quality | 0/1 | Not started | - |
| 7. Gallery Adapter | 0/1 | Not started | - |
| 8. LLM Analysis | 0/2 | Not started | - |
| 9. CLI & Library API | 0/2 | Not started | - |

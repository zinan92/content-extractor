# Research Summary: content-extractor

**Domain:** Multimodal content extraction pipeline (video/image/article/gallery to structured text)
**Researched:** 2026-03-30
**Overall confidence:** HIGH

## Executive Summary

The content-extractor sits at a critical junction in the content pipeline: without it, no downstream step (curator, rewriter) has usable input. The domain is well-served by mature, stable libraries. The core technical challenge is not "can we do this?" but "can we do this reliably?" -- Whisper hallucinations, Claude API rate limits, and cascading error propagation are the real risks, not missing tooling.

The recommended stack centers on **faster-whisper** (CTranslate2 backend, 4x faster than vanilla Whisper, same accuracy, lower memory) for video transcription, **anthropic SDK** for Claude vision and text analysis via CLI Proxy API, **trafilatura** for article HTML cleaning, and **Typer + Rich** for CLI. All libraries are verified compatible with Python 3.13+ as of early 2026. The total new dependency footprint is modest: ~200MB for CTranslate2 + Whisper turbo model (~1.6GB downloaded once), versus ~2GB+ if using vanilla openai-whisper with PyTorch.

Architecture follows a two-layer adapter pattern: Layer 1 (raw extraction) produces text from media using content-type-specific adapters; Layer 2 (LLM analysis) produces structured insights from that text. The layers are independent -- you can re-analyze without re-transcribing, and you can test extraction without LLM access. Pydantic models define all data boundaries.

The most dangerous pitfalls are Whisper hallucinations on non-speech audio (background music, silence) and cascading errors through the pipeline. Both must be addressed in Phase 1, not deferred. Voice Activity Detection preprocessing and per-item quality scores are not optional refinements -- they are architectural requirements.

## Key Findings

**Stack:** faster-whisper 1.2.1 + anthropic 0.86+ + trafilatura 2.0.0 + Typer 0.24+ + Rich 14.1+ + Pydantic 2.12+ on Python 3.13+. All verified on PyPI with current versions.

**Architecture:** Two-layer adapter pattern. Layer 1 = raw extraction (Whisper/Vision/trafilatura per content type). Layer 2 = LLM structured analysis. Filesystem as intermediate (transcript.json before analysis.json). Output appended to content-downloader directories.

**Critical pitfall:** Whisper hallucinations on non-speech audio. Must use VAD preprocessing and confidence scoring from Phase 1. This is not a polish item -- hallucinated transcripts poison the entire downstream pipeline.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Foundation + Data Models** - Define Pydantic models, ContentItem loader, adapter registry, output writer, config
   - Addresses: Standardized output format, content type routing, idempotent processing
   - Avoids: Building adapters before the contract is defined (schema drift pitfall)

2. **Article Adapter** - Simplest adapter, no external service dependencies
   - Addresses: Article HTML cleaning (trafilatura), proves the adapter pattern
   - Avoids: Needing Whisper or Claude API to test the pipeline end-to-end

3. **LLM Infrastructure + Image Adapter** - CLI Proxy API client, Claude vision integration
   - Addresses: Image OCR + description, establishes LLM calling patterns
   - Avoids: Duplicating client setup across adapters

4. **Video Adapter** - FFmpeg audio extraction + faster-whisper transcription + VAD
   - Addresses: Video transcription (highest-value feature), hallucination prevention
   - Avoids: Memory issues (faster-whisper + int8), hallucination cascades (VAD + confidence)

5. **Gallery Adapter + LLM Analysis** - Multi-image synthesis, structured analysis layer
   - Addresses: Gallery narrative, structured analysis (themes, sentiment, takeaways)
   - Avoids: Rate limit issues (batch images into single API calls)

6. **CLI Polish + Batch Mode** - Progress bars, error summaries, batch scanning
   - Addresses: Operational usability for processing 100+ items
   - Avoids: Premature optimization of batch flow before adapters are proven

**Phase ordering rationale:**
- Foundation first because everything depends on Pydantic models and the adapter interface
- Article adapter second because it proves the pattern with zero external dependencies (no Whisper, no Claude)
- LLM infra before video because image adapter is simpler and validates the Claude API integration
- Video adapter is the most complex (FFmpeg + Whisper + VAD) -- tackle after patterns are proven
- Gallery depends on image adapter, so it comes after
- CLI polish last -- library API is the product, CLI is one interface

**Research flags for phases:**
- Phase 4 (Video): Likely needs deeper research on VAD integration with faster-whisper, Chinese audio quality
- Phase 5 (Gallery): May need research on optimal image batching strategy for Claude API rate limits
- Phase 2 (Article): Standard patterns, unlikely to need further research
- Phase 3 (LLM Infra): CLI Proxy API token loading needs validation against actual token files

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified on PyPI. CTranslate2 Python 3.13 support confirmed (v4.7.1, Feb 2026). |
| Features | HIGH | Feature landscape is well-understood. Content-downloader's output format is the input contract. |
| Architecture | HIGH | Adapter pattern proven in content-downloader. Two-layer extraction+analysis is standard. |
| Pitfalls | HIGH | Whisper hallucinations are extensively documented. Claude Vision limits in official docs. |

## Gaps to Address

- **CLI Proxy API token format:** Need to validate actual `~/.cli-proxy-api/claude-*.json` file structure against assumed fields (`access_token`, `expired`, `refresh_token`). The client factory depends on this.
- **faster-whisper on Apple Silicon M-series:** CTranslate2 has macOS ARM64 wheels, but CPU inference performance on M1/M2/M3 with int8 quantization needs benchmarking with real Chinese audio content.
- **Whisper turbo Chinese accuracy:** Turbo is a distilled model -- need to verify Chinese transcription quality is acceptable vs large-v3 on real Douyin/XHS content. May need to default to large-v3 for Chinese and turbo for English.
- **Rate limits on CLI Proxy API:** Exact rate limits for the Max plan proxy are undocumented. Gallery batching strategy depends on knowing the limit. Need empirical testing.
- **content-downloader ContentItem schema:** Need to verify the exact fields in content_item.json. The extractor should define its own Pydantic model reading from JSON (not importing from content-downloader) to avoid coupling.

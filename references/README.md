# References

Documentation for content-extractor adapters and output formats.

## Output Schema Reference

### extractor_output.json (rewriter handoff)
- `content_id`: string — unique content identifier
- `source_platform`: string — origin platform
- `title`: string — content title
- `transcript`: string — full raw text
- `key_points`: string[] — extracted takeaways
- `visual_descriptions`: string[] — image/video descriptions
- `metadata`: object — duration, publish_date, engagement counts

### extraction_status.json (degradation signals)
- `content_id`: string
- `transcript`: "ok" | "degraded"
- `analysis`: "ok" | "degraded"

## Adapter Notes

### Video
- Audio extracted via FFmpeg, normalized to -16 LUFS
- Transcription via faster-whisper (turbo model, ~1.6GB)
- Hallucination detection: confidence threshold + char/sec rate + repetition check

### Image
- Claude vision API: combined OCR + visual description in single call

### Article
- trafilatura for HTML → Markdown (F1=0.96 vs BeautifulSoup 0.665)
- Structure preservation (headings, lists, emphasis)

### Gallery
- Per-image Claude vision analysis
- LLM narrative synthesis across all images (all-or-nothing)

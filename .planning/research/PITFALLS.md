# Domain Pitfalls

**Domain:** Multimodal content extraction pipeline (video/image/article/gallery)
**Researched:** 2026-03-30

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or pipeline-wide failures.

### Pitfall 1: Whisper Hallucinations on Silence and Background Noise

**What goes wrong:** Whisper generates confident-sounding but entirely fabricated text when encountering silence, background music, or ambient noise in video audio. This is especially severe with Chinese audio where the training corpus is smaller. The model uses previous transcription output to prompt current segments, so one hallucination cascades into a stream of fabricated content. Whisper large-v3 and turbo are both affected.

**Why it happens:** Whisper's autoregressive architecture feeds prior output as context for subsequent segments. When it encounters non-speech audio, it "fills in" based on patterns from training data rather than admitting silence. Chinese content from Douyin/Xiaohongshu frequently has background music, sound effects, and variable-quality audio.

**Consequences:** Downstream LLM analysis produces structured insights based on fabricated transcripts. The curator and rewriter consume garbage data with high confidence. Worst case: entirely hallucinated quotes attributed to content creators.

**Warning signs:**
- Repeated phrases or loops in transcript output
- Transcript segments that don't match video length (too much text for a short clip)
- Famous quotes, song lyrics, or copyright attributions appearing in transcripts of original content
- Transcripts for audio that is primarily music

**Prevention:**
1. Use Silero VAD (Voice Activity Detection) as a preprocessing step -- strip non-speech segments before feeding to Whisper. WhisperX or faster-whisper both integrate this natively
2. Set `condition_on_previous_text=False` to break the hallucination cascade chain
3. Use `no_speech_threshold` (default 0.6) and `logprob_threshold` (default -1.0) to filter low-confidence segments
4. Add a post-processing validation: if transcript word count per second exceeds a reasonable threshold (~4 words/sec for Chinese), flag as suspicious
5. Store confidence scores per segment in `transcript.json` so downstream consumers can filter

**Detection:** Compare transcript duration coverage vs audio duration. If Whisper claims 100% speech for a Douyin video with background music, something is wrong.

**Phase:** Must be addressed in Phase 1 (video adapter). This is not a polish item -- hallucinated transcripts poison the entire pipeline.

**Confidence:** HIGH -- well-documented across multiple sources including OpenAI's own issue tracker and academic research.

---

### Pitfall 2: Simplified vs Traditional Chinese Script Confusion

**What goes wrong:** Whisper's Chinese language code is a single `zh` covering both Simplified and Traditional. The model unpredictably switches between scripts mid-transcript, sometimes within the same sentence. For a pipeline targeting Douyin/Xiaohongshu content (Simplified Chinese), getting Traditional Chinese output breaks downstream text matching, search, and LLM analysis consistency.

**Why it happens:** Whisper was trained on a mixed corpus of Simplified and Traditional Chinese text. There is no built-in mechanism to force one script over the other.

**Consequences:** Inconsistent text encoding across transcripts. LLM analysis may produce mixed-script structured output. Text search and deduplication fail because the same word appears in two scripts.

**Warning signs:**
- Traditional characters appearing in transcripts of mainland Chinese creators
- Mixed scripts within a single transcript file

**Prevention:**
1. Use the `initial_prompt` parameter with a Simplified Chinese prompt like `"以下是普通话的句子。"` to bias the model toward Simplified output
2. Add a post-processing step using `opencc` (Open Chinese Convert) to normalize all output to Simplified Chinese
3. Store the original script variant in metadata so the normalization is reversible

**Detection:** Run a script detection check on transcript output (Traditional characters have distinct Unicode ranges).

**Phase:** Phase 1 (video adapter), as a post-processing normalization step.

**Confidence:** HIGH -- directly documented in OpenAI Whisper discussions and MacWhisper support docs.

---

### Pitfall 3: Cascading Errors Through the Pipeline

**What goes wrong:** A single bad extraction (hallucinated transcript, failed image OCR, malformed article HTML) propagates silently through LLM analysis, curator scoring, and rewriter output. Because each stage adds a layer of abstraction, the original error becomes invisible -- the LLM confidently analyzes garbage input and produces plausible-looking structured output.

**Why it happens:** Modular pipelines are inherently susceptible to cascading errors. LLMs are particularly dangerous here because they don't say "this input looks wrong" -- they generate coherent analysis of whatever they receive.

**Consequences:** The content-curator makes selection decisions based on fabricated analysis. The content-rewriter produces derivative content from fiction. Trust in the entire pipeline erodes.

**Warning signs:**
- LLM analysis that seems generically insightful but doesn't reference specific content details
- Analysis sentiments that contradict the original content's tone
- Structured output where all fields are populated but themes/viewpoints feel templated

**Prevention:**
1. Each adapter must output an explicit `extraction_quality` score (0-1) based on objective metrics (speech-to-silence ratio, OCR confidence, HTML cleanliness)
2. The LLM analysis layer must receive and propagate this quality score -- don't analyze items below a threshold
3. `analysis.json` must include `source_quality` metadata so downstream consumers can make informed decisions
4. Implement a "circuit breaker" pattern: if extraction quality for a batch drops below a threshold, halt and alert rather than producing bad data at scale

**Detection:** Spot-check pipeline output against original content. If you can't trace an analysis claim back to specific source text, the pipeline is laundering errors.

**Phase:** Must be designed into the architecture from Phase 1. Retrofitting quality propagation requires touching every component.

**Confidence:** HIGH -- well-established pattern in data pipeline engineering.

---

### Pitfall 4: Claude Vision Token Burn on Galleries

**What goes wrong:** Gallery content from Xiaohongshu can have 9-20 images per post. Sending each image to Claude Vision individually means 9-20 API calls per content item, each consuming ~1,600 tokens for the image alone plus prompt tokens. A batch of 100 gallery posts = potentially 2,000 API calls. Even with CLI Proxy API (Max plan), you hit rate limits quickly and processing grinds to a halt.

**Why it happens:** The naive implementation is "one image, one API call." Claude Vision supports up to 20 images per request (claude.ai) or up to 600 via API, but developers often don't realize they can batch images into a single request with a combined prompt.

**Consequences:** Rate limiting from CLI Proxy API causes intermittent failures. Batch processing takes hours instead of minutes. Retry logic becomes complex. The "zero cost" assumption breaks when rate limits are the real constraint, not money.

**Warning signs:**
- Gallery processing taking 10x longer than video processing
- HTTP 429 (rate limit) errors in logs
- Individual image descriptions that lack context about the gallery narrative

**Prevention:**
1. Batch all gallery images into a single Claude Vision request with a prompt like "Describe each image and the overall narrative of this gallery post"
2. Resize images to max 1568px on the long edge before sending -- Claude resizes internally anyway, and pre-resizing reduces upload time and avoids latency penalty
3. Implement exponential backoff with jitter for rate limit handling
4. For galleries with >20 images, split into batches of 10-15 and synthesize narratives
5. Cache Vision results aggressively -- image content doesn't change

**Detection:** Monitor API calls per content item. If gallery items average >5 API calls, batching is broken.

**Phase:** Phase 1 (gallery adapter design). The batching strategy affects the adapter interface.

**Confidence:** MEDIUM -- token costs are documented by Anthropic; rate limit behavior on CLI Proxy API specifically is less documented.

---

### Pitfall 5: FFmpeg Audio Extraction Failures on Platform-Specific Formats

**What goes wrong:** Videos downloaded from Douyin, Xiaohongshu, and WeChat use various container formats and codecs. Some Douyin videos use non-standard audio streams, WeChat videos may have unusual container wrapping, and the audio extraction step (ffmpeg -> PCM/WAV -> Whisper) silently produces empty or corrupted audio files. Whisper then either errors out or hallucinates on the empty input.

**Why it happens:** Platform content uses whatever encoder the app ships. There's no guarantee of standard MP4/AAC. The content-downloader stores files as-is from the platform.

**Consequences:** Silent failures where Whisper receives zero-length or corrupted audio. Empty transcripts for content that actually has speech. Or worse, Whisper hallucinates on the noise from a corrupt extraction.

**Warning signs:**
- Empty or near-empty transcript files for videos that clearly have audio
- FFmpeg stderr warnings being swallowed by subprocess calls
- Audio files with 0 bytes or unexpected durations

**Prevention:**
1. Always validate FFmpeg output: check file size > 0, duration matches expected range, audio stream is present
2. Extract audio to WAV (PCM s16le, mono, 16kHz) -- this is what Whisper expects internally anyway, and avoids codec issues downstream
3. Capture and log FFmpeg stderr -- it contains critical warnings about missing streams, codec errors, etc.
4. Probe the video first with `ffprobe` to check if an audio stream exists at all (some Douyin videos are silent/music-only with no separate audio track)
5. Handle the "no audio stream" case explicitly: mark the content item as `audio_unavailable` rather than generating an empty transcript

**Detection:** Post-extraction validation: `ffprobe` the output WAV file and verify sample rate, channels, and duration.

**Phase:** Phase 1 (video adapter), before Whisper integration.

**Confidence:** HIGH -- standard FFmpeg pitfall, well-documented.

---

## Moderate Pitfalls

### Pitfall 6: Idempotency Races in Batch Processing

**What goes wrong:** The spec calls for idempotent processing (skip already-extracted items unless `--force`). But the idempotency check (does `transcript.json` exist?) and the file write are not atomic. In batch mode, if the process crashes mid-extraction, you get partially written files that pass the existence check but contain incomplete data. On retry, the pipeline skips the corrupted item.

**Prevention:**
1. Write to a temporary file first (e.g., `transcript.json.tmp`), then atomically rename on completion
2. Use a completion marker approach: write `.extraction_complete` only after all three output files are successfully written
3. The idempotency check should verify the completion marker, not individual files
4. `--force` should delete the completion marker, triggering full re-extraction

**Detection:** Scan for output files without completion markers. These are zombie extractions.

**Phase:** Phase 1 (core extraction loop design). Must be baked into the write pattern from the start.

**Confidence:** HIGH -- standard data pipeline pattern.

---

### Pitfall 7: LLM Structured Output Schema Drift

**What goes wrong:** The LLM analysis layer produces JSON with themes, viewpoints, sentiment, and takeaways. Without strict schema enforcement, the output structure drifts over time -- field names change, nesting varies, optional fields disappear, array items have inconsistent shapes. Downstream consumers (curator, rewriter) break on unexpected shapes.

**Prevention:**
1. Define Pydantic models for `analysis.json` schema and validate every LLM response against them
2. Use Claude's structured output / tool_use with a JSON schema to constrain the response format
3. Implement retry logic: if validation fails, retry with the validation error in the prompt (up to 2 retries)
4. Never store raw LLM output -- always parse, validate, then serialize from the Pydantic model
5. Version the schema in the output file (`"schema_version": "1.0"`) so downstream consumers can handle evolution

**Detection:** Pydantic validation errors in logs. If you're catching and silently handling them, the schema is drifting.

**Phase:** Phase 1 (LLM analysis layer). Schema design is an architectural decision.

**Confidence:** HIGH -- well-documented LLM integration pitfall, supported by multiple benchmarking studies.

---

### Pitfall 8: Whisper Memory Exhaustion on Long Videos

**What goes wrong:** Whisper turbo requires ~6GB VRAM for inference. Long videos (30+ minutes, common for WeChat Official Account video content) can exhaust memory during batch processing, especially if multiple extractions are queued. On macOS with Apple Silicon, "VRAM" is shared system memory, so OOM affects the entire system.

**Prevention:**
1. Use `faster-whisper` instead of raw OpenAI Whisper -- it uses CTranslate2 with 2-4x less memory via int8 quantization
2. Process audio in chunks for long videos rather than loading entire audio files
3. Set a maximum concurrent Whisper processes limit (1 on most consumer hardware)
4. Monitor memory before starting extraction; queue items if memory is low
5. For Apple Silicon: `compute_type="int8"` or `"float16"` to manage unified memory pressure

**Detection:** System memory pressure warnings, process killed by OS, or incomplete transcripts that cut off mid-sentence.

**Phase:** Phase 1 (video adapter), critical for batch processing mode.

**Confidence:** MEDIUM -- documented for GPU systems; Apple Silicon behavior is less documented but follows same patterns.

---

### Pitfall 9: Article Cleaning Destroys Meaningful Structure

**What goes wrong:** Aggressive HTML cleaning strips not just ads and boilerplate, but also meaningful formatting -- tables, blockquotes, emphasis, lists, and embedded media references. The resulting "clean" text loses the structure that conveys meaning. A WeChat Official Account article's careful formatting (headers, pull quotes, numbered lists) becomes a wall of undifferentiated text.

**Prevention:**
1. Convert to Markdown rather than plain text -- preserve semantic structure (headers, lists, emphasis, blockquotes, tables)
2. Use a two-pass approach: first extract the main content area (strip nav, ads, sidebars), then convert the content area to Markdown preserving structure
3. For WeChat OA specifically: the `js_content` div contains the article body; extract that div specifically rather than applying generic boilerplate removal
4. Keep the original HTML in the content-downloader output; only the extractor output is cleaned
5. Test cleaning against 10+ real articles from each platform before finalizing rules

**Detection:** Compare cleaned output side-by-side with original. If numbered lists become run-on paragraphs, the cleaner is too aggressive.

**Phase:** Phase 1 (article adapter). Platform-specific cleaning rules are needed from the start.

**Confidence:** MEDIUM -- general web scraping wisdom; platform-specific rules need validation against real content.

---

### Pitfall 10: Treating All Content Types with the Same LLM Prompt

**What goes wrong:** Using a single "analyze this content" prompt for videos, images, articles, and galleries produces shallow, generic analysis. A Douyin cooking video needs different analysis dimensions than a Xiaohongshu product review gallery or a WeChat thought-leadership article. Generic prompts extract generic insights.

**Prevention:**
1. Design content-type-specific analysis prompts: video (narrative arc, key claims, demonstrated techniques), gallery (visual progression, product features, aesthetic choices), article (argument structure, evidence quality, originality)
2. Include platform context in prompts: Douyin content tends to be entertainment/education, Xiaohongshu tends to be product/lifestyle, WeChat OA tends to be long-form analysis
3. Make prompts configurable, not hardcoded -- store them as template files that can be iterated without code changes
4. Include the content metadata (platform, content_type, creator info) in the LLM prompt for context

**Detection:** If analysis output for a cooking video reads the same as analysis for a tech opinion article, prompts are too generic.

**Phase:** Phase 1 (LLM analysis layer), but expect iteration in later phases as you see real output quality.

**Confidence:** MEDIUM -- based on general LLM prompt engineering patterns; needs validation against real content.

---

## Minor Pitfalls

### Pitfall 11: Image Resolution Assumptions

**What goes wrong:** Claude Vision handles images up to 1568px per dimension internally. Sending very small images (<200px, like thumbnails) produces unreliable descriptions. Sending very large images wastes upload bandwidth for no quality gain. Not checking image dimensions means inconsistent analysis quality across content items.

**Prevention:**
1. Skip images below 200px in either dimension (likely thumbnails, icons, or decorative elements)
2. Pre-resize images above 1568px to save upload time
3. Log image dimensions in extraction metadata for quality tracking

**Phase:** Phase 1 (image/gallery adapter).

**Confidence:** HIGH -- documented in Claude Vision API docs.

---

### Pitfall 12: Missing Audio Stream Detection

**What goes wrong:** Some "video" content from platforms is actually a slideshow with background music and no speech. Some are silent. The pipeline attempts transcription and either gets empty output or hallucinated text.

**Prevention:**
1. Use `ffprobe` to detect audio stream presence and properties before extraction
2. Run Silero VAD on extracted audio; if speech ratio < 10%, mark as `no_speech` and skip transcription
3. For slideshows with music + text overlays: route to image adapter (extract frames) rather than video adapter

**Detection:** Track speech ratio metrics per content item. Items with 0% speech that have transcripts are hallucinations.

**Phase:** Phase 1 (routing logic before adapter selection).

**Confidence:** HIGH -- straightforward engineering check.

---

### Pitfall 13: Output Directory Pollution

**What goes wrong:** The spec requires output files to coexist in content-downloader's directory structure. Careless file naming or stale outputs from failed runs accumulate and confuse downstream consumers. Temporary files, partial outputs, and outputs from different extractor versions mix together.

**Prevention:**
1. Use a clear naming convention: `transcript.json`, `analysis.json`, `structured_text.md` only
2. Prefix temporary files (`.tmp.transcript.json`) and clean up on completion or failure
3. Include extractor version and timestamp in output metadata (inside the JSON, not in filenames)
4. Never write files outside the content item's directory

**Detection:** `find` for `.tmp.*` files or unexpected files in content item directories.

**Phase:** Phase 1 (output file management). Establish the convention early.

**Confidence:** HIGH -- standard file management practice.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Video adapter (Whisper) | Hallucinations on non-speech audio | VAD preprocessing + confidence scoring mandatory |
| Video adapter (FFmpeg) | Silent failures on platform-specific codecs | ffprobe validation + stderr logging |
| Video adapter (memory) | OOM on long videos with Apple Silicon | Use faster-whisper with int8, chunk long audio |
| Image adapter (Claude Vision) | Low-quality image hallucinations | Skip images <200px, pre-resize large images |
| Gallery adapter (Claude Vision) | Rate limit exhaustion on multi-image posts | Batch images into single API calls |
| Article adapter (cleaning) | Over-aggressive stripping destroys structure | HTML -> Markdown conversion, not plain text |
| LLM analysis layer | Schema drift in structured output | Pydantic validation + retry logic |
| LLM analysis layer | Generic analysis across content types | Content-type-specific prompt templates |
| Batch processing | Partial writes breaking idempotency | Atomic writes with completion markers |
| Pipeline integration | Cascading error propagation | Quality scores at every stage, circuit breakers |

## Sources

- [Whisper Chinese Recognition Discussion](https://community.openai.com/t/whispers-chinese-recognition/192789)
- [Whisper Simplified vs Traditional Chinese](https://github.com/openai/whisper/discussions/277)
- [Whisper Hallucination Solutions](https://memo.ac/blog/whisper-hallucinations)
- [Whisper Turbo Release Discussion](https://github.com/openai/whisper/discussions/2363)
- [Whisper v3 Hallucinations on Real World Data](https://deepgram.com/learn/whisper-v3-results)
- [WhisperX - VAD + Batched Inference](https://github.com/m-bain/whisperX)
- [faster-whisper VAD Integration](https://deepwiki.com/SYSTRAN/faster-whisper/5.2-voice-activity-detection)
- [Claude Vision API Documentation](https://platform.claude.com/docs/en/build-with-claude/vision)
- [Claude Vision OCR Comparison](https://sparkco.ai/blog/deepseek-ocr-vs-claude-vision-a-deep-dive-into-accuracy)
- [Structured Output AI Reliability Guide](https://www.cognitivetoday.com/2025/10/structured-output-ai-reliability/)
- [Idempotency in Data Pipelines](https://airbyte.com/data-engineering-resources/idempotency-in-data-pipelines)
- [Whisper Memory Requirements](https://github.com/openai/whisper/discussions/5)
- [Investigation of Whisper ASR Hallucinations](https://arxiv.org/html/2501.11378v1)
- [Whisper False Copyright Hallucination Bug](https://github.com/openai/whisper/discussions/2685)

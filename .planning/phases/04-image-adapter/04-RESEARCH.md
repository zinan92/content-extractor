# Research: Phase 4 — Image Adapter

**Researched:** 2026-03-30
**Confidence:** HIGH
**Discovery Level:** 1 (Quick Verification — single known library, confirming API patterns)

## Research Questions

1. How to send images to Claude vision API for combined OCR + visual description?
2. Image preprocessing requirements (size limits, base64 encoding)?
3. Chinese text overlay handling for Xiaohongshu images?
4. Structured response parsing into ExtractionResult?

## Findings

### 1. Claude Vision API — Single-Call OCR + Description

The `anthropic` SDK (0.86+) supports vision via the Messages API. Images are sent as `image` content blocks alongside text prompts in a single API call.

**API pattern:**

```python
from anthropic import Anthropic

client = Anthropic(api_key=access_token)

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",  # or image/png, image/gif, image/webp
                        "data": base64_encoded_string,
                    },
                },
                {
                    "type": "text",
                    "text": "prompt here",
                },
            ],
        }
    ],
)
```

**Key points:**
- One API call can do both OCR and visual description — no need for two calls
- Supported formats: JPEG, PNG, GIF, WebP
- The prompt should explicitly request both OCR text and visual description in structured format
- `temperature=0.0` for deterministic OCR output

### 2. Image Preprocessing Requirements

**Claude Vision limits:**
- Maximum image size: ~5MB per image after base64 encoding
- Maximum resolution: Images are automatically resized by the API, but sending smaller images reduces token cost and latency
- Recommended: Resize to max 1568px on longest side (Claude's internal limit — larger images are downscaled anyway, wasting upload bandwidth)

**Preprocessing pipeline:**
1. Read image with Pillow to get format and dimensions
2. If longest side > 1568px, resize proportionally (LANCZOS resampling)
3. Convert to JPEG if PNG is very large (JPEG is smaller for photos)
4. Base64-encode the result
5. Detect MIME type from actual format (not file extension)

**Pillow pattern:**

```python
from PIL import Image
import base64
import io

MAX_DIMENSION = 1568

def preprocess_image(image_path: Path) -> tuple[str, str]:
    """Returns (base64_data, media_type)."""
    with Image.open(image_path) as img:
        # Resize if needed
        if max(img.size) > MAX_DIMENSION:
            ratio = MAX_DIMENSION / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        # Encode to bytes
        buffer = io.BytesIO()
        fmt = img.format or "JPEG"
        if fmt.upper() not in ("JPEG", "PNG", "GIF", "WEBP"):
            fmt = "JPEG"
        img.save(buffer, format=fmt)

        data = base64.standard_b64encode(buffer.getvalue()).decode("ascii")
        media_type = f"image/{fmt.lower()}"
        return data, media_type
```

### 3. Chinese Text Overlay Handling (Xiaohongshu)

Xiaohongshu images frequently have:
- Chinese text overlays with decorative fonts
- Text on complex backgrounds (gradient, photo)
- Mixed Chinese + English text (brand names, hashtags)
- Emoji and special characters mixed with text

**Best practices for Chinese OCR via Claude vision:**
- Explicitly instruct the model to transcribe ALL visible text including Chinese characters
- Request text in original language (do not translate)
- Ask for text position context ("top banner says...", "caption at bottom reads...")
- Claude handles Chinese characters well — no special preprocessing needed for the text itself
- The key is in the prompt, not in image preprocessing

**Recommended prompt structure:**

```
Analyze this image and provide:

1. OCR_TEXT: Transcribe ALL visible text in the image exactly as written,
   including Chinese characters, English text, numbers, and special characters.
   Preserve the original language. If text appears in multiple locations,
   separate with newlines and note position (e.g., "top:", "bottom:", "overlay:").

2. VISUAL_DESCRIPTION: Describe what the image shows — the scene, objects,
   people, colors, composition, and mood. Be specific and concise.

3. CONFIDENCE: Rate your confidence in the OCR accuracy from 0.0 to 1.0.
   Lower confidence if text is partially obscured, decorative, or blurry.

Respond in JSON format:
{
  "ocr_text": "...",
  "visual_description": "...",
  "confidence": 0.95
}
```

### 4. Structured Response Parsing

**Option A: JSON mode (recommended)**
Ask Claude to respond in JSON and parse with `orjson`. Simple, reliable for this use case.

**Option B: Anthropic structured output (tool_use)**
The SDK supports tool-based structured output where Claude fills a function schema. More complex than needed for a simple 3-field response.

**Recommendation:** Use JSON mode with explicit JSON schema in the prompt. Parse response text with `orjson.loads()`. Validate with a simple Pydantic model. Fall back gracefully if JSON parsing fails (extract what we can from raw text).

**Response model:**

```python
class VisionResponse(BaseModel):
    """Parsed response from Claude vision API."""
    model_config = ConfigDict(frozen=True)

    ocr_text: str = ""
    visual_description: str = ""
    confidence: float = 0.0
```

### 5. Error Handling

Key failure modes:
- **Image file not found / unreadable**: Pillow raises `FileNotFoundError` or `PIL.UnidentifiedImageError`
- **Image too large after preprocessing**: Should not happen with resize, but check base64 size
- **API rate limit (429)**: Phase 3 LLM Infrastructure handles retry/backoff — image adapter should propagate the exception
- **API error (500, auth failure)**: Let Phase 3 client handle; image adapter catches and wraps in a clear error
- **JSON parse failure**: Fall back to using raw response text as description, confidence=0.0
- **Empty/no text in image**: Valid result — `ocr_text=""`, confidence reflects this

### 6. Integration with Existing Models

The `MediaDescription` model already has the right fields:

```python
class MediaDescription(BaseModel):
    file_path: str
    description: str      # maps to visual_description
    ocr_text: str = ""    # maps to ocr_text
    confidence: float = 0.0
```

The `ExtractionResult` aggregates these:
- `raw_text`: Combined OCR text from the image
- `media_descriptions`: Tuple of MediaDescription (one per image file)
- `quality.confidence`: Overall confidence score
- `quality.language`: Detected from OCR text (reuse `_detect_language` from article adapter)

## Architecture Decision

**Phase 3 Dependency:** The image adapter needs a Claude API client. Phase 3 (LLM Infrastructure) creates this. The image adapter should accept a client via dependency injection (or create one internally using a shared factory function from the LLM module).

**Design:** Create `src/content_extractor/llm.py` in Phase 3 with a `get_claude_client() -> Anthropic` function. The image adapter imports and uses it. If Phase 3 is not yet executed when Phase 4 runs, the image adapter needs a minimal inline client setup (but per roadmap, Phase 3 precedes Phase 4).

**For planning purposes:** Assume Phase 3 provides `src/content_extractor/llm.py` with at minimum:
- `get_claude_client() -> Anthropic` — loads token, creates client
- Handles CLI Proxy API token loading and ANTHROPIC_API_KEY fallback
- Rate limit awareness (429 retry) built into the client or as a wrapper

## Confidence

| Aspect | Confidence | Notes |
|--------|------------|-------|
| Claude vision API pattern | HIGH | Well-documented, SDK verified on PyPI |
| Image preprocessing with Pillow | HIGH | Standard pattern, well-tested library |
| Chinese OCR via Claude | HIGH | Claude handles CJK text well per docs |
| JSON response parsing | HIGH | Simple pattern, orjson is fast and reliable |
| Integration with existing models | HIGH | MediaDescription already has ocr_text + description fields |

## Sources

- [Claude Vision docs](https://platform.claude.com/docs/en/build-with-claude/vision) — image understanding, base64 encoding
- [Claude OCR cookbook](https://platform.claude.com/cookbook/multimodal-how-to-transcribe-text) — text transcription from images
- [Anthropic SDK PyPI](https://pypi.org/project/anthropic/) — v0.86.0, Messages API
- [Pillow docs](https://pillow.readthedocs.io/) — image resizing, format conversion
- Existing codebase: `models.py` MediaDescription, `adapters/article.py` pattern

---
*Research for: Phase 4 Image Adapter*
*Researched: 2026-03-30*

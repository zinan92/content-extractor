# Phase 2: Article Adapter - Research

**Researched:** 2026-03-30
**Domain:** HTML article extraction with trafilatura, markdown output, metadata extraction
**Confidence:** HIGH

## Summary

Phase 2 implements the first real adapter in the content-extractor pipeline -- the ArticleExtractor. It replaces the `NotImplementedError` stub in `src/content_extractor/adapters/article.py` with a working implementation that uses trafilatura to clean HTML into structured markdown and extract article metadata (author, date, word count).

This phase is deliberately chosen as the first adapter because it has zero external service dependencies (no LLM, no Whisper, no FFmpeg). It proves the Extractor Protocol end-to-end: load ContentItem -> route to adapter -> extract -> write output files. The primary content source is WeChat OA articles, which arrive as saved HTML files in the `media/` subdirectory.

**Primary recommendation:** Use `trafilatura.bare_extraction()` to get both cleaned text and metadata in a single call. Output the text portion as markdown via `output_format="markdown"` with `include_formatting=True`. Construct ExtractionResult from the returned Document object, populating raw_text with the markdown content and quality metadata with word count and language.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ARTC-01 | Clean HTML content using trafilatura, output structured markdown | trafilatura `extract()` with `output_format="markdown"` produces clean markdown from HTML. `bare_extraction()` returns a Document with both text and metadata. F1=0.960 for article extraction. |
| ARTC-02 | Preserve article structure (headings, lists, emphasis) in markdown output | `output_format="markdown"` combined with `include_formatting=True` preserves headings, lists, bold/italic. Verified in trafilatura source. |
| ARTC-03 | Extract article metadata (author, date, word count) from cleaned content | trafilatura Document object includes `author`, `date`, `title`, `sitename`, `categories`, `tags`, `language`. Word count is computed from the extracted text. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| trafilatura | 2.0.0 | HTML to clean text + metadata extraction | Purpose-built for article extraction. F1=0.960. Strips ads, nav, boilerplate. Outputs markdown natively. Already selected in STACK.md research. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| orjson | 3.10+ | JSON serialization for transcript.json | Already in pyproject.toml deps. Used by output.py for atomic writes. |
| pydantic | 2.12+ | Data models | Already in pyproject.toml. All models are frozen Pydantic BaseModel. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| trafilatura | BeautifulSoup4 | BS4 has no article detection heuristics. F1=0.665 vs 0.960. Would require 50+ lines of custom boilerplate removal. |
| trafilatura | readability-lxml | Lower benchmark scores, less maintained. |

**Installation (Phase 2 addition):**
```bash
pip install trafilatura>=2.0,<3
```

Must be added to `pyproject.toml` `dependencies` list.

## Architecture Patterns

### File Layout for Article Adapter

The adapter lives at the existing stub location. No new directories needed.

```
src/content_extractor/
    adapters/
        base.py          # Extractor Protocol (exists)
        article.py       # ArticleExtractor (stub -> implement)
    models.py            # ExtractionResult, QualityMetadata (exists)
    output.py            # write_extraction_output (exists)
    extract.py           # extract_content orchestrator (exists)

tests/
    fixtures/
        wechat_article.json       # Already exists
        sample_article.html       # NEW: realistic WeChat OA HTML fixture
    test_article_extractor.py     # NEW: unit tests for ArticleExtractor
```

### Pattern 1: Adapter Implementation Pattern

**What:** Each adapter satisfies the Extractor Protocol via structural subtyping. It reads files from `content_dir`, processes them, and returns an immutable `ExtractionResult`.

**When to use:** Every content type adapter follows this pattern.

**Example:**
```python
# Source: Extractor Protocol from base.py + trafilatura API
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import trafilatura

from content_extractor.models import (
    ExtractionResult,
    MediaDescription,
    QualityMetadata,
)

if TYPE_CHECKING:
    from content_extractor.config import ExtractorConfig


class ArticleExtractor:
    """Extract clean text from article HTML content."""

    content_type: str = "article"

    def extract(
        self, content_dir: Path, config: ExtractorConfig
    ) -> ExtractionResult:
        """Clean and structure article HTML into markdown."""
        # 1. Find the HTML file in content_dir/media/
        html_content = self._load_html(content_dir)

        # 2. Extract text + metadata via trafilatura
        result = trafilatura.bare_extraction(
            html_content,
            output_format="markdown",
            include_formatting=True,
            include_links=False,
            include_tables=True,
            include_comments=False,
            favor_precision=True,
        )

        # 3. Handle extraction failure
        if result is None:
            # Return minimal result with empty text
            ...

        # 4. Build ExtractionResult from Document
        ...
```

### Pattern 2: HTML File Discovery

**What:** Article ContentItems from content-downloader store HTML in `media/` with names like `article.html`. The adapter needs to find the HTML file(s).

**When to use:** When the adapter needs to locate the raw content file.

**Example:**
```python
def _load_html(self, content_dir: Path) -> str:
    """Find and read the article HTML file from media/ directory."""
    media_dir = content_dir / "media"
    # Look for .html files
    html_files = sorted(media_dir.glob("*.html"))
    if not html_files:
        raise ArticleExtractionError(
            f"No HTML files found in {media_dir}"
        )
    # Use the first HTML file (articles typically have one)
    return html_files[0].read_text(encoding="utf-8")
```

### Pattern 3: Metadata Mapping

**What:** Map trafilatura's Document fields to ExtractionResult + QualityMetadata.

**When to use:** When building the return value from bare_extraction output.

**Key mapping:**
```python
# trafilatura Document -> ExtractionResult fields
doc.text       -> raw_text (the cleaned markdown)
doc.author     -> platform_metadata["extracted_author"]
doc.date       -> platform_metadata["extracted_date"]
doc.title      -> platform_metadata["extracted_title"]
doc.sitename   -> platform_metadata["extracted_sitename"]
doc.categories -> platform_metadata["extracted_categories"]
doc.tags       -> platform_metadata["extracted_tags"]
doc.language   -> quality.language
len(text.split()) -> quality.word_count
```

### Anti-Patterns to Avoid
- **Parsing HTML manually with regex or string operations:** Use trafilatura -- it handles encoding, malformed HTML, boilerplate removal automatically.
- **Ignoring trafilatura returning None:** `extract()` and `bare_extraction()` return None when no main content is found. This is common with non-article pages. Always handle this case.
- **Storing metadata in ContentItem (mutation):** ContentItem is frozen. Article metadata goes into ExtractionResult.platform_metadata dict.
- **Using `include_formatting=False` with `output_format="markdown"`:** Without formatting, markdown output degrades to plain text. Always pair markdown output with `include_formatting=True`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML boilerplate removal | Custom xpath/css selectors for ads, nav, footer | `trafilatura.bare_extraction()` | Trafilatura uses scoring heuristics tested across millions of pages. Custom selectors break on every new site layout. |
| Article date extraction | Custom regex for date patterns | trafilatura's built-in `date` field (uses `htmldate` under the hood) | Date formats vary wildly (ISO, Chinese, relative). htmldate handles 100+ formats. |
| Author extraction | Custom meta tag / byline parsing | trafilatura's built-in `author` field | Author attribution appears in meta tags, JSON-LD, bylines, header -- trafilatura checks all. |
| Encoding detection | `chardet` + manual decoding | trafilatura handles encoding internally | WeChat articles may use GB2312, GBK, or UTF-8. trafilatura normalizes. |
| Word count for Chinese | `len(text.split())` | Simple `len(text)` for character count + `len(text.split())` for approximate word count | Chinese text has no spaces between words. A simple split-based word count underestimates for Chinese. Use character count as primary metric for Chinese content. |

**Key insight:** trafilatura is specifically built to handle the messy reality of web articles. Every "simple" HTML cleaning task (encoding, boilerplate, date parsing) has edge cases that trafilatura has already solved.

## Common Pitfalls

### Pitfall 1: trafilatura Returns None on Valid Articles
**What goes wrong:** `bare_extraction()` returns None when it cannot identify the main content area, even if the HTML contains article text.
**Why it happens:** WeChat OA HTML has non-standard structure. Trafilatura's heuristics may not recognize the content area.
**How to avoid:** Test with real WeChat OA HTML early. If trafilatura fails on WeChat structure, use `no_fallback=False` (default) to enable fallback extraction. If that also fails, consider passing the HTML through a minimal pre-processing step to extract the `#js_content` div (WeChat's article container ID).
**Warning signs:** Tests pass with clean HTML but fail with real WeChat content.

### Pitfall 2: Chinese Word Count Is Misleading
**What goes wrong:** `len(text.split())` returns a very low number for Chinese text because Chinese doesn't use spaces between words.
**Why it happens:** Word splitting by whitespace works for English but not Chinese/Japanese/Korean.
**How to avoid:** Use character count as the primary metric. For word count, count non-whitespace characters for CJK text. A simple heuristic: if the text contains CJK characters, use `len(text)` minus whitespace as the word count proxy.
**Warning signs:** Quality metadata shows word_count=5 for a 2000-character Chinese article.

### Pitfall 3: HTML File Not Found in media/
**What goes wrong:** ArticleExtractor raises an error because no `.html` file exists in the expected location.
**Why it happens:** Article content_item.json may reference HTML files by a different naming convention, or the HTML might be at a different path within the content directory.
**How to avoid:** Use `content_item.media_files` from the loaded ContentItem to locate the HTML file, rather than blindly globbing. The fixture shows `"media_files": ["media/article.html", "media/img_01.jpg"]` -- filter for `.html` extensions.
**Warning signs:** Works with test fixtures but fails on real downloader output.

### Pitfall 4: Encoding Issues with WeChat HTML
**What goes wrong:** Chinese characters appear as garbled text or mojibake.
**Why it happens:** WeChat OA HTML may declare one encoding in meta tags but use another in practice. Or the file was saved without proper encoding declaration.
**How to avoid:** Read files as bytes and let trafilatura handle encoding detection. If reading as text, use `encoding="utf-8"` with `errors="replace"` as a safety net.
**Warning signs:** Output contains sequences like `\xe4\xb8\xad` or `???` instead of Chinese characters.

### Pitfall 5: bare_extraction Output Format Differences
**What goes wrong:** Code expects `bare_extraction()` to return a dict but gets a Document object, or vice versa.
**Why it happens:** `bare_extraction()` returns a `Document` object by default, but returns a `dict` when `as_dict=True` is passed.
**How to avoid:** Use `bare_extraction(..., as_dict=False)` (default) and access attributes like `doc.text`, `doc.author`, `doc.date`. The Document object is more type-safe.
**Warning signs:** `AttributeError: 'dict' object has no attribute 'text'` or `TypeError: 'Document' object is not subscriptable`.

## Code Examples

### Example 1: Basic Article Extraction with trafilatura
```python
# Source: trafilatura GitHub + official docs
import trafilatura

# Read HTML content
html = Path("media/article.html").read_text(encoding="utf-8")

# Option A: Get just the text as markdown
text = trafilatura.extract(
    html,
    output_format="markdown",
    include_formatting=True,
    include_tables=True,
    include_comments=False,
)

# Option B: Get text + metadata together (RECOMMENDED)
doc = trafilatura.bare_extraction(
    html,
    output_format="markdown",
    include_formatting=True,
    include_tables=True,
    include_comments=False,
)
if doc is not None:
    text = doc.text          # cleaned markdown text
    author = doc.author      # str or None
    date = doc.date          # str (YYYY-MM-DD) or None
    title = doc.title        # str or None
    language = doc.language   # str or None
```

### Example 2: Building ExtractionResult from trafilatura Document
```python
# Source: models.py ExtractionResult schema + trafilatura Document
import time

def _build_result(
    doc: trafilatura.settings.Document,
    content_id: str,
    start_time: float,
) -> ExtractionResult:
    text = doc.text or ""
    word_count = _compute_word_count(text)

    return ExtractionResult(
        content_id=content_id,
        content_type="article",
        raw_text=text,
        transcript=None,  # Articles don't have transcripts
        media_descriptions=(),
        quality=QualityMetadata(
            confidence=1.0 if text else 0.0,
            language=doc.language or "unknown",
            word_count=word_count,
            processing_time_seconds=time.monotonic() - start_time,
        ),
        platform_metadata={
            "extracted_author": doc.author or "",
            "extracted_date": doc.date or "",
            "extracted_title": doc.title or "",
            "extracted_sitename": doc.sitename or "",
        },
    )
```

### Example 3: Chinese-Aware Word Count
```python
import re

def _compute_word_count(text: str) -> int:
    """Compute word count, handling both CJK and Latin text."""
    if not text:
        return 0
    # Count CJK characters (each is roughly a "word")
    cjk_chars = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', text))
    # Count space-separated words (Latin text)
    latin_words = len(re.findall(r'[a-zA-Z]+', text))
    return cjk_chars + latin_words
```

### Example 4: WeChat OA HTML Pre-Processing (Fallback)
```python
# Only needed if trafilatura fails on raw WeChat HTML
from lxml import html as lxml_html

def _extract_wechat_content(raw_html: str) -> str:
    """Extract the #js_content div from WeChat OA HTML as fallback."""
    tree = lxml_html.fromstring(raw_html)
    content_divs = tree.cssselect("#js_content")
    if content_divs:
        # Re-serialize just the content div for trafilatura
        from lxml.html import tostring
        return tostring(content_divs[0], encoding="unicode")
    return raw_html  # Fall through to full page
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| trafilatura `extract()` returns string only | `bare_extraction()` returns Document with text + metadata | Available since trafilatura 1.x, refined in 2.0 | Use bare_extraction for unified text+metadata access |
| `output_format="txt"` default | `output_format="markdown"` available | trafilatura 1.x+ | Markdown preserves headings/lists/emphasis that txt loses |
| readability-lxml for article extraction | trafilatura dominates benchmarks | 2023+ | F1=0.960 vs readability-lxml's lower scores |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_article_extractor.py -x` |
| Full suite command | `pytest --cov=content_extractor --cov-report=term-missing` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARTC-01 | HTML -> clean markdown via trafilatura | unit | `pytest tests/test_article_extractor.py::TestArticleClean -x` | No -- Wave 0 |
| ARTC-02 | Preserve headings, lists, emphasis in markdown | unit | `pytest tests/test_article_extractor.py::TestArticleStructure -x` | No -- Wave 0 |
| ARTC-03 | Extract author, date, word count metadata | unit | `pytest tests/test_article_extractor.py::TestArticleMetadata -x` | No -- Wave 0 |
| E2E | Full pipeline: content_dir -> 3 output files | integration | `pytest tests/test_article_extractor.py::TestArticleEndToEnd -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_article_extractor.py -x`
- **Per wave merge:** `pytest --cov=content_extractor --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_article_extractor.py` -- covers ARTC-01, ARTC-02, ARTC-03, and E2E
- [ ] `tests/fixtures/sample_article.html` -- realistic WeChat OA HTML for testing
- [ ] Add `trafilatura>=2.0,<3` to pyproject.toml dependencies
- [ ] `pip install -e ".[dev]"` to install trafilatura locally

## Open Questions

1. **WeChat OA HTML structure compatibility with trafilatura**
   - What we know: trafilatura works well on standard web articles. WeChat OA uses `#js_content` as the main content container.
   - What's unclear: Whether trafilatura's heuristics correctly identify WeChat OA article content area out of the box, or if pre-processing is needed.
   - Recommendation: Test with a real WeChat OA HTML file early. If trafilatura fails, implement the `#js_content` extraction fallback shown in Code Examples.

2. **Content in media_files vs raw HTML**
   - What we know: The wechat_article.json fixture shows `"media_files": ["media/article.html", "media/img_01.jpg"]`. The HTML file is listed alongside images.
   - What's unclear: Whether all article types store HTML in media_files, or if some store article text differently (e.g., in description field or as plain text).
   - Recommendation: Filter media_files for `.html`/`.htm` extensions. Fall back to description field if no HTML file found.

## Sources

### Primary (HIGH confidence)
- [trafilatura GitHub core.py](https://github.com/adbar/trafilatura/blob/master/trafilatura/core.py) -- extract() and bare_extraction() full signatures verified
- [trafilatura GitHub settings.py](https://github.com/adbar/trafilatura/blob/master/trafilatura/settings.py) -- Document class fields verified (20 fields)
- [trafilatura GitHub metadata.py](https://github.com/adbar/trafilatura/blob/master/trafilatura/metadata.py) -- extract_metadata() signature verified
- Phase 1 source code -- Extractor Protocol, models.py, output.py, extract.py reviewed directly

### Secondary (MEDIUM confidence)
- [trafilatura readthedocs](https://trafilatura.readthedocs.io/en/latest/) -- API docs (blocked by Cloudflare, verified via GitHub source instead)
- [trafilatura PyPI](https://pypi.org/project/trafilatura/) -- v2.0.0, Python 3.8-3.13

### Tertiary (LOW confidence)
- WeChat OA `#js_content` div convention -- based on training data knowledge, not verified against current WeChat OA pages. Needs validation with real HTML.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- trafilatura 2.0.0 verified on PyPI and GitHub, API signatures confirmed from source
- Architecture: HIGH -- adapter pattern already established in Phase 1, just implementing the stub
- Pitfalls: MEDIUM -- WeChat-specific issues based on training data, not tested with real content
- Code examples: HIGH -- API signatures verified directly from trafilatura source code on GitHub

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (trafilatura is stable, unlikely to change)

"""Article content extractor using trafilatura.

Cleans HTML into structured markdown and extracts metadata
(author, date, title, word count). Handles CJK text correctly.

Uses trafilatura.extract() for markdown output and
trafilatura.metadata.extract_metadata() for article metadata,
since bare_extraction() does not reliably populate both.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import trafilatura
from trafilatura.metadata import extract_metadata

from content_extractor.config import ExtractorConfig
from content_extractor.loader import load_content_item
from content_extractor.models import ExtractionResult, QualityMetadata


class ArticleExtractionError(Exception):
    """Raised when article extraction fails due to missing or invalid input."""


def _compute_word_count(text: str) -> int:
    """Compute word count handling both CJK and Latin text.

    CJK characters are counted individually (each is roughly a word).
    Latin words are counted by matching alphabetic sequences.
    """
    if not text:
        return 0
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", text))
    latin_words = len(re.findall(r"[a-zA-Z]+", text))
    return cjk_chars + latin_words


def _detect_language(text: str) -> str:
    """Simple language detection based on CJK character ratio."""
    if not text:
        return "unknown"
    cjk_count = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", text))
    if cjk_count > len(text) * 0.1:
        return "zh"
    return "en"


class ArticleExtractor:
    """Extract clean text from article HTML content."""

    content_type: str = "article"

    def _load_html(self, content_dir: Path) -> str:
        """Find and read the article HTML file from a content directory.

        Checks content_item.json media_files for .html/.htm entries first,
        then falls back to globbing media/*.html.
        """
        item = load_content_item(content_dir)

        # Filter media_files for HTML entries
        html_files = [
            f for f in item.media_files if f.endswith((".html", ".htm"))
        ]

        if html_files:
            html_path = content_dir / html_files[0]
        else:
            # Fallback: glob media directory
            media_dir = content_dir / "media"
            candidates = sorted(media_dir.glob("*.html"))
            if not candidates:
                raise ArticleExtractionError(
                    f"No HTML files found in {content_dir}"
                )
            html_path = candidates[0]

        return html_path.read_text(encoding="utf-8", errors="replace")

    def extract(
        self, content_dir: Path, config: ExtractorConfig
    ) -> ExtractionResult:
        """Clean and structure article HTML into markdown."""
        start_time = time.monotonic()

        html_content = self._load_html(content_dir)
        item = load_content_item(content_dir)

        # Extract markdown text via extract() with favor_recall
        # to preserve headings, lists, emphasis in output
        text = trafilatura.extract(
            html_content,
            output_format="markdown",
            include_formatting=True,
            include_tables=True,
            include_comments=False,
            include_links=False,
            no_fallback=False,
            favor_recall=True,
        ) or ""

        # Extract metadata separately (author, date, title, sitename)
        meta = extract_metadata(html_content)

        elapsed = time.monotonic() - start_time

        if not text:
            return ExtractionResult(
                content_id=item.content_id,
                content_type="article",
                raw_text="",
                quality=QualityMetadata(
                    confidence=0.0,
                    processing_time_seconds=elapsed,
                ),
            )

        word_count = _compute_word_count(text)
        language = _detect_language(text)

        author = meta.author if meta else ""
        date = meta.date if meta else ""
        title = meta.title if meta else ""
        sitename = meta.sitename if meta else ""

        return ExtractionResult(
            content_id=item.content_id,
            content_type="article",
            raw_text=text,
            transcript=None,
            media_descriptions=(),
            quality=QualityMetadata(
                confidence=1.0,
                language=language,
                word_count=word_count,
                processing_time_seconds=elapsed,
            ),
            platform_metadata={
                "extracted_author": author or "",
                "extracted_date": date or "",
                "extracted_title": title or "",
                "extracted_sitename": sitename or "",
            },
        )

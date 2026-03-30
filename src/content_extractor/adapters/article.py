"""Article content extractor stub.

Actual implementation in Phase 4 (trafilatura HTML cleaning).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from content_extractor.models import ExtractionResult


class ArticleExtractor:
    """Extract clean text from article HTML content."""

    content_type: str = "article"

    def extract(
        self, content_dir: Path, config: "ExtractorConfig"
    ) -> "ExtractionResult":
        """Clean and structure article content."""
        raise NotImplementedError(
            f"{self.content_type} extraction not yet implemented"
        )

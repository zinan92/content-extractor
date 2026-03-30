"""Image content extractor stub.

Actual implementation in Phase 3 (Claude vision).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from content_extractor.models import ExtractionResult


class ImageExtractor:
    """Extract text from image content via vision API."""

    content_type: str = "image"

    def extract(
        self, content_dir: Path, config: "ExtractorConfig"
    ) -> "ExtractionResult":
        """Extract descriptions and OCR text from images."""
        raise NotImplementedError(
            f"{self.content_type} extraction not yet implemented"
        )

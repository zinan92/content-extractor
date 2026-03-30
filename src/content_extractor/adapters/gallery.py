"""Gallery content extractor stub.

Actual implementation in Phase 5 (multi-image Claude vision + narrative).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from content_extractor.models import ExtractionResult


class GalleryExtractor:
    """Extract text from gallery (multi-image) content."""

    content_type: str = "gallery"

    def extract(
        self, content_dir: Path, config: "ExtractorConfig"
    ) -> "ExtractionResult":
        """Extract descriptions from all gallery images and synthesize narrative."""
        raise NotImplementedError(
            f"{self.content_type} extraction not yet implemented"
        )

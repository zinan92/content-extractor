"""Video content extractor stub.

Actual implementation in Phase 2 (faster-whisper transcription).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from content_extractor.models import ExtractionResult


class VideoExtractor:
    """Extract text from video content via speech-to-text."""

    content_type: str = "video"

    def extract(
        self, content_dir: Path, config: "ExtractorConfig"
    ) -> "ExtractionResult":
        """Extract transcript from video files."""
        raise NotImplementedError(
            f"{self.content_type} extraction not yet implemented"
        )

"""Content extractor -- turn raw multimedia into structured text."""

from content_extractor.extract import (
    BatchError,
    BatchResult,
    extract_batch,
    extract_content,
)
from content_extractor.loader import (
    ContentItemInvalidError,
    ContentItemNotFoundError,
    load_content_item,
)

__version__ = "0.1.0"

__all__ = [
    "BatchError",
    "BatchResult",
    "ContentItemInvalidError",
    "ContentItemNotFoundError",
    "extract_batch",
    "extract_content",
    "load_content_item",
]

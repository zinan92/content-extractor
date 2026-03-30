"""Atomic output writer with idempotency guard.

Writes transcript.json, analysis.json, and structured_text.md to a content
directory using atomic temp-file-then-rename. Uses .extraction_complete marker
for idempotency -- skips already-extracted items unless force=True.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import orjson

from content_extractor.models import AnalysisResult, ExtractionResult

if TYPE_CHECKING:
    from content_extractor.models import ContentItem

MARKER_FILE = ".extraction_complete"


# ---------------------------------------------------------------------------
# Atomic writers
# ---------------------------------------------------------------------------


def write_json_atomic(path: Path, data: bytes) -> None:
    """Write JSON bytes atomically via temp file + rename.

    On failure, the temp file is cleaned up (QUAL-03).
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_bytes(data)
        tmp.rename(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def write_text_atomic(path: Path, text: str) -> None:
    """Write UTF-8 text atomically via temp file + rename.

    On failure, the temp file is cleaned up (QUAL-03).
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        tmp.rename(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Idempotency marker
# ---------------------------------------------------------------------------


def is_extracted(content_dir: Path) -> bool:
    """Check if content has already been extracted."""
    return (content_dir / MARKER_FILE).exists()


def mark_complete(content_dir: Path) -> None:
    """Mark content as extracted by creating the completion marker."""
    (content_dir / MARKER_FILE).touch()


def clear_marker(content_dir: Path) -> None:
    """Remove the extraction marker (for --force reprocessing)."""
    (content_dir / MARKER_FILE).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Structured text rendering (D-04)
# ---------------------------------------------------------------------------


def _render_structured_text(
    result: ExtractionResult,
    *,
    item_title: str,
    item_author: str,
    item_platform: str,
    item_publish_time: str,
    item_likes: int = 0,
    item_comments: int = 0,
    item_shares: int = 0,
) -> str:
    """Render structured_text.md in D-04 report format."""
    return (
        f"# {item_title}\n"
        f"\n"
        f"**Author:** {item_author} | **Platform:** {item_platform}"
        f" | **Published:** {item_publish_time}\n"
        f"**Engagement:** {item_likes} likes, {item_comments} comments,"
        f" {item_shares} shares\n"
        f"\n"
        f"## Summary\n"
        f"\n"
        f"*Populated by analysis phase.*\n"
        f"\n"
        f"## Key Takeaways\n"
        f"\n"
        f"*Populated by analysis phase.*\n"
        f"\n"
        f"## Full Transcript/Content\n"
        f"\n"
        f"{result.raw_text}\n"
        f"\n"
        f"## Analysis\n"
        f"\n"
        f"*Populated by analysis phase.*\n"
    )


# ---------------------------------------------------------------------------
# High-level output writer
# ---------------------------------------------------------------------------


def write_extraction_output(
    content_dir: Path,
    result: ExtractionResult,
    content_item: "ContentItem",
    *,
    force: bool = False,
) -> bool:
    """Write all extraction output files to content_dir.

    Returns True if files were written, False if skipped (already extracted).

    When force=True, clears the marker and re-writes all files (FOUND-05).
    """
    if is_extracted(content_dir) and not force:
        return False

    if force:
        clear_marker(content_dir)

    # transcript.json
    if result.transcript is not None:
        transcript_data = orjson.dumps(
            result.transcript.model_dump(), option=orjson.OPT_INDENT_2
        )
    else:
        transcript_data = orjson.dumps(
            {
                "content_id": result.content_id,
                "content_type": result.content_type,
                "full_text": result.raw_text,
            },
            option=orjson.OPT_INDENT_2,
        )
    write_json_atomic(content_dir / "transcript.json", transcript_data)

    # analysis.json (placeholder -- populated by Phase 8)
    placeholder_analysis = AnalysisResult(
        content_id=result.content_id,
        content_type=result.content_type,
    )
    analysis_data = orjson.dumps(
        placeholder_analysis.model_dump(), option=orjson.OPT_INDENT_2
    )
    write_json_atomic(content_dir / "analysis.json", analysis_data)

    # structured_text.md (D-04)
    md_text = _render_structured_text(
        result,
        item_title=content_item.title,
        item_author=content_item.author_name,
        item_platform=content_item.platform,
        item_publish_time=content_item.publish_time,
        item_likes=content_item.likes,
        item_comments=content_item.comments,
        item_shares=content_item.shares,
    )
    write_text_atomic(content_dir / "structured_text.md", md_text)

    mark_complete(content_dir)
    return True

"""Video content extractor.

Orchestrates the video extraction pipeline:
find video -> probe audio -> extract audio -> transcribe -> build result.

Uses FFmpeg for audio extraction and faster-whisper for transcription.
Handles no-audio gracefully and always cleans up temp files.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from content_extractor.config import ExtractorConfig
from content_extractor.loader import load_content_item
from content_extractor.models import (
    ExtractionResult,
    QualityMetadata,
    Transcript,
    TranscriptSegment,
)
from content_extractor.video.ffmpeg import extract_audio, probe_audio_stream
from content_extractor.video.transcribe import transcribe_audio

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = (".mp4", ".mov", ".webm", ".avi", ".mkv", ".flv")


def _find_video_file(content_dir: Path) -> Path:
    """Find the first video file in content_dir/media/.

    Raises
    ------
    FileNotFoundError
        If no video file with a recognized extension is found.
    """
    media_dir = content_dir / "media"
    if not media_dir.exists():
        raise FileNotFoundError(f"No video file in {media_dir}")

    for child in sorted(media_dir.iterdir()):
        if child.is_file() and child.suffix.lower() in VIDEO_EXTENSIONS:
            return child

    raise FileNotFoundError(f"No video file in {media_dir}")


def _compute_word_count(text: str) -> int:
    """Compute word count handling CJK and Latin text.

    Each CJK character counts as one word.
    Latin alphabetic sequences count as one word each.
    """
    if not text:
        return 0
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", text))
    latin_words = len(re.findall(r"[a-zA-Z]+", text))
    return cjk_chars + latin_words


def _build_platform_metadata(
    item: object,
) -> dict[str, int | str]:
    """Extract non-zero engagement fields from a ContentItem."""
    fields = ("likes", "comments", "shares", "collects", "views")
    metadata: dict[str, int | str] = {}
    for field in fields:
        value = getattr(item, field, 0)
        if value:
            metadata[field] = value
    return metadata


class VideoExtractor:
    """Extract text from video content via speech-to-text."""

    content_type: str = "video"

    def extract(
        self, content_dir: Path, config: ExtractorConfig
    ) -> ExtractionResult:
        """Extract transcript from video files.

        Pipeline: find video -> probe -> extract audio -> transcribe -> result.

        Videos with no audio stream return a result with empty transcript
        and confidence=0.0 (not an error).
        """
        item = load_content_item(content_dir)
        video_path = _find_video_file(content_dir)
        start_time = time.monotonic()

        # Probe for audio stream
        probe = probe_audio_stream(video_path)

        if not probe.has_audio:
            elapsed = time.monotonic() - start_time
            logger.info("No audio stream in %s", video_path)
            return ExtractionResult(
                content_id=item.content_id,
                content_type="video",
                raw_text="",
                transcript=None,
                quality=QualityMetadata(
                    confidence=0.0,
                    language="zh",
                    word_count=0,
                    processing_time_seconds=elapsed,
                ),
                platform_metadata=_build_platform_metadata(item),
            )

        # Extract audio to temp WAV
        wav_path = content_dir / "media" / ".tmp_audio.wav"

        try:
            extract_audio(video_path, wav_path)
            segments = transcribe_audio(
                wav_path,
                whisper_model=config.whisper_model,
            )
        finally:
            # Always clean up temp file
            if wav_path.exists():
                wav_path.unlink()

        elapsed = time.monotonic() - start_time

        # Build transcript
        full_text = " ".join(seg.text for seg in segments)
        avg_confidence = (
            sum(s.confidence for s in segments) / len(segments)
            if segments
            else 0.0
        )
        word_count = _compute_word_count(full_text)

        transcript = Transcript(
            content_id=item.content_id,
            content_type="video",
            language="zh",
            segments=segments,
            full_text=full_text,
        )

        quality = QualityMetadata(
            confidence=avg_confidence,
            language="zh",
            word_count=word_count,
            processing_time_seconds=elapsed,
        )

        return ExtractionResult(
            content_id=item.content_id,
            content_type="video",
            raw_text=full_text,
            transcript=transcript,
            quality=quality,
            platform_metadata=_build_platform_metadata(item),
        )

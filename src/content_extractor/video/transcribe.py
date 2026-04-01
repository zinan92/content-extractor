"""Faster-whisper transcription module.

Wraps faster-whisper with anti-hallucination settings:
- condition_on_previous_text=False to prevent cascade errors
- vad_filter=True with min_silence_duration_ms=500
- no_speech_prob > 0.6 filtering
- Explicit language='zh' with Chinese initial_prompt

Model instances are cached to avoid ~5 second reload per call.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path

from faster_whisper import WhisperModel

from content_extractor.models import TranscriptSegment

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Raised when transcription fails."""


@dataclass(frozen=True)
class TranscriptionResult:
    """Result of transcription including VAD metadata.

    Attributes
    ----------
    segments:
        Immutable tuple of transcript segments with timestamps.
    speech_ratio:
        Fraction of audio containing speech (from VAD), 0.0 to 1.0.
    duration_seconds:
        Total audio duration in seconds.
    """

    segments: tuple[TranscriptSegment, ...]
    speech_ratio: float
    duration_seconds: float


# Module-level model cache. Justified by ~5s model load time.
# This is the ONE mutable module-level state.
_model_cache: dict[str, WhisperModel] = {}


def _get_model(model_name: str) -> WhisperModel:
    """Return a cached WhisperModel, loading if necessary.

    Parameters
    ----------
    model_name:
        Model size or path (e.g. "turbo", "large-v3").

    Returns
    -------
    WhisperModel
        Cached or freshly loaded model instance.

    Raises
    ------
    TranscriptionError
        If the model fails to load.
    """
    if model_name in _model_cache:
        return _model_cache[model_name]

    logger.info("Loading Whisper model: %s", model_name)

    try:
        model = WhisperModel(
            model_size_or_path=model_name,
            device="auto",
            compute_type="int8",
        )
    except Exception as exc:
        raise TranscriptionError(
            f"Failed to load Whisper model '{model_name}': {exc}"
        ) from exc

    _model_cache[model_name] = model
    return model


def transcribe_audio(
    audio_path: Path,
    *,
    whisper_model: str = "turbo",
    language: str = "zh",
) -> TranscriptionResult:
    """Transcribe an audio file using faster-whisper.

    Parameters
    ----------
    audio_path:
        Path to a WAV audio file (16kHz mono recommended).
    whisper_model:
        Model name for faster-whisper (default "turbo").
    language:
        Language code for transcription (default "zh").

    Returns
    -------
    TranscriptionResult
        Frozen dataclass with segments, speech_ratio, and duration.

    Raises
    ------
    TranscriptionError
        If the model fails to load.
    """
    model = _get_model(whisper_model)

    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language,
        initial_prompt="以下是普通话的句子。",
        condition_on_previous_text=False,
        beam_size=1,
        best_of=1,
        temperature=0.0,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )

    segments: list[TranscriptSegment] = []

    for segment in segments_iter:
        if segment.no_speech_prob > 0.6:
            continue

        raw_confidence = math.exp(segment.avg_logprob)
        confidence = min(max(raw_confidence, 0.0), 1.0)

        segments.append(
            TranscriptSegment(
                text=segment.text.strip(),
                start=segment.start,
                end=segment.end,
                confidence=confidence,
            )
        )

    duration = info.duration if info.duration else 0.0
    speech_ratio = (
        info.duration_after_vad / duration
        if duration > 0
        else 0.0
    )

    return TranscriptionResult(
        segments=tuple(segments),
        speech_ratio=speech_ratio,
        duration_seconds=duration,
    )

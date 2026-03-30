"""LLM-powered content analysis module.

Sends extracted text to Claude and returns a structured AnalysisResult
with topics, viewpoints, sentiment, and takeaways.

Usage:
    from content_extractor.analysis import analyze_content
    result = analyze_content("article text...", content_id="x", content_type="article")
"""

from __future__ import annotations

import logging

import orjson

from content_extractor.config import ExtractorConfig
from content_extractor.llm import create_claude_client
from content_extractor.models import AnalysisResult, SentimentResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class AnalysisError(Exception):
    """Raised when LLM analysis fails (API error, timeout, etc.)."""


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_ANALYSIS_PROMPT = """\
Analyze the following text and return a JSON object with exactly these fields:

{
  "topics": ["topic1", "topic2", ...],
  "viewpoints": ["viewpoint1", "viewpoint2", ...],
  "sentiment": {"overall": "positive|negative|neutral|mixed", "confidence": 0.0},
  "takeaways": ["takeaway1", "takeaway2", ...]
}

Rules:
- topics: 3-7 main themes or subjects discussed in the content
- viewpoints: core arguments, perspectives, or positions presented
- sentiment: overall emotional tone with confidence score (0.0-1.0)
  - "positive", "negative", "neutral", or "mixed"
- takeaways: actionable insights or key lessons from the content
- Handle both Chinese and English content naturally
- Return ONLY valid JSON, no markdown fences or extra text
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_content(
    raw_text: str,
    *,
    content_id: str,
    content_type: str,
    config: ExtractorConfig | None = None,
) -> AnalysisResult:
    """Analyze extracted text via Claude and return structured AnalysisResult.

    Parameters
    ----------
    raw_text:
        The extracted text to analyze.
    content_id:
        Identifier for the content item.
    content_type:
        Type of content (video, article, image, gallery).
    config:
        Optional ExtractorConfig with LLM settings.

    Returns
    -------
    AnalysisResult
        Structured analysis with topics, viewpoints, sentiment, takeaways.

    Raises
    ------
    AnalysisError
        If the LLM API call fails.
    """
    config = config if config is not None else ExtractorConfig()

    # Empty input -- return fallback without calling LLM
    if not raw_text or not raw_text.strip():
        return AnalysisResult(
            content_id=content_id,
            content_type=content_type,
        )

    client = create_claude_client(config)

    # Call LLM
    try:
        response = client.messages.create(
            model=config.claude_model,
            max_tokens=config.claude_max_tokens,
            temperature=config.claude_temperature,
            messages=[
                {
                    "role": "user",
                    "content": f"{_ANALYSIS_PROMPT}\n\n---\n\n{raw_text}",
                }
            ],
        )
    except Exception as exc:
        raise AnalysisError(f"LLM API call failed: {exc}") from exc

    # Extract text from response
    response_text = ""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            response_text = block.text
            break

    # Parse JSON response
    try:
        parsed = orjson.loads(response_text)
    except (orjson.JSONDecodeError, ValueError, TypeError):
        logger.warning(
            "Failed to parse analysis JSON for %s, returning fallback",
            content_id,
        )
        return AnalysisResult(
            content_id=content_id,
            content_type=content_type,
        )

    # Map parsed dict to AnalysisResult
    sentiment_data = parsed.get("sentiment")
    sentiment = None
    if isinstance(sentiment_data, dict):
        sentiment = SentimentResult(
            overall=sentiment_data.get("overall", "neutral"),
            confidence=float(sentiment_data.get("confidence", 0.0)),
        )

    return AnalysisResult(
        content_id=content_id,
        content_type=content_type,
        topics=tuple(parsed.get("topics", ())),
        viewpoints=tuple(parsed.get("viewpoints", ())),
        sentiment=sentiment,
        takeaways=tuple(parsed.get("takeaways", ())),
    )

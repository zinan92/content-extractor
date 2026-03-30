"""Tests for vision module and ImageExtractor adapter."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from content_extractor.config import ExtractorConfig


# ---------------------------------------------------------------------------
# Task 1: Vision module tests — preprocess_image + describe_image
# ---------------------------------------------------------------------------


class TestPreprocessImage:
    """Tests for preprocess_image function."""

    def test_small_jpeg_no_resize(self, tmp_image_dir: Path) -> None:
        """A small JPEG (100x100) should not be resized."""
        from content_extractor.vision import preprocess_image

        b64, media_type = preprocess_image(tmp_image_dir / "media" / "test.jpg")
        assert isinstance(b64, str)
        assert media_type == "image/jpeg"
        assert len(b64) > 0

    def test_large_image_resized(self, tmp_path: Path) -> None:
        """An image larger than 1568px should be resized proportionally."""
        from content_extractor.vision import preprocess_image

        large_img = Image.new("RGB", (3000, 4000), color=(0, 128, 255))
        img_path = tmp_path / "large.png"
        large_img.save(img_path, "PNG")

        b64, media_type = preprocess_image(img_path)
        assert media_type == "image/png"
        assert len(b64) > 0

    def test_unsupported_format_converted_to_jpeg(self, tmp_path: Path) -> None:
        """BMP (unsupported by Claude) should be converted to JPEG."""
        from content_extractor.vision import preprocess_image

        bmp_img = Image.new("RGB", (200, 200), color=(0, 255, 0))
        img_path = tmp_path / "test.bmp"
        bmp_img.save(img_path, "BMP")

        b64, media_type = preprocess_image(img_path)
        assert media_type == "image/jpeg"

    def test_nonexistent_file_raises(self, tmp_path: Path) -> None:
        """preprocess_image should raise FileNotFoundError for missing file."""
        from content_extractor.vision import preprocess_image

        with pytest.raises(FileNotFoundError):
            preprocess_image(tmp_path / "nope.jpg")

    def test_rgba_png_converted_to_rgb_for_jpeg(self, tmp_path: Path) -> None:
        """RGBA image converted to JPEG should first drop alpha channel."""
        from content_extractor.vision import preprocess_image

        rgba_img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        img_path = tmp_path / "alpha.bmp"
        rgba_img.save(img_path, "BMP")

        b64, media_type = preprocess_image(img_path)
        assert media_type == "image/jpeg"
        assert len(b64) > 0


class TestDescribeImage:
    """Tests for describe_image function."""

    def _make_mock_response(self, text_content: str) -> MagicMock:
        """Create a mock anthropic response object."""
        mock_resp = MagicMock()
        content_block = SimpleNamespace(type="text", text=text_content)
        mock_resp.content = [content_block]
        return mock_resp

    def test_describe_image_calls_api_correctly(
        self, mock_vision_response_json: str
    ) -> None:
        """describe_image should call client.messages.create with image block."""
        from content_extractor.vision import describe_image

        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response(
            mock_vision_response_json
        )

        config = ExtractorConfig()

        with patch(
            "content_extractor.vision.create_claude_client",
            return_value=mock_client,
        ):
            result = describe_image("base64data", "image/jpeg", config)

        # Verify API was called
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == config.claude_model
        assert call_kwargs.kwargs["max_tokens"] == config.claude_max_tokens

        # Verify result parsed correctly
        assert result.ocr_text == "小红书爆款笔记分享"
        assert "Chinese text overlay" in result.visual_description
        assert result.confidence == pytest.approx(0.92)

    def test_describe_image_malformed_json(self) -> None:
        """Malformed JSON response should use raw text as description."""
        from content_extractor.vision import describe_image

        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response(
            "This is not valid JSON but a description of the image"
        )

        config = ExtractorConfig()

        with patch(
            "content_extractor.vision.create_claude_client",
            return_value=mock_client,
        ):
            result = describe_image("base64data", "image/jpeg", config)

        assert result.visual_description == (
            "This is not valid JSON but a description of the image"
        )
        assert result.ocr_text == ""
        assert result.confidence == 0.0

    def test_describe_image_api_error(self) -> None:
        """API errors should raise ImageExtractionError."""
        from content_extractor.vision import ImageExtractionError, describe_image

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API connection failed")

        config = ExtractorConfig()

        with patch(
            "content_extractor.vision.create_claude_client",
            return_value=mock_client,
        ):
            with pytest.raises(ImageExtractionError, match="API connection failed"):
                describe_image("base64data", "image/jpeg", config)

    def test_describe_image_prompt_requests_chinese(
        self, mock_vision_response_json: str
    ) -> None:
        """The prompt sent to Claude should request Chinese text transcription."""
        from content_extractor.vision import describe_image

        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._make_mock_response(
            mock_vision_response_json
        )

        config = ExtractorConfig()

        with patch(
            "content_extractor.vision.create_claude_client",
            return_value=mock_client,
        ):
            describe_image("base64data", "image/jpeg", config)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        messages = call_kwargs["messages"]
        # Find the text prompt in the message content
        prompt_text = ""
        for msg in messages:
            for block in msg.get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    prompt_text += block["text"]

        assert "Chinese" in prompt_text or "chinese" in prompt_text.lower()
        assert "JSON" in prompt_text or "json" in prompt_text.lower()

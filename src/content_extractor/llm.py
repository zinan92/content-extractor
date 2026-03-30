"""LLM client infrastructure for content-extractor.

Provides token loading from CLI Proxy API files, environment variable fallback,
expiration checking, and a client factory that configures the Anthropic SDK
with automatic rate-limit retry.

Usage:
    from content_extractor.llm import create_claude_client
    client = create_claude_client()
    # client is a configured anthropic.Anthropic instance
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from pydantic import BaseModel, ConfigDict

from content_extractor.config import ExtractorConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class LLMError(Exception):
    """Base exception for all LLM-related errors."""


class LLMConfigError(LLMError):
    """No valid token found, token disabled, or token expired."""


class LLMRateLimitError(LLMError):
    """API returned 429 — rate limit exceeded."""


class LLMAPIError(LLMError):
    """Other API failures (500, network errors, etc.)."""


# ---------------------------------------------------------------------------
# Token file model
# ---------------------------------------------------------------------------


class _CLIProxyToken(BaseModel):
    """Frozen Pydantic model for CLI Proxy API token files."""

    model_config = ConfigDict(frozen=True)

    access_token: str
    disabled: bool = False
    email: str = ""
    expired: str = ""  # ISO 8601 datetime string
    type: str = "claude"


# ---------------------------------------------------------------------------
# Token loading
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG_DIR = Path.home() / ".cli-proxy-api"


def _load_token_from_cli_proxy(
    config_dir: Path | None = None,
) -> str | None:
    """Load a valid access token from CLI Proxy API token files.

    Scans ``config_dir`` (default ``~/.cli-proxy-api``) for ``claude-*.json``
    files.  Returns the first valid (non-disabled, non-expired, type=claude)
    ``access_token``, or ``None`` if no valid token is found.
    """
    directory = config_dir if config_dir is not None else _DEFAULT_CONFIG_DIR

    if not directory.is_dir():
        return None

    for token_path in sorted(directory.glob("claude-*.json")):
        try:
            raw = json.loads(token_path.read_text())
            token = _CLIProxyToken.model_validate(raw)
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            logger.warning("Skipping invalid token file %s: %s", token_path, exc)
            continue

        if token.disabled:
            logger.debug("Skipping disabled token: %s", token_path.name)
            continue

        if token.type != "claude":
            logger.debug("Skipping non-claude token: %s", token_path.name)
            continue

        if token.expired:
            try:
                expiry = datetime.fromisoformat(token.expired)
                if expiry < datetime.now(timezone.utc):
                    logger.debug("Skipping expired token: %s", token_path.name)
                    continue
            except ValueError:
                logger.warning(
                    "Unparseable expiry in %s: %s", token_path.name, token.expired
                )
                continue

        return token.access_token

    return None


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------


def create_claude_client(
    config: ExtractorConfig | None = None,
    *,
    config_dir: Path | None = None,
) -> anthropic.Anthropic:
    """Create a configured Anthropic client.

    Token resolution order:
    1. CLI Proxy API token files (``~/.cli-proxy-api/claude-*.json``)
    2. ``ANTHROPIC_API_KEY`` environment variable

    Raises :class:`LLMConfigError` if no valid token is found or all tokens
    are expired.
    """
    token = _load_token_from_cli_proxy(config_dir)

    if token is not None:
        return anthropic.Anthropic(api_key=token, max_retries=5)

    # Check if there were expired-only tokens (no valid ones)
    # to give a specific "expired" error message.
    if _has_only_expired_tokens(config_dir):
        msg = (
            "All CLI Proxy API tokens are expired. "
            "Run the CLI Proxy API refresh process to obtain a new token."
        )
        raise LLMConfigError(msg)

    # Fallback to environment variable
    env_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_key:
        return anthropic.Anthropic(api_key=env_key, max_retries=5)

    msg = (
        "No Claude API token found. Checked:\n"
        "  1. CLI Proxy API files (~/.cli-proxy-api/claude-*.json)\n"
        "  2. ANTHROPIC_API_KEY environment variable\n"
        "Please configure one of these token sources."
    )
    raise LLMConfigError(msg)


def _has_only_expired_tokens(config_dir: Path | None = None) -> bool:
    """Return True if token files exist but ALL are expired (not disabled)."""
    directory = config_dir if config_dir is not None else _DEFAULT_CONFIG_DIR

    if not directory.is_dir():
        return False

    found_any = False
    for token_path in sorted(directory.glob("claude-*.json")):
        try:
            raw = json.loads(token_path.read_text())
            token = _CLIProxyToken.model_validate(raw)
        except (json.JSONDecodeError, ValueError, OSError):
            continue

        if token.disabled or token.type != "claude":
            continue

        found_any = True
        if token.expired:
            try:
                expiry = datetime.fromisoformat(token.expired)
                if expiry >= datetime.now(timezone.utc):
                    return False  # At least one is still valid
            except ValueError:
                continue
        else:
            return False  # No expiry means it's valid

    return found_any

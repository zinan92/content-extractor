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

    Token resolution order (with 401 fallback):
    1. CLI Proxy API token files (``~/.cli-proxy-api/claude-*.json``)
    2. ``ANTHROPIC_API_KEY`` environment variable

    If a CLI Proxy token is found but returns 401, automatically falls back
    to ANTHROPIC_API_KEY before raising.

    Raises :class:`LLMConfigError` if no valid token is found.
    """
    candidates: list[tuple[str, str]] = []

    proxy_token = _load_token_from_cli_proxy(config_dir)
    if proxy_token is not None:
        candidates.append(("cli-proxy", proxy_token))

    env_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_key:
        candidates.append(("env-ANTHROPIC_API_KEY", env_key))

    if not candidates:
        msg = (
            "No Claude API token found. Checked:\n"
            "  1. CLI Proxy API files (~/.cli-proxy-api/claude-*.json)\n"
            "  2. ANTHROPIC_API_KEY environment variable\n"
            "Please configure one of these token sources.\n"
            "  - Refresh CLI Proxy: open http://localhost:8317\n"
            "  - Or set: export ANTHROPIC_API_KEY=sk-ant-..."
        )
        raise LLMConfigError(msg)

    # Return a FallbackClient that tries candidates in order on 401
    return _FallbackClient(candidates)


class _FallbackClient:
    """Wraps multiple Anthropic clients, falling back on AuthenticationError.

    Avoids upfront ping validation — only falls back when a real call fails
    with 401. Proxies attribute access to the active underlying client.
    """

    def __init__(self, candidates: list[tuple[str, str]]) -> None:
        self._candidates = candidates
        self._active_index = 0
        self._clients = [
            (source, anthropic.Anthropic(api_key=token, max_retries=5))
            for source, token in candidates
        ]

    @property
    def messages(self) -> "_FallbackMessages":
        return _FallbackMessages(self)

    def _call_with_fallback(self, method_name: str, *args: object, **kwargs: object) -> object:
        last_error: Exception | None = None
        for i in range(self._active_index, len(self._clients)):
            source, client = self._clients[i]
            try:
                method = getattr(client.messages, method_name)
                result = method(*args, **kwargs)
                self._active_index = i  # remember which worked
                return result
            except anthropic.AuthenticationError as exc:
                logger.warning("Token from %s returned 401, trying next source", source)
                last_error = exc
                continue
        msg = (
            f"All token sources returned 401. Last error: {last_error}\n"
            "Refresh CLI Proxy: open http://localhost:8317\n"
            "Or set: export ANTHROPIC_API_KEY=sk-ant-..."
        )
        raise LLMConfigError(msg)


class _FallbackMessages:
    """Proxy for client.messages that routes through fallback logic."""

    def __init__(self, parent: _FallbackClient) -> None:
        self._parent = parent

    def create(self, **kwargs: object) -> object:
        return self._parent._call_with_fallback("create", **kwargs)


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

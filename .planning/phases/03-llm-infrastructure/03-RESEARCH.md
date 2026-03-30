# Research: Phase 3 — LLM Infrastructure

**Researched:** 2026-03-30
**Discovery Level:** 1 (Quick Verification — single known library, confirming token format)

## Token File Format (Verified on Disk)

File: `~/.cli-proxy-api/claude-zinan92@hotmail.com.json`

```json
{
  "access_token": "sk-ant-oat01-...",    // 108 chars, starts with sk-ant-oat01-
  "disabled": false,
  "email": "zinan92@hotmail.com",
  "expired": "2026-03-30T20:41:40+08:00", // ISO 8601 with timezone
  "id_token": "",
  "last_refresh": "2026-03-30T12:41:40+08:00",
  "refresh_token": "sk-ant-ort01-...",   // 108 chars
  "type": "claude"
}
```

**Key findings:**
- File pattern: `~/.cli-proxy-api/claude-*.json` (glob matches by email)
- `access_token` is the API key — pass directly to `anthropic.Anthropic(api_key=...)`
- `expired` field: ISO 8601 datetime with timezone offset — parse with `datetime.fromisoformat()`
- `disabled` flag: boolean, must check before using
- `type` field: must be `"claude"` (there are also `codex-*.json` files — skip those)
- Token refreshes automatically (external process handles `refresh_token`) — we only need to READ, not refresh

## Anthropic SDK Usage

The `anthropic` SDK (v0.86+) accepts:
```python
client = anthropic.Anthropic(api_key="sk-ant-oat01-...")
```

No `base_url` override needed — CLI Proxy API tokens are standard Anthropic API tokens from the Max plan. They work directly with `api.anthropic.com`.

### Vision API call pattern:
```python
import base64

with open("image.jpg", "rb") as f:
    image_data = base64.standard_b64encode(f.read()).decode("utf-8")

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data}},
            {"type": "text", "text": "Describe this image..."}
        ]
    }]
)
```

### Rate limit handling:
- 429 responses raise `anthropic.RateLimitError`
- SDK has built-in retry with exponential backoff (default: 2 retries)
- Can configure: `anthropic.Anthropic(max_retries=5)`
- For more control: catch `RateLimitError` and read `retry-after` header

### Token expiration:
- Expired tokens return 401 → `anthropic.AuthenticationError`
- Our code should check `expired` field BEFORE making API call to give a clear message
- If token unexpectedly fails with 401, surface: "Token may be expired. Run CLI Proxy API refresh."

## Architecture Decision

### Token loading strategy:
1. Glob `~/.cli-proxy-api/claude-*.json` — take the first non-disabled, non-expired file
2. If no valid token: check `ANTHROPIC_API_KEY` env var
3. If neither: raise `LLMConfigError` with clear message

### Client lifecycle:
- Create client once per extraction run (not per API call)
- Store in a module-level factory function: `create_claude_client(config) -> anthropic.Anthropic`
- Adapters receive the client via dependency injection (passed through `ExtractorConfig` or separate)

### Error hierarchy:
```
LLMError (base)
├── LLMConfigError      — no token, disabled, expired
├── LLMRateLimitError   — 429, includes retry-after
└── LLMAPIError         — other API failures (500, network, etc.)
```

### What NOT to build:
- Token refresh logic — external process handles this
- Async client — sync is fine for batch pipeline (no concurrent API calls needed yet)
- Streaming — not needed for structured output extraction
- Custom retry logic — SDK's built-in retry (max_retries=5) is sufficient for 429

## Dependency Addition

Add to pyproject.toml `dependencies`:
```
"anthropic>=0.86,<1",
```

## Files to Create

| File | Purpose |
|------|---------|
| `src/content_extractor/llm.py` | Token loading, client factory, error types |
| `tests/test_llm.py` | Unit tests with mocked tokens and API calls |

## Sources

- CLI Proxy API token file on disk: `~/.cli-proxy-api/claude-zinan92@hotmail.com.json`
- anthropic SDK: PyPI v0.86.0, official docs at platform.claude.com
- STACK.md research (completed in research phase)

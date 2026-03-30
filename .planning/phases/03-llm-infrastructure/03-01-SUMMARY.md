---
phase: 03-llm-infrastructure
plan: 01
subsystem: llm
tags: [anthropic, claude, cli-proxy-api, token-loading, rate-limiting]

requires:
  - phase: 01-models-config
    provides: ExtractorConfig with claude_model, claude_max_tokens, claude_temperature
provides:
  - "create_claude_client() factory returning configured anthropic.Anthropic"
  - "Token loading from ~/.cli-proxy-api/claude-*.json with expiration/disabled checks"
  - "ANTHROPIC_API_KEY env var fallback"
  - "LLMError hierarchy: LLMConfigError, LLMRateLimitError, LLMAPIError"
affects: [04-image-adapter, 05-gallery-adapter, 07-analysis-layer]

tech-stack:
  added: ["anthropic>=0.86,<1"]
  patterns: ["CLI Proxy API token loading with Pydantic validation", "SDK max_retries=5 for rate limit backoff"]

key-files:
  created: ["src/content_extractor/llm.py", "tests/test_llm.py"]
  modified: ["pyproject.toml"]

key-decisions:
  - "No base_url override needed -- CLI Proxy API tokens are standard Anthropic API tokens"
  - "Sorted glob for deterministic token selection when multiple files exist"
  - "Separate _has_only_expired_tokens() check for specific error messaging"

patterns-established:
  - "Token loading: glob + Pydantic validate + skip disabled/expired/non-claude"
  - "Client factory: CLI Proxy -> env var -> LLMConfigError with both sources listed"

requirements-completed: [LLM-01, LLM-02, LLM-03, LLM-04]

duration: 2min
completed: 2026-03-30
---

# Phase 3 Plan 1: LLM Infrastructure Summary

**Claude API client with CLI Proxy API token loading, env var fallback, expiration guard, and max_retries=5 rate-limit backoff**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-30T06:11:51Z
- **Completed:** 2026-03-30T06:14:10Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments
- Token loader reads ~/.cli-proxy-api/claude-*.json, validates with frozen Pydantic model, skips disabled/expired/non-claude tokens
- Client factory with two-tier resolution: CLI Proxy token first, ANTHROPIC_API_KEY env var fallback, clear LLMConfigError if neither available
- Error hierarchy (LLMError > LLMConfigError, LLMRateLimitError, LLMAPIError) for structured error handling downstream
- 14 tests covering all token loading edge cases and client creation paths, 82% coverage on llm.py

## Task Commits

Each task was committed atomically:

1. **Task 1: Token loader, client factory, and error types** - `8decdc0` (test: RED phase) + `11db65f` (feat: GREEN phase)

## Files Created/Modified
- `src/content_extractor/llm.py` - Token loading, client factory, error hierarchy (196 lines)
- `tests/test_llm.py` - 14 tests: token loading, env var fallback, expiration, error hierarchy
- `pyproject.toml` - Added anthropic>=0.86,<1 dependency

## Decisions Made
- No base_url override needed for CLI Proxy API tokens (they are standard Anthropic API tokens from Max plan)
- Sorted glob for deterministic token file selection when multiple files exist
- Separate `_has_only_expired_tokens()` helper for specific "expired" error messaging vs generic "no token" error

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## Known Stubs
None - all functionality is wired and tested.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `create_claude_client()` is ready for image adapter (Phase 04) and gallery adapter (Phase 05) to consume
- Error types ready for structured error handling in all LLM-dependent adapters

---
*Phase: 03-llm-infrastructure*
*Completed: 2026-03-30*

## Self-Check: PASSED

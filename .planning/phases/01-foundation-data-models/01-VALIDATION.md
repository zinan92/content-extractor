---
phase: 1
slug: foundation-data-models
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml [tool.pytest.ini_options]` — Wave 0 installs |
| **Quick run command** | `pytest tests/ -x --no-header -q` |
| **Full suite command** | `pytest tests/ --cov=content_extractor --cov-report=term-missing` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x --no-header -q`
- **After every plan wave:** Run `pytest tests/ --cov=content_extractor --cov-report=term-missing`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 0 | FOUND-01 | unit | `pytest tests/test_loader.py -x` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 0 | FOUND-03 | unit | `pytest tests/test_models.py -x` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | FOUND-02 | unit | `pytest tests/test_router.py -x` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | FOUND-04 | unit | `pytest tests/test_output.py -x` | ❌ W0 | ⬜ pending |
| 01-02-03 | 02 | 1 | FOUND-05 | unit | `pytest tests/test_output.py::test_idempotency -x` | ❌ W0 | ⬜ pending |
| 01-02-04 | 02 | 1 | QUAL-03 | unit | `pytest tests/test_output.py::test_atomic_write_failure -x` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 1 | FOUND-06 | unit | `pytest tests/test_config.py -x` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 1 | QUAL-01 | integration | `pytest tests/test_output.py::test_batch_error_isolation -x` | ❌ W0 | ⬜ pending |
| 01-03-03 | 03 | 1 | QUAL-02 | unit | `pytest tests/test_models.py::test_quality_metadata -x` | ❌ W0 | ⬜ pending |
| 01-03-04 | 03 | 1 | QUAL-04 | unit | `pytest tests/test_models.py::test_platform_metadata -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — project definition with pytest config, dependencies, src layout
- [ ] `tests/conftest.py` — shared fixtures (sample ContentItem JSON, temp dirs)
- [ ] `tests/test_loader.py` — stubs for FOUND-01
- [ ] `tests/test_models.py` — stubs for FOUND-03, QUAL-02, QUAL-04
- [ ] `tests/test_router.py` — stubs for FOUND-02
- [ ] `tests/test_output.py` — stubs for FOUND-04, FOUND-05, QUAL-01, QUAL-03
- [ ] `tests/test_config.py` — stubs for FOUND-06

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

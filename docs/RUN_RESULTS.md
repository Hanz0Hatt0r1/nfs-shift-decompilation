# SHIFT run results

## Current documentation date

2026-09-28.

## Historical baseline

The older baseline recorded 193 Python tests passed and 2 skipped. This is historical and is not the current mainline result.

## Current mainline

Commit: `9bab80af4673856f77d58bed684e7a5290ff6f03`

| CI job | Result |
|---|---|
| native | success |
| capture-producer | success |
| linux-vulkan | success |
| python | failure during collection |

Python collection stops at:

`tools/run_specialized_provider_differential.py:131`

because of an unterminated string literal.

The repository should not describe global Python CI as green until that syntax error is repaired.

## Phase 499–500 verification coverage

The new provider-bundle tests cover filename parsing, pre/post pairing, missing-pre blocking, summaries, CLI argument parsing, pre-only validation and manifest output.

## Useful local commands

```bash
python -m pytest -q
python -m pytest -q \
  tests/test_specialized_provider_capture_bundle_runtime.py \
  tests/test_verify_specialized_provider_capture_bundle.py
```

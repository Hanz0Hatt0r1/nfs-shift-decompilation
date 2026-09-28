# SHIFT run results

## Current documentation date

2026-09-28.

## Historical baseline

The older baseline recorded 193 Python tests passed and 2 skipped. This is historical and is not the current mainline result.

## Current mainline

Commit: `dffddaaa0db4290b35d3826234c2e2e7a867cb3a`

| CI job | Result |
|---|---|
| native | success |
| capture-producer | success |
| python | 1 failed, 2537 passed, 3 skipped |

The Python failure is:

`tests/test_bmw_runtime_render_contract.py::test_runtime_render_contract_builds_stage_specific_inputs`

with:

`KeyError: "byte_hashes"`

The contract already exposed the byte-hash values at `shader.byte_hashes`; the failing regression expected the same compatibility view under `shader.identity.byte_hashes`. The fix in this development branch mirrors the values into the identity object without changing the underlying `SHIFT.ShaderPermutationIdentity/1` flat fields.

## Phase 499–500 verification coverage

The provider-bundle tests cover filename parsing, pre/post pairing, missing-pre blocking, summaries, CLI argument parsing, pre-only validation and manifest output.

## Useful local commands

```bash
python -m pytest -q
python -m pytest -q \
  tests/test_specialized_provider_capture_bundle_runtime.py \
  tests/test_verify_specialized_provider_capture_bundle.py
```

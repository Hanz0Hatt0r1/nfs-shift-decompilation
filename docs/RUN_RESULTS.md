# SHIFT run results

## Current documentation date

2026-09-28.

## Historical baseline

The older baseline recorded 193 Python tests passed and 2 skipped. This is historical and is not the current mainline result.

## Current mainline

Commit: `b7a0c777a16f674f82887e3f7964e0c56bb53caa`

| CI job | Result |
|---|---|
| native | success |
| capture-producer | success |
| python | success |

The preceding mainline regression at `dffddaaa0db4290b35d3826234c2e2e7a867cb3a`
failed one Python test with `KeyError: "byte_hashes"`. PR #618 mirrored the
existing byte-hash compatibility values into `shader.identity.byte_hashes` while
preserving the flat `SHIFT.ShaderPermutationIdentity/1` fields. The post-merge
mainline run passed all three CI jobs.

## Phase 499–500 verification coverage

The provider-bundle tests cover filename parsing, pre/post pairing, missing-pre blocking, summaries, CLI argument parsing, pre-only validation and manifest output.

## Useful local commands

```bash
python -m pytest -q
python -m pytest -q \
  tests/test_specialized_provider_capture_bundle_runtime.py \
  tests/test_verify_specialized_provider_capture_bundle.py
```

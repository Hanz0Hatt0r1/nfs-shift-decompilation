# SHIFT run results

## Current documentation date

2026-09-28.

## Historical baseline

The older baseline recorded 193 Python tests passed and 2 skipped. This is historical and is not the current mainline result.

## Current mainline

Commit: `4227e279c3b2163ef531832afbcfc350d826b6b9`

| CI job | Result |
|---|---|
| native | success |
| capture-producer | success |
| python | success |

The Phase 504 merge followed a green PR validation: Python, native, capture-producer
and Vulkan smoke all passed. The post-merge mainline run also passed all four checks.

## Phase 504 verification coverage

The runtime preflight tests cover GDB Python marker detection, missing toolchain handling,
tool-version failures and successful host readiness aggregation. It also confirms that
preflight remains non-invasive: no game launch and no debugger attach are performed.

## Phase 504 verification coverage

The runtime preflight tests cover GDB Python marker detection, missing toolchain handling,
tool-version failures and successful host readiness aggregation. The merged Phase 504
mainline CI passed Python, native, capture-producer and Vulkan smoke.

## Phase 503 verification coverage

The BFF-to-pre-PhysX/provider handoff tests cover successful composition of the
vehicle physics bundle, missing SDF protection, blocker propagation and standalone
CLI behavior. The post-merge mainline run for commit `19b53820f30fd18bca84f77171c327d473bc39f5`
reported success across Python, native, capture-producer and Vulkan smoke.

## Phase 499–500 verification coverage

The provider-bundle tests cover filename parsing, pre/post pairing, missing-pre blocking, summaries, CLI argument parsing, pre-only validation and manifest output.

## Useful local commands

```bash
python -m pytest -q
python -m pytest -q \
  tests/test_specialized_provider_capture_bundle_runtime.py \
  tests/test_verify_specialized_provider_capture_bundle.py
```

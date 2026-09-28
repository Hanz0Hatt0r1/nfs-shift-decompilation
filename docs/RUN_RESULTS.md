# SHIFT run results

## Current documentation date

2026-09-28.

## Historical baseline

The older baseline recorded 193 Python tests passed and 2 skipped. This is historical and is not the current mainline result.

## Current mainline

Commit: `a8b4a2767e4ffd090e942e5cc2d74668b8e71446`

| CI job | Result |
|---|---|
| native | success |
| capture-producer | success |
| python | success |
| Vulkan smoke | success |

The Phase 511 merge followed green PR validation after one corrected test-only regression: Python, native, capture-producer
and Vulkan smoke all passed. The post-merge mainline run for commit
`b18a6969ae1851edde2120b1f033d6a9d616c152` also passed all four checks.

## Phase 509 verification coverage

The participant process/reselection tests cover consumption of `IGPhaseVehicle+0x450`,
pre-load processing via `FUN_00468ed0`, direct reselection through `DAT_00bbc600`,
the `Pakfiles/Vehicles/%s.bff` load gate, and pointer/ordinal writeback only after
successful load. The BFF-to-pre-PhysX handoff tests also verify persistence of the
Phase 509 process/reselection contract and its JSON artifact.

## Phase 511 verification coverage

The IGPhaseVehicle finalization tests cover `FUN_004d5930` container iteration and
cleanup for `+0x3ec`, `+0x3cc` and `+0x40c`, guarded `+0x160` cleanup via
`+0x3c8`, resource cleanup ordering and the normal/cockpit completion callback
ordering in `FUN_004d5f30`. The BFF-to-pre-PhysX handoff tests also verify the
finalization contract and persisted JSON artifact.

## Phase 510 verification coverage

The selector lifecycle tests cover the repeated descriptor layout, explicit
`+0x74 = 0` population in `thunk_FUN_00d36a00`, the `+0x74 == 0` eligibility
scan, `+0x8c` ordinal writeback, the bounded 16-entry batch exclusion/reset
path, and the separate `+0x1d` post-load/process byte. The handoff CLI tests
also verify stable summaries for blocked early-return paths.

## Phase 508 verification coverage

The selector-context tests cover the source-backed `thunk_FUN_00453990 → FUN_00402435 →
DAT_00bbc600` identity, selector storage at `+0x9fc`, descriptor layout, matching/linking
rules, fallback enumeration and the observed `candidate+0x74 == 0` readiness predicate.
They also assert that the selector global remains distinct from the Phase 506-507
`DAT_00c109e0` PhysicsParticipantManager global.

## Phase 507 verification coverage

The participant registry/update tests cover manager slot allocation at `+0x140` with
`0x1fa0` stride, slot count `+0x148`, the `FUN_00713f40` registration writeback,
`FUN_00713ec0` state refresh, and the direct `PhysicsParticipant.cpp` type-3 callsite.
The BFF-to-pre-PhysX handoff tests also verify that the registry/update contract is
present in the composed manifest.

## Phase 504 verification coverage

The runtime preflight tests cover GDB Python marker detection, missing toolchain handling,
tool-version failures and successful host readiness aggregation. The merged Phase 504
mainline CI passed Python, native, capture-producer and Vulkan smoke.

## Phase 505 verification coverage

The participant-gate tests cover the source-backed `FUN_00410ef0` selector, pointer/index
writeback slots, the `-1` waiting path, and the post-success transition into
`Pakfiles/Vehicles/%s.bff` loading. The BFF-to-pre-PhysX handoff tests also assert that the
participant gate is present in the composed manifest.

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

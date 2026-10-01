# Phase 636 — exact FUN_00757d20 call-site classification

Phase 635 adds a non-mutating retail observer at `FUN_00757d2c` and records
the raw caller return address for every relation-state mutation event. Phase
636 closes the static caller set behind that field.

Raw `SHIFT.exe` disassembly contains exactly five direct
`call FUN_00757d20` instructions. No heuristic caller inference is needed.

## Recovered direct callers

| Call address | Return address | Source context | Slot rule |
|---:|---:|---|---|
| `0x76EE91` | `0x76EE96` | `FUN_0076ed60` vehicle setup | fixed FL / slot 0 |
| `0x76EEA3` | `0x76EEA8` | `FUN_0076ed60` vehicle setup | fixed FR / slot 1 |
| `0x76EEB5` | `0x76EEBA` | `FUN_0076ed60` vehicle setup | fixed RL / slot 2 |
| `0x76EEC7` | `0x76EECC` | `FUN_0076ed60` vehicle setup | fixed RR / slot 3 |
| `0x79A5BC` | `0x79A5C1` | `FUN_0079a050` runtime threshold path | dynamic slot 0..3 |

The first four calls are the source-backed setup sequence already visible
around the four `component+0x504` tests. The fifth call is separate: it
appears inside the four-slot loop of `FUN_0079a050`, after its own runtime
conditions and a `FUN_0070e540(..., 6, ..., slot)` call.

Phase 636 deliberately names the fifth class only
`runtime-threshold-slot`. It does not assign a higher-level gameplay meaning
that has not been independently proven.

## Capture classification

`classify_relation_state_mutation_callsite(...)` maps the captured return
address to the exact call instruction, source function and caller class.

For the four `FUN_0076ed60` call sites it additionally checks that the
captured component slot equals the statically fixed slot. A mismatch produces:

`fixed-callsite-slot-mismatch`

and the call-site classification is not ready.

For `FUN_0079a050`, the call site is statically known but the slot is dynamic,
so any already-valid 0..3 component slot is accepted.

Unknown or missing return addresses remain in the raw Phase 635 event stream,
but their nested classification has `ready=false` and
`known_callsite=false`. The capture itself is not discarded; downstream
admission can therefore fail closed without losing unexpected retail evidence.

The Phase 635 event now exposes:

- `caller_classification`;
- `callsite_ready`.

The nested format is:

`SHIFT.ConstraintRelationStateMutationCallsite/1`.

## Why both caller families matter

The four setup calls prove that relation bit0 mutation can occur during vehicle
setup. The fifth direct caller proves that treating all
`FUN_00757d2c` mutations as setup-only would be incorrect.

This is why Phase 636 classifies the raw caller address before any native
scheduler decision. Runtime timing still comes from the Phase 635 shared
`runtime_event_sequence` rather than from static source guesses.

## Regression coverage

The Python runtime-probe regression verifies:

- all five exact return addresses;
- all five exact call addresses;
- fixed slot 0/1/2/3 identity for the four setup calls;
- mismatch rejection for a fixed setup caller;
- all four dynamic slots through the `FUN_0079a050` call site;
- unknown caller retention with `callsite_ready=false`;
- propagation of known classification into the Phase 635 event payload.

## Deliberate boundary

Phase 636 classifies provenance; it does not connect either caller family to
`shift_runtime`.

The next safe step is to correlate an authentic Phase 635 event stream using
this exact caller classification plus the existing frame/reset/solve timeline.
Only then should a native admission artifact decide whether a captured event
belongs to construction/setup state, a runtime mutation path, or neither.

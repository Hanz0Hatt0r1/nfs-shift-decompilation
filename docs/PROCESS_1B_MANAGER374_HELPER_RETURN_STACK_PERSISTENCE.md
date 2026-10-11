# Process 1B — helper-returned `+0x374` target stack persistence

## Blocker

`SHIFT.P1B.Manager374HelperReturnedMaterializedTargetProbe/1` bounds direct local helpers that return `entry-argument + 0x374` in `EAX` and immediate caller-side GPR writes through that returned address. Its caller window intentionally does not preserve a returned target through stack memory.

A caller can therefore still:

```text
call helper                  ; EAX = receiver+0x374
mov  [ebp-0x10],eax          ; spill returned target
...
mov  edi,[ebp-0x10]          ; reload
mov  [edi],ecx               ; later write
```

or use an ESP-relative slot whose physical displacement changes as `ESP` moves. This probe bounds only that caller-side stack spill/reload transport.

## Tool and contract

```text
tools/ghidra/analyze_p1b_manager374_helper_return_stack_persistence.py
SHIFT.P1B.Manager374HelperReturnedTargetStackPersistenceProbe/1
```

The probe reuses the helper qualification semantics from:

```text
SHIFT.P1B.Manager374HelperReturnedMaterializedTargetProbe/1
```

and remains SHA-locked to PC retail 1.02:

```text
eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

## Caller transport

At a qualifying helper return the exact returned target starts in `EAX`. For at most 64 following instructions the probe tracks:

- exact GPR `mov` copies;
- EBP-relative spill/reload slots keyed by exact textual displacement;
- ESP-relative spill/reload slots keyed by normalized logical displacement;
- `push` / `pop` round trips;
- immediate `sub/add esp,imm`;
- exact `lea esp,[esp+/-imm]`.

The normalized ESP key is:

```text
textual displacement - cumulative ESP delta
```

so, for example, a spill at `[esp+0x10]` after `sub esp,0x20` and a reload from `[esp]` after `add esp,0x10` refer to the same logical `esp-0x10` slot.

## New candidate rule

A write is new for this probe only if the returned target has actually passed through a stack reload. Thus:

```text
call helper
mov [eax],ecx
```

is recorded as a direct-no-reload write and remains owned by the immediate helper-return probe, while:

```text
call helper
mov [ebp-0x10],eax
mov edi,[ebp-0x10]
mov [edi],ecx
```

is a `stack_reload_derived_write_candidate`.

Only explicit zero-displacement write/RMW through the recovered alias counts as a write candidate. Stack-slot overwrites invalidate the saved alias before any later reload.

## Non-stack persistence

A store of the returned target into non-stack memory is inventoried as an open escape:

```text
mov [edi+0x20],eax
```

The probe deliberately does not follow that memory carrier. This avoids converting a bounded stack proof into an unsound generic heap/global alias claim.

## Fail-closed boundaries

The post-return scan stops at:

- the next call;
- branch/jump/return/trap;
- dynamic or unsupported `ESP` mutation;
- 64 instructions.

Partial/implicit GPR clobbers kill exact returned-target provenance using the same conservative semantics as the upstream helper-return probe.

EBP-relative keys are only syntactic fixed-base persistence. A positive EBP-derived candidate still requires later classification that the base is a relevant caller frame/storage context; this probe does not infer object identity from EBP syntax.

## Outside scope

Still open after this probe:

- non-stack persistence of returned targets;
- returned target forwarded into another helper call;
- indirect/external helper returns;
- CFG-carried returned-target aliases;
- unrelated opaque target synthesis;
- runtime patching/generated code;
- external process mutation.

## Gate policy

The only scoped acquisition gate promoted by the analyzer itself is:

```text
helper_returned_target_stack_persistence_subset_scanned = true
```

These remain false without authoritative retail results and candidate adjudication:

```text
helper_returned_target_stack_reload_write_candidates_classified
helper_returned_target_non_stack_persistence_complete
helper_returned_materialized_address_surface_complete
global_helper_non_vtable_indirect_setter_surface_complete
external_or_unknown_origin_outer_alias_surface_complete
independent_unnamed_opaque_or_external_runtime_root_synthesis_complete
unrecognized_runtime_transform_root_origin_surface_complete
global_manager_root_origin_surface_complete
manager_374_join_to_hdvehicle_4330_complete
last_literal_0x004b86cf_rejected
p1_3_control_producer_complete
```

External provider count remains `7`.

## Tests

```bash
python3 -m pytest -q \
  tests/test_process1b_manager374_helper_return_stack_persistence.py
```

Regressions cover:

- EBP spill/reload/write;
- ESP-normalized spill/reload across stack movement;
- push/pop round trip;
- overwrite invalidation;
- direct-no-reload write de-duplication;
- non-stack escape inventory;
- dynamic ESP failure;
- call-boundary stop;
- GPR copy before spill;
- fail-closed semantic gates.

## Next step

Run on the authoritative retail image. Classify every reload-derived write candidate and every non-stack persistence escape. If the stack frontier is empty, close only this returned-target stack-persistence class. A positive non-stack escape should drive the next narrowly scoped carrier proof rather than reopening already closed direct/materialized classes.

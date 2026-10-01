# Phase 635 — FUN_0076ed60 vehicle relation-state initialization

Phase 634 closes the named four-slot dispatcher for `FUN_00757d2c` but
deliberately leaves the caller event unresolved. Phase 635 closes that static
call-site provenance from the retail executable without inventing fixed-step
scheduling.

The recovered mutation is an initialization/setup path, not a 60 Hz solver
event.

## Retail call site

Raw x86 at `FUN_0076ed60` first updates all four component blocks through
`FUN_00753020`:

| Slot | Component | Config record |
|---:|---:|---:|
| 0 / FL | `vehicle+0x400` | `param+0x88` |
| 1 / FR | `vehicle+0xE80` | `param+0x128` |
| 2 / RL | `vehicle+0x1900` | `param+0x1C8` |
| 3 / RR | `vehicle+0x2380` | `param+0x268` |

`FUN_00753020` copies the source record boolean at `+0x98` into the
component byte at `+0x504`.

Therefore the four source booleans live at:

- FL: `param+0x120`;
- FR: `param+0x1C0`;
- RL: `param+0x260`;
- RR: `param+0x300`.

Immediately after the four component updates, raw instructions at
`0x76EE84..0x76EEC7` test `vehicle+0x904`, `+0x1384`, `+0x1E04` and
`+0x2884` in FL → FR → RL → RR order. Each nonzero byte causes an exact
`FUN_00757d20(slot)` call with stack arguments 0, 1, 2 or 3 respectively.

This corrects the misleading Ghidra rendering that displayed the vehicle
pointer as the argument to `FUN_00757d20`; the raw call sites push the slot
index and keep the vehicle in `ECX`.

## Normalized native boundary

Phase 635 adds:

`apply_fun_0076ed60_vehicle_relation_state_initialization(...)`

The input contains only the two source-backed per-slot facts needed by the
already recovered dispatcher:

- `mutation_enabled[slot]`: the copied `component+0x504` setup flag;
- `spindle_body_present[slot]`: the `component+0x424` pointer-presence
  branch already modeled in Phase 634.

The function walks slots 0..3 in retail order, skips disabled slots, and chains
each enabled slot through
`dispatch_fun_00757d2c_vehicle_slot_relation_state_mutation`. Relation state
is therefore accumulated exactly across multiple enabled slots.

The result records the dispatched mask/order, branch counts, matched relation
counts and newly-set relation counts while preserving the Phase 633 set-only
semantics.

## Caller provenance

The decompiled parent path shows `FUN_0074ddc3` invoking
`FUN_0076ed60(&DAT_00c13700, ...)` in switch case 3 when the relevant
participant selector field is zero. The same function contains vehicle
spawn/setup handling and later participant setup calls.

Phase 635 therefore classifies the recovered relation mutation as vehicle
initialization/setup provenance. It does **not** classify it as a per-frame
physics event.

## Regression coverage

`shift_runtime_constraint_relation_state_initialization_check` proves:

- config record base `0x88`, stride `0xA0`, flag offset `0x98`;
- exact source flag offsets `0x120/0x1C0/0x260/0x300`;
- FL → FR → RL → RR iteration order;
- disabled slot suppression;
- chained pair/BAR mutations over one relation-state frame;
- preservation of pre-existing set bits;
- no fixed-step scheduler integration;
- no persistent native participant-state integration yet.

Linux Vulkan CI runs the checker independently of `shift_runtime`.

## Deliberate boundary

The event provenance gap from Phase 634 is now closed: the retail caller is
`FUN_0076ed60` and the trigger is the per-component setup/configuration flag
copied by `FUN_00753020`.

The next safe integration boundary is transporting these four setup flags and
the corresponding spindle-pointer presence into the native participant
construction path, then applying the resulting relation state before the first
admitted solver frame. Phase 635 does not synthesize those runtime inputs and
does not mutate the existing fixed-step scheduler.

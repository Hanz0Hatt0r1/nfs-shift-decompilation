# Phase 633 — source-backed relation state bit0 mutation

Phase 632 independently reconstructs the `FUN_007b3f40` reset selection from
prepared relation-state bit0 evidence. The remaining question is where that
bit is produced.

Phase 633 ports the source-backed mutation semantics from `FUN_00757d2c`
without assigning an unresolved scheduler event or vehicle-lifecycle meaning.

## Temporal reuse of relation +0x70

The relation field at `+0x70` has two distinct lifetimes.

During solver setup, `FUN_007b1b60` writes the scalar base into `+0x70`
for JOINT, HINGE and BAR records. `FUN_007b3820` consumes that temporary
base while allocating/linking BODY-owned endpoint samples and then clears
`+0x70` to zero for every relation.

Later runtime code treats the same field as state flags. Phase 632 already
ports the `FUN_007b3f40` bit0 consumer.

This separation matters: the runtime bit is not the setup scalar-base value.

## Recovered writer: FUN_00757d2c

The audited `SHIFT.exe.c` path contains a direct set-only mutation:

```text
relation+0x70 = relation+0x70 | 1
```

for all three relation types.

The function has two source branches.

### Pair branch

When the local branch selector is zero, retail scans JOINT and then HINGE
relations. Bit0 is set when the relation endpoints match an unordered pair of
BODY pointers:

```text
(pos == A && neg == B) || (neg == A && pos == B)
```

The reconstructed neutral API therefore takes two CSRF BODY indices and
performs the same unordered identity match.

### BAR endpoint branch

When the local branch selector is nonzero, retail scans BAR relations and sets
bit0 when either endpoint pointer equals the selected BODY pointer:

```text
pos == A || neg == A
```

The neutral API takes one CSRF BODY index and applies the same endpoint match.

## Native API

Phase 633 adds:

```cpp
apply_fun_00757d2c_pair_relation_state_mutation(...)
apply_fun_00757d2c_bar_endpoint_state_mutation(...)
```

Both return a copied `PreparedConstraintRelationResetFrame` plus matched and
newly-set relation counts.

The implementation is intentionally set-only:

- existing bit0 values are preserved;
- matching zero bits become one;
- no bit is cleared;
- JOINT/HINGE pair mutation does not touch BAR state;
- BAR endpoint mutation does not touch JOINT/HINGE state.

CSRF BODY indices replace raw pointer equality only as the already-established
neutral identity domain from Phase 630.

## Fail-closed checks

The native implementation rejects:

- CRRF/CSRF relation-count mismatches;
- relation endpoints outside the CSRF BODY domain;
- mutation BODY indices outside that domain;
- normalized state values other than 0 or 1.

It does not require a relation to match. A retail event can legitimately leave
the relation-state arrays unchanged.

## Regression coverage

`shift_runtime_constraint_relation_state_mutation_check` covers:

- unordered JOINT/HINGE pair matching;
- reversed-pair equivalence;
- unmatched pair no-op;
- BAR endpoint matching across multiple relations;
- a BAR whose two endpoints are the same BODY;
- preservation of pre-existing set bits;
- state-cardinality rejection;
- endpoint-domain rejection;
- event BODY-domain rejection.

Linux Vulkan CI runs the native checker and requires it to report:

```text
source_function = FUN_00757d2c
mutation_set_only = true
scheduler_integrated = false
event_timing_assigned = false
```

## Component-slot trampoline provenance

Raw `SHIFT.exe` disassembly closes the decompiler's implicit-`EAX` ambiguity.

`FUN_00757d20` is a small wrapper that loads its stack argument into `EAX`
and jumps to `FUN_00469736`. The thunk at `0x469736` executes:

```text
imul eax, eax, 0xA80
jmp  FUN_00757d2c
```

`FUN_00757d2c` then addresses the repeated component block as:

```text
vehicle + 0x400 + component_index * 0xA80
```

A recovered load/restore caller, `FUN_0076ed60`, passes literal indices
0, 1, 2 and 3 for the four repeated blocks at vehicle offsets
`+0x400`, `+0xE80`, `+0x1900` and `+0x2380`.

A second audited call site around `0x79A5BC` passes the current four-slot loop
index to the global vehicle object at `0xC13700`.

Therefore the component-slot index itself is proven. What remains unresolved
is the semantic name of the event at every call site, the exact BODY identity
meaning of component fields `+0x420/+0x424` for all runtime states, and the
correct scheduler/frame timing for the Linux path.

## Deliberate boundary

Phase 633 does not call the mutation kernel from `shift_runtime`.

The source mutation and the 0..3 component-slot trampoline are statically
recovered, but scheduling a prepared mutation still requires a proven
component-field BODY mapping and event timing. Phase 633 therefore reconstructs
the state transition itself while keeping dispatch evidence-gated.

The next safe step is to normalize the four component slots and their
`+0x420/+0x424` BODY references into an evidence packet, or obtain a runtime
observation tying those fields and the triggering event to a concrete frame,
before connecting mutation to the fixed-step CRRF path.

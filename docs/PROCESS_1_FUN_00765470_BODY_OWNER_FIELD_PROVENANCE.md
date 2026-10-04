# Process 1 — retail `FUN_00765470` BODY-owner field provenance

## Playable-slice blocker removed

The first `FUN_00765470` receiver analyzer asked whether the receiver passed to
`FUN_007b2270` at `0x0076582a` was numerically the same pointer as the
`FUN_00765470` entry `ECX`.

The targeted retail Ghidra export is now available. It proves that this equality
is false and exposes the actual object-layout edge instead:

```text
FUN_00765470 entry ECX
  -> 0x0076548a: MOV ESI,ECX
  -> ESI preserved to the BODY-loop call site
  -> 0x00765824: MOV ECX,dword ptr [ESI + 0x339c]
  -> 0x0076582a: CALL FUN_007b2270
```

Therefore the remaining BODY-owner relation is not:

```text
vehicle base == BODY-array owner
```

It is:

```text
global vehicle base
  -> pointer field +0x339c
  -> FUN_007b2270 receiver / BODY-array owner domain
```

This correction removes the retail BODY-owner identity blocker without inventing
pointer equality, class names, scheduling, or a new runtime capture.

## Retail input result

The user-supplied targeted analyzer result covers all 247 instructions reachable
inside `FUN_00765470` and reports exactly one receiver origin at the body-loop
call:

```text
memory:dword ptr [esi + 0x339c]
```

The old report correctly keeps
`receiver_equals_half_step_entry_ECX_on_all_reachable_paths=false`; its
`receiver_provenance_ambiguous=true` reflects that the original analyzer treated
all memory-derived receivers as unresolved for the stricter equality question.
It is not evidence for multiple machine origins.

The companion instruction export supplies the missing base-register proof:

```text
0x0076548a  8b f1              MOV ESI,ECX
0x00765824  8b 8e 9c 33 00 00  MOV ECX,dword ptr [ESI + 0x339c]
0x0076582a                      CALL FUN_007b2270
```

The promotion additionally checks that no second syntactic writer replaces ESI
between the entry copy and the owner load. Calls do not invalidate ESI because
the existing IA-32 provenance model treats ESI as callee-saved and only
EAX/ECX/EDX as caller-saved.

## New proof contract

```text
SHIFT.Fun00765470BodyOwnerFieldProvenance/1
```

Tool:

```text
tools/ghidra/promote_fun_00765470_body_owner_field.py
```

Inputs:

```text
SHIFT.Fun00765470BodyOwnerReceiverProvenance/1
SHIFT.GhidraFunctionInstructions/2 for FUN_00765470
```

A positive proof requires all of the following:

1. the old report has one exact receiver origin,
   `memory:dword ptr [esi + 0x339c]`;
2. all exported function instructions are reachable according to that report;
3. `0x0076548a` is exact `MOV ESI,ECX`, bytes `8bf1`;
4. no later first-operand writer replaces ESI before `0x00765824`;
5. `0x00765824` is exact `MOV ECX,dword ptr [ESI + 0x339c]`, bytes
   `8b8e9c330000`;
6. that load falls through directly to `0x0076582a`;
7. `0x0076582a` directly targets `FUN_007b2270`.

The output explicitly preserves:

```text
entry_receiver_equals_call_receiver_pointer = false
BODY_array_owner_pointer_field_offset        = 0x339c
entry_receiver_to_BODY_owner_pointer_field_edge_proven = true
```

## Global vehicle composition correction

The existing `SHIFT.GlobalVehicleBodyOwnerIdentity/1` remains the public Process
1 -> Process 2 handoff. No second selector ABI is introduced.

New promotion tool:

```text
tools/ghidra/promote_global_vehicle_body_owner_identity.py
```

It consumes the previous fail-closed composed identity plus the proven field edge
and publishes:

```text
global vehicle address = 0x00c13700
BODY owner pointer      = *(0x00c13700 + 0x339c)
BMW chassis BODY        = body, index 0
```

while retaining:

```text
BODY_array_owner_is_global_vehicle_base = false
update-child equality required          = false
```

Only the semantic continuity/readiness flags become positive:

```text
outer_receiver_to_BODY_owner_continuity_proven = true
vehicle_BODY_selection_ready                    = true
selected_BODY_index                             = 0
phase698_positive_selection_admissible          = true
phase700_runtime_handoff_admissible             = true
phase703_gate_rewrite_ready                     = true
```

This matches the existing Phase 703 consumer, which reads the composed readiness
and BODY index and does not require owner/base pointer equality.

Committed retail evidence:

```text
evidence/fun_00765470_body_owner_field_retail.json
evidence/global_vehicle_body_owner_identity_retail.json
```

## Process 2 / 3 consequence

Current `main` already contains:

- Phase 703: composed Process 1 BODY-owner identity -> Phase 698/700 BODY0 pose;
- Phase 704/705: BODY0/VHF world-matrix composition and runtime handoff gates;
- Phase 706: persistent BMW vehicle world-transform state;
- Phase 646: renderer-side per-step vehicle transform transport core.

This proof removes the first of the two Phase 706 upstream blockers. The remaining
semantic blocker for a retail dynamic matrix is now the separately tracked
`SHIFT.BMWBody0BindFrameProof/1` witness (`M_BODY0_bind`). Process 1 PR #1200 has
already reduced that problem to a finite construction/writer caller worklist.

## Preserved negative claims

This proof does not establish:

- BODY owner pointer == global vehicle pointer;
- an OO class name for the object at `+0x339c`;
- `FUN_007b2270` class identity;
- BODY0 bind matrix;
- fixed-step scheduling ownership;
- camera-follow convention;
- live Vulkan buffer mutation;
- original-game execution;
- a new runtime capture.

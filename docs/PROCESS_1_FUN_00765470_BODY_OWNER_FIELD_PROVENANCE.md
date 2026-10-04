# Process 1 — retail `FUN_00765470` BODY-owner field provenance

## Playable-slice blocker removed

The original `FUN_00765470` analyzer asked whether the receiver passed to
`FUN_007b2270` at `0x0076582a` was the same pointer as the function-entry `ECX`.
The targeted retail Ghidra export now proves that equality false and exposes the
actual object-layout edge:

```text
FUN_00765470 entry ECX
  -> 0x0076548a: MOV ESI,ECX
  -> ESI preserved
  -> 0x00765824: MOV ECX,dword ptr [ESI + 0x339c]
  -> 0x0076582a: CALL FUN_007b2270
```

The resulting relation is therefore:

```text
global vehicle base 0x00c13700
  -> pointer field +0x339c
  -> FUN_007b2270 receiver / BODY-array owner domain
  -> proven BMW chassis BODY index 0
```

It is **not** `vehicle base == BODY-array owner`.

No original `SHIFT.exe` execution and no new runtime capture are used.

## Retail evidence

The user-supplied `SHIFT.Fun00765470BodyOwnerReceiverProvenance/1` report covers
all 247 function instructions and exposes one receiver origin before the
BODY-loop call:

```text
memory:dword ptr [esi + 0x339c]
```

The companion `SHIFT.GhidraFunctionInstructions/2` row freezes the exact machine
anchors:

```text
0x0076548a  8b f1              MOV ESI,ECX
0x00765824  8b 8e 9c 33 00 00  MOV ECX,dword ptr [ESI + 0x339c]
0x0076582a                      CALL FUN_007b2270
```

The promotion checks both explicit machine writers and structured p-code writes
to full-width ESI (`register` space offset `0x18`, size 4) between the entry copy
and the owner load. Both must contain only `0x0076548a`. Missing structured
p-code fails closed.

## New local proof

Tool:

```text
tools/ghidra/promote_fun_00765470_body_owner_field.py
```

Contract:

```text
SHIFT.Fun00765470BodyOwnerFieldProvenance/1
```

The positive handoff freezes:

```text
entry_receiver_equals_call_receiver_pointer = false
BODY_array_owner_pointer_field_offset        = 0x339c
entry_receiver_to_BODY_owner_pointer_field_edge_proven = true
```

The local artifact still cannot admit Phase 698 by itself.

Committed retail evidence:

```text
evidence/fun_00765470_body_owner_field_retail.json
```

## Existing global composition corrected

`tools/ghidra/build_global_vehicle_body_owner_identity.py` continues to emit the
existing public contract:

```text
SHIFT.GlobalVehicleBodyOwnerIdentity/1
```

For compatibility it still accepts the old direct-receiver contract. It now also
accepts the field-provenance contract and distinguishes the two cases explicitly.
The retail field path emits:

```text
half_step_entry_ECX_to_BODY_array_owner_ECX_continuity_proven   = false
half_step_entry_ECX_to_BODY_array_owner_field_continuity_proven = true
BODY_array_owner_is_global_vehicle_base                         = false
BODY_array_owner_pointer_loaded_from_global_vehicle_base         = true
BODY_array_owner_pointer_field_offset                            = 0x339c
global_vehicle_BODY_owner_identity_ready                        = true
vehicle_BODY_selection_ready                                    = true
selected_BODY_index                                             = 0
phase698_positive_selection_admissible                          = true
phase700_runtime_handoff_admissible                             = true
```

Committed composed retail evidence:

```text
evidence/global_vehicle_body_owner_identity_retail.json
```

## Cross-process consequence

Current Process 2 already has Phase 698/700 BODY-pose selection/transport and
Phase 704/705/706 vehicle-world-transform infrastructure. This proof removes the
BODY-owner identity blocker in front of those paths.

The remaining semantic transform blocker is the separately tracked
`SHIFT.BMWBody0BindFrameProof/1`: the exact `M_BODY0_bind` construction/writer
witness. Process 1 PR #1200 has already reduced that problem to a finite static
caller/worklist boundary.

Process 3 Phase 646 already provides per-step vehicle transform transport. Thus
renderer transport is not reopened by this proof.

## Preserved negative claims

This phase does not establish:

- BODY-owner pointer == global vehicle pointer;
- an OO class name for the object at `+0x339c`;
- `FUN_007b2270` class identity;
- the writer/initializer of vehicle field `+0x339c`;
- `M_BODY0_bind`;
- fixed-step scheduling ownership;
- camera-follow convention;
- live Vulkan buffer mutation;
- original-game execution or a new runtime capture.

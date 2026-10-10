# Process 1A / P1.3A — direct exact-HDVehicle-root persistence handoff

## Scope

P1.3A still has slot0 `HDVehicle+0x938` and slot1 `HDVehicle+0x13b8` open after the shallow write/copy classes and first deeper direct tranche. The next stored/escaped-alias question is narrower than writer semantics: can a machine-proven **exact HDVehicle root pointer** be directly stored, pushed, or copied into a new persistent GPR alias inside the known carrier set?

Merged P1D contract `SHIFT.P1D.Slot3SixteenCarrierDirectRootPersistence/1` already answers that machine question over 16 exact-root carriers. This P1A handoff consumes only the **11 carriers whose exact root is HDVehicle itself** and deliberately excludes the five exact-wheel-root carriers. Ownership of the upstream machine proof remains with P1D.

## Consumed carrier subset

```text
FUN_00758810
FUN_00758b50
FUN_00758fc0
FUN_00763570
FUN_00765c40
FUN_00766510
FUN_007675f0
FUN_007682c0
FUN_00769ef0
FUN_0076d100
FUN_00770e80
```

The excluded wheel-root carriers are `FUN_00752fc0`, `FUN_00755950`, `FUN_00755a60`, `FUN_00755f80`, and `FUN_00760b50`; those remain part of the separate wheel/derived alias frontier.

## Result

Across the upstream 16-carrier machine surface there are only two direct exact-root memory stores, both inside the 11-function HDVehicle subset and both stack-local preservation:

- `0x00758b9b`: `FUN_00758b50`, `[ebp-0x1c] = EDI`;
- `0x00763590`: `FUN_00763570`, `[ebp-0x3c] = EDI`.

There are zero non-stack/unknown direct exact-root stores, zero exact-root pushes, and all 23 immediate root-register copies target only `ECX` as receiver reload traffic. No new persistent GPR alias class appears in this bounded direct-value surface.

This result is pointer-persistence evidence. It does **not** prove the absence of writes to slot0/slot1 fields by unrelated or derived receivers.

## Gate

```text
P1A direct exact-HDVehicle-root persistence subset complete = true
direct exact-root non-stack store found                     = false
direct exact-root push found                                = false
new direct exact-root GPR alias found                       = false

derived wheel/interior alias storage ruled out              = false
runtime-generated/copied pointer stores ruled out           = false
callee-created aliases ruled out                            = false
callbacks / indirect entry ruled out                        = false
stored-or-escaped aliases ruled out                         = false

slot0 complete                                              = false
slot1 complete                                              = false
P1.3 complete                                               = false
provider count                                              = 7
```

## Reproduce

```bash
python3 tools/ghidra/build_p1a_slot01_direct_root_persistence_handoff.py \
  --upstream evidence/p1d_slot3_16carrier_direct_root_persistence.json \
  --output evidence/p1a_p13a_slot01_direct_hdvehicle_root_persistence_handoff.json
```

The builder validates the upstream contract format, PC retail SHA-256, exact 16-carrier set, direct-store/push/register-copy counts, and fail-closed premises before producing the P1A handoff.

## Next step

Close the exact wheel-root persistence/materialization subset for slot0/slot1, then trace derived/interior and runtime-generated pointer aliases before changing the global stored-or-escaped-alias gate.

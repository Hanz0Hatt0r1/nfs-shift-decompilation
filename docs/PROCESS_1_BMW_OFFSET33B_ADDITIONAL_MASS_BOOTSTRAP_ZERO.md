# Process 1 — BMW `offset33b` additional-mass bootstrap-zero proof

## Playable-slice blocker reduced

The symbolic BMW BODY0-local -> outer Vehicle-root relation is already proven,
and `SHIFT.BMWOffset33bStoreProvenance/1` bounds the exact producer stores in
`FUN_0076b280`. Numeric `offset33b` still depends on several resource/init roots.
One of those roots was previously anonymous: the scalar read from the current
PhysicsParticipant at `+0xba0` and used as an additional mass contribution.

This proof closes that one root for the first/reinitialized vehicle bootstrap.

Contract:

```text
SHIFT.BMWOffset33bAdditionalMassBootstrapZero/1
```

Analyzer:

```text
tools/ghidra/analyze_bmw_offset33b_additional_mass_bootstrap_zero.py
```

## Proven storage alias

The outer `Vehicle` is embedded at `PhysicsParticipant+0x340`, therefore:

```text
participant+0xba0
== (participant+0x340)+0x860
== Vehicle+0x860
```

This is the scalar consumed by the source-backed `FUN_0076b280` offset33b
producer as the additional participant-mass term.

## Constructor/reset proof

PhysicsParticipantManager allocates participant records with stride `0x1fa0`
and constructs them through `FUN_00714360`.

The exact retail constructor calls:

```text
0x007143c9 -> FUN_00552dd0
```

with the recovered argument:

```text
participant + 0xb00
```

`FUN_00552dd0` has exact retail fingerprint
`cf7b038743bf9c6e0d8554f2c4026e3197c668ef8dc1bfbdf4711b5d38670d02`.
Its reviewed body clears dwords across the first recovered zero range
`subobject+[0x24,0x124)`. The target scalar is `subobject+0xa0`, so:

```text
(participant+0xb00)+0xa0 = participant+0xba0 = 0x00000000 = +0.0f
```

Reused slots go through `FUN_007126a0`, which calls the same zero helper at
`0x007126db` with the same `participant+0xb00` subobject. The proof therefore
covers both fresh construction and participant-slot reinitialization.

## Preservation to `Vehicle::InitVehicle`

The proof freezes the exact source-backed bootstrap path:

```text
FUN_0074e1a0
  -> VDF/GetCarPhysicsDetails pre-init
  -> FUN_0074ddb0
  -> FUN_0041cbd6
  -> MWL::Core::PhysicsParticipant::Restart (FUN_0074ddc3)
       0x0074ddc3 -> FUN_0074d640
       0x0074dddb -> FUN_00797fd0
       0x0074de12 -> MWL::Core::Vehicle::InitVehicle (FUN_00798df0)
```

`FUN_0074e1a0`, `FUN_0074d640`, and `FUN_00797fd0` were reviewed against the
retail decompiler output and do not write the target storage before
`Vehicle::InitVehicle`. The contract does not infer this from names: their exact
retail function fingerprints and the exact direct-call instruction addresses are
validated fail-closed.

## Usage

```bash
python3 tools/ghidra/analyze_bmw_offset33b_additional_mass_bootstrap_zero.py \
  out/shift_ghidra_database \
  --json-out out/bmw_offset33b_additional_mass_bootstrap_zero.json
```

No new Ghidra analysis, game execution, Wine run, or runtime capture is needed.
The input is the already exported retail evidence:

```text
binary.json
functions.jsonl
callgraph.jsonl
strings_xrefs.jsonl
```

## Exact result and deliberate non-claims

For the first/reinitialized bootstrap path the contract proves:

```text
offset33b additional participant mass root = +0.0f
```

and exposes:

```text
offset33b_additional_mass_bootstrap_zero_ready = true
offset33b_additional_mass_term_can_be_elided_for_first_bootstrap = true
```

It deliberately keeps these gates false:

```text
BMW_numeric_offset33b_ready                       = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                      = false
vehicle_world_transform_ready                     = false
```

The remaining numeric work is the bounded HDV/VDF/SDF/tire-resource evaluation
already exposed by the `FUN_0076b280` store/value-root frontier. This contract
removes one root from that evaluator; it does not pretend the other resource
values are already known.

# Process 1D — `FUN_00765c40` exact-HDVehicle carrier handoff

P1D's exact-carrier escape inventories were built around 15 functions. That set omitted `FUN_00765c40`, even though merged Process 1/P1A evidence already proves this function operates on the selected `HDVehicle` runtime state and its complete object-side-effect surface is closed.

This handoff consumes, without re-owning, four merged PC-retail contracts:

- `SHIFT.Fun00765c40ResidualOwnershipFrontier/1`;
- `SHIFT.Fun00765c40DirectMachineWriteSurface/1`;
- `SHIFT.Fun00752fa0WheelStateMachineProof/1`;
- `SHIFT.Fun007584f0MachineSideEffectProof/1`.

The lifecycle edge is the direct `FUN_0076d100 @ 0x0076d12b -> FUN_00765c40` pass call. The upstream ownership contract states that all direct HDVehicle-relative writes and all callee-mediated object side effects are classified.

## Slot3 adjudication

Selected slot3 is the qword lane:

```text
HDVehicle+0x28b8 .. HDVehicle+0x28bf
```

The complete direct machine-write surface contains no overlapping lane. Important high-address wheel-loop destinations include `+0x29f0`, `+0x2b20/+0x2b28`, and other already enumerated state arrays, all disjoint from `+0x28b8..+0x28bf`.

The two persistent callee-mediated HDVehicle write proofs are also disjoint:

- `FUN_00752fa0`: slot3-derived destinations `+0x2d78` dword and `+0x2d80` qword;
- `FUN_007584f0`: persistent HDVehicle writes `+0x0d40`, `+0x17c0`, `+0x3420`.

Other callees are already classified as explicit-output-buffer/read-only transforms or separate BODY accumulator operations. Upstream reports no unclassified callees.

Therefore `FUN_00765c40` is added to the P1D exact carrier set as carrier 16, and its already-proven persistent write surface does not contain the selected slot3 writer.

## Reproduce

```bash
python3 tools/ghidra/build_p1d_slot3_fun00765c40_carrier_handoff.py \
  evidence/fun_00765c40_residual_ownership_frontier.json \
  evidence/fun_00765c40_direct_machine_write_surface.json \
  evidence/fun_00752fa0_wheel_state_machine_proof.json \
  evidence/fun_007584f0_machine_side_effect_proof.json \
  --output out/p1d_slot3_fun00765c40_carrier_handoff.json
```

## Fail-closed boundary

This handoff does not silently extend the previous 15-carrier `SHIFT.exe.c` storage replay to `FUN_00765c40`. A 16-carrier source-storage replay remains separate work. Runtime/generated pointer stores, callee-created aliases and unresolved indirect-entry mechanisms also remain open.

Accordingly slot3 writer provenance, P1.3D and aggregate P1.3 remain false; external provider count remains 7.

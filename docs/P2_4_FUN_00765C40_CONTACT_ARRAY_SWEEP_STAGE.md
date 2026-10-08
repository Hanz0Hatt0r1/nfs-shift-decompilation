# Process 2 P2.4 — `FUN_00765c40` contact-array sweep

## BLOCKER

P2.4 continues internalizing the complete residual `FUN_00765c40` pass in retail order. The merged wheel-pair stage now hands off into the source-visible 12-slot contact-array sweep.

## INPUT

This slice consumes:

- `SHIFT.Fun00765c40ResidualPassContract/1`;
- `SHIFT.Fun00765c40DirectMachineWriteSurface/1`;
- PC-retail `SHIFT.exe` SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

The machine-backed surface proves two arrays written by the sweep:

```text
12 dword slots: +0x35c8 .. +0x35f4, stride 0x04, site 0x00766120
12 qword slots: +0x35f8 .. +0x3650, stride 0x08, site 0x0076618b
```

## OUTPUT

Adds `SHIFT.Fun00765c40ContactArraySweepStage/1`.

Native code owns the exact 24 destinations and their widths. The source-computed dword and qword payloads remain explicit inputs and are preserved bit-for-bit. This keeps the write contract native without assigning pointer/class identity, scalar type, units, or per-slot computation that the current proof does not establish.

The stage is pinned immediately after `wheel_pair_state_refresh` and before `optional_BODY_accumulator_sweep` by the existing residual-pass order contract.

## GATES_CHANGED

- all 12 dword contact-array destinations are native-owned;
- all 12 qword contact-array destinations are native-owned;
- exact array geometry and stage ordering are compile-time tested;
- per-slot producer arithmetic remains external;
- `+0x3660/+0x3668/+0x3670/+0x3678` remain a separate conditional state slice;
- complete `FUN_00765c40` internalization remains false;
- top-level provider remains present;
- external provider count remains 7.

## LIMITS

This PR does not infer what the dword tokens reference, does not reinterpret qword payloads as a physical scalar, and does not fold the later bounded state writes into the array stage. The lower scene-query boundary is unchanged.

## TESTS

`shift_runtime_fun_00765c40_contact_array_sweep_stage_check` pins slot count, exact first/last offsets, retail ordering and bit-preserving materialization. `tests/test_p2_4_fun_00765c40_contact_array_sweep_stage.py` cross-checks evidence/native/CMake fail-closed state.

## NEXT_STEP

Internalize the separately bounded `+0x3660/+0x3668/+0x3670/+0x3678` state-write slice while preserving its conditional semantics. Keep the top-level callback until complete end-to-end native execution exists.

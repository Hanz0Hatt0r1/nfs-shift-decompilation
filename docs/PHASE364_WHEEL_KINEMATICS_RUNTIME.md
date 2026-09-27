# Phase 364 — wheel kinematics runtime boundary

Phase 364 continues the non-rendering physics track from the tyre thermal pass into
FUN_00758b50, a per-step wheel kinematics/control-flow boundary invoked by
FUN_0076d100.

## Evidence source

Retail SHIFT.exe.c:

- FUN_00758b50 at source line 753071;
- FUN_00755950 at source line 750822;
- FUN_007555b0 at source line 750726;
- FUN_0076d100 at source line 762992;
- verified source SHA-256:
  512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9.

## Recovered four-wheel boundary

FUN_00758b50 walks four wheel blocks beginning at this + 0x848 with an
0xA80 byte stride. The first active-state gate is the byte at block +0xF8.

For an active wheel, the source constructs a relative vector, normalizes it, and
retains its Euclidean length. It then calls FUN_00755950 on the corresponding
wheel runtime object. The runtime objects begin at this + 0x400 and use the same
0xA80 stride.

The exact scalar handoff is:

    distance_error = runtime(+0x538) - relative_length
    stored_projection = -projection_input
    FUN_00755950(runtime, wheel_index, relative_length, projection_input)

FUN_00755950 stores distance_error at runtime +0x528, the negated projection at
+0x530, and forwards both through FUN_007555b0; the helper result is stored at
runtime +0x548. The helper's semantic return value is not recovered from the
available decompiler prototype, so the new contract leaves it opaque.

## Pair adjustment boundary

After the four wheel passes, the source applies two exact pairwise deltas.

Front:

    delta = ((+0x928 - +0x938) - (+0x13A8 - +0x13B8)) * +0x2E20
    +0x948 += delta
    +0x13C8 -= delta

Rear:

    delta = ((+0x1E28 - +0x1E38) - (+0x28A8 - +0x28B8)) * +0x2E28
    +0x1E48 += delta
    +0x28C8 -= delta

Both pair updates are guarded by their corresponding two byte flags. When +0x2E4C
is set, the source also invokes FUN_007555b0 for each pair and adds half of that
opaque helper result to both pair destinations.

The phase intentionally calls these pair adjustments, not anti-roll, load transfer,
or grip forces: those higher-level semantics are not established by this function alone.

## Final per-wheel transform

A final four-wheel loop checks block +0x11C. For eligible blocks it scales a scratch
vector from the block's +0x124 field and passes the result through FUN_007baa70 to
the wheel object and FUN_007baaf0 to the vehicle object.

No physical meaning is assigned to these transformations beyond the observed call
topology.

## Scope boundary

This phase does not claim:

- a complete tyre longitudinal/lateral force law;
- contact-material/friction semantics;
- suspension units;
- the semantic identity of FUN_007555b0's returned value;
- undocumented meanings for the pair-adjustment fields.

The result is a machine-readable wheel-kinematics boundary that later tyre/contact
decompilation can consume without inventing semantics.


## Phase 365 correction

The x87 call chain is decoded separately as SHIFT.SpringHelperRuntime/1. FUN_00755950 consumes the live x87 result of FUN_007555b0 and stores it at runtime +0x548. The helper also maintains +0x248/+0x250 gap history, the crossing flag +0x260 and trigger value +0x258. Phase 364 left this result opaque because the recovered C prototype lost the x87 return type; Phase 365 closes that ABI boundary while leaving physical units and higher-level tyre/contact semantics unresolved.

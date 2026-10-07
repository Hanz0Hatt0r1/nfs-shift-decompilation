# Phase 743 — `FUN_00766510` primary response post-application

Phase 743 closes the source-backed operations immediately after the Phase742 primary BODY application. It does not internalize the complete `FUN_00766510` anchor and does not reduce the external-provider count.

## PC retail sequence

The authoritative PC decompiler export shows source lines 759689–759695:

```text
FUN_00753650(local_1a0, &local_108, local_120)
HDVehicle+0x40a0 += local_1a0[0]
HDVehicle+0x40a8 += local_1a0[1]
HDVehicle+0x40b0 += local_1a0[2]
local_c0 += local_78
local_b8 += local_70
local_b0 += local_68
```

`local_120` is exactly the transformed response already produced by Phase742. `local_78/local_70/local_68` are the auxiliary lanes returned by the same current `FUN_007551e0` call.

`local_108` has an earlier source-visible producer using `HDVehicle+0x3b08`, but Phase743 deliberately keeps its ownership explicit rather than promoting that producer without a dedicated lifetime proof. Likewise the incoming `local_c0/local_b8/local_b0` accumulator already contains contributions from earlier `FUN_00766510` work and remains an explicit input.

## Exact `FUN_00753650` arithmetic

PC `FUN_00753650` at `0x00753650..0x0075368c` computes `left cross right` with x87 arithmetic. Each component:

1. forms two f64 products in x87;
2. executes opcode `DE E9` for the subtraction order visible in retail;
3. stores one f64 result.

The retail x87 control word used by this executable path is `0x027f`. The native helper uses the literal `DE E9` opcode rather than relying on GNU AT&T `fsubp` spelling, whose encoded direction is easy to reverse.

The frozen machine hashes are:

```text
FUN_00753650 0x00753650..0x0075368c
SHA-256 01a753b9668434bc769f1c9304931f0067e502e26f93097275e4c1b3469202ab

FUN_00766510 post-application 0x00766fd6..0x00767046
SHA-256 300ede8cca6353c0ccc96993161d299a67e337b5482c4ae40025e163069c07d7
```

## Native boundary

`execute_fun_00766510_primary_response_post_application()` consumes:

- the explicit caller reference vector (`local_108`);
- Phase742 transformed response (`local_120`);
- the incoming persistent caller triplet at `+0x40a0/+0x40a8/+0x40b0`;
- the current `FUN_007551e0` auxiliary response;
- the incoming local auxiliary accumulator.

It produces the source-ordered cross delta and the two updated accumulator triplets. No physical force/torque names are assigned.

## Xbox corroboration

Xbox recomp partition `nfs_shift_recomp.220.cpp` independently shows the same post-application topology: the caller triplet begins at `HDVehicle+16544` (`0x40a0`), a cross-like multiply/subtract sequence follows the primary BODY application, and both the caller triplet and accumulated auxiliary lanes are updated. Xbox is corroboration only; PC source and machine code remain authoritative for operand order and x87 precision.

## Remaining boundary

`contact_response` remains external. A full closure still requires the earlier `+0x3b20` response branch, ownership/timing of `+0x3b08`, the primary application/configuration records, later response work, the already-native auxiliary pair scheduling, final accumulated auxiliary application, and remaining caller-visible writes. The active provider count therefore remains seven.

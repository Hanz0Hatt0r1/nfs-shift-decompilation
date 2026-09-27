# Phase 392 — Body accumulator impulse primitives

`FUN_007baa70` and `FUN_007baaf0` are the positive/negative body accumulation primitives used by the SDF constraint projection path.

## Exact update

Both functions update the six accumulator channels at `+0x48/+0x50/+0x58` and +0x60/+0x68/+0x70`.

For lever arm `r=(x,y,z)` and contribution `v=(vx,vy,vz)`, the positive helper performs `linear += v` and `angular += r × v`. The negative helper performs the exact opposite updates.

The angular components are therefore:

`(y*vz - z*vy, z*vx - x*vz, x*vy - y*vx)`.

## Callers

The primitives are consumed from JOINT and BAR projection paths and also from the shared body projection chain. The implementation exposes these operations as neutral algebraic primitives while retaining the retail function names and offsets.

No physical force/torque units are inferred; the result remains a source-level accumulator contract.

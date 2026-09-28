# Phase 424 — source-backed pre-PhysX construction IR

Phase 424 adds a neutral intermediate representation for the construction boundary immediately before the provider/SDK handoff. It is deliberately limited to operations directly evidenced by the retail `SHIFT.exe.c` decompilation.

## Scope

The new `physics_constraint_construction_runtime.py` lowers a parsed SDF report into two concrete plans:

- `FUN_007b3670`: BODY record lowering into the `0x170`-byte runtime record.
- `FUN_007b3150`: JOINT/HINGE/BAR materialization, endpoint links, solver-node slot and vector copies.
- `FUN_007b3820`: solver scalar count and storage allocation plan, followed by the provider/generic-fallback boundary.

The module does **not** assign undocumented PhysX class names, ownership semantics or physical units. Provider vtable offsets remain explicit ABI facts.

## Body ABI

`FUN_007b3670` / `FUN_007bba90` now have a machine-readable contract for:

- source body name `+0x20` -> runtime name `+0x100`;
- mass `+0x120` -> runtime `+0x120`;
- inverse mass -> `+0x90`;
- inertia `+0x128/+0x12c/+0x130`;
- inverse inertia -> `+0x138/+0x140/+0x148`;
- auxiliary vector copies through `FUN_007bbb10` and `FUN_007bbb60`.

The auxiliary vectors remain intentionally unnamed.

## Constraint ABI

| Runtime record | Stride | Solver width | Main vectors | Endpoint slots |
| --- | ---: | ---: | --- | --- |
| JOINT | `0xA0` | 3 | `+0x88/+0x90/+0x98` | `+0x78/+0x80` |
| HINGE | `0xA0` | 2 | `+0x88/+0x90/+0x98` | `+0x78/+0x80` |
| BAR | `0xB8` | 1 | `+0x88/+0x90/+0x98` and `+0xA0/+0xA8/+0xB0` | `+0x78/+0x80` |

`JOINT&HINGE` expands into one JOINT and one HINGE runtime record in source order.

## BMW M3 E36 shape

The existing retail-shaped regression remains:

- 11 BODY records;
- 4 `JOINT&HINGE` source records;
- 20 BAR records;
- 28 runtime constraint records;
- 40 scalar solver nodes.

The stage also verifies the expected matrix allocation size `40 * 40 * 8` and blocks the plan when a constraint references a missing body.

## Remaining boundary

The next unresolved boundary is the actual SDK/provider object construction behind `FUN_007b3150` / `FUN_007b3820`. Phase 424 does not pretend that the neutral construction IR is itself a PhysX implementation.

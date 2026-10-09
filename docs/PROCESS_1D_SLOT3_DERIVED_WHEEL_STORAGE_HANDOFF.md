# Process 1D — slot3 derived-wheel storage handoff

This pass composes two already-merged retail machine proofs with the exact PC retail `SHIFT.exe.c` export. The machine contracts remain the authority for selected-wheel identity; the decompiler source is used only to bound visible local storage/forwarding syntax.

## `FUN_00763570`

The merged wheel-child contract proves:

```text
entry receiver = HDVehicle
wheel seed      = HDVehicle+0x400
stride          = 0xa80
iterations      = 4
slot3 receiver  = HDVehicle+0x2380
callee          = FUN_00755f80
```

The source-visible alias is only the local iterator storage:

```text
local_18._4_4_ = this+0x400
FUN_00755f80(local_18._4_4_)
local_18._4_4_ += 0xa80
```

Immediately after the wheel loop the same decompiler storage is overwritten with an unrelated floating-point temporary before any later reuse. No persistent store of the derived wheel pointer is visible, and the only consumer is the already-closed `FUN_00755f80` path.

## `FUN_00770e80`

The merged direct-carrier contract proves slot3 `HDVehicle+0x2380 -> FUN_00760b50`. In the pinned source export the selected pointer appears exactly once:

```text
FUN_00760b50((void *)(this+0x2380), ...)
```

It is an inline call argument, not assigned to persistent storage. The callee path is already closed for target writes and exact-root forwarding.

## Boundary

This closes only these two **source-visible, machine-proven** derived-wheel materializations. It does not cover register-only aliases, aliases created in callees, aggregate stores, other lifecycle functions, callback registration, or indirect consumers elsewhere.

Therefore `stored_or_escaped_aliases_ruled_out` remains false. Slot3 writer provenance remains false, P1.3D remains false, and provider count remains 7.

Reproduce:

```bash
python3 tools/ghidra/build_p1d_slot3_derived_wheel_storage_handoff.py \
  /path/to/SHIFT.exe.c \
  evidence/p1d_slot3_exact_wheel_direct_carrier_closure.json \
  evidence/p1d_slot3_fun00755f80_wheel_child_closure.json \
  --output out/p1d_slot3_derived_wheel_storage_handoff.json
```

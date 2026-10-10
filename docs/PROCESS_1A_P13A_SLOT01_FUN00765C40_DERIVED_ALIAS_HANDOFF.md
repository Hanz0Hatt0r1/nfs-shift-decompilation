# Process 1A / P1.3A — `FUN_00765c40` slot0/slot1 derived-alias handoff

## Scope

After exact wheel-root and known interior/child alias closure, P1.3A can consume two additional four-wheel pointer families already machine-bounded in `FUN_00765c40`:

- `wheel+0x678`;
- `wheel+0x7a8`.

The same upstream inventory also classifies the later `HDVehicle+0x6730` manager/subobject and the `+0x3430/+0x35c8/+0x35f8/+0x36e0` local arrays. These later families are included only for **identity classification**; incomplete callee lifetimes remain fail-closed.

## Slot geometry

Using the merged P1A wheel-root handoff:

```text
slot0 wheel = HDVehicle+0x400
slot1 wheel = HDVehicle+0xe80
slot0 target = HDVehicle+0x938..+0x93f
slot1 target = HDVehicle+0x13b8..+0x13bf
```

### `wheel+0x678`

```text
slot0 receiver = HDVehicle+0xa78
slot1 receiver = HDVehicle+0x14f8
writes = wheel+0x670 / wheel+0x678
slot0 writes = HDVehicle+0xa70 / +0xa78
slot1 writes = HDVehicle+0x14f0 / +0x14f8
```

The four-wheel machine surface proves no persistent/nonlocal store of the interior pointer. `[wheel+0x420]` is read through the identity `[wheel+0x678-0x258]`, but the child pointer is neither stored nor forwarded.

A raw `push ecx` at `0x00765da4` is retained as a real transient pointer copy. The exact same stack word is overwritten by `fstp DWORD PTR [esp]` at `0x00765dc9` before the next call, so that pointer does not reach `FUN_00758ad0`. The callee also overwrites incoming `ECX` before reading it as an object receiver.

### `wheel+0x7a8`

```text
slot0 receiver = HDVehicle+0xba8
slot1 receiver = HDVehicle+0x1628
writes = wheel+0x7a0 / wheel+0x7a8
slot0 writes = HDVehicle+0xba0 / +0xba8
slot1 writes = HDVehicle+0x1620 / +0x1628
```

The complete bounded ECX surface contains no pointer-valued store, no pointer push, and no direct call. Its writes are disjoint from wheel-local target `+0x538`.

## Post-derived identity inventory

The remaining machine-visible pointer families after these loops are not selected wheel aliases:

- `HDVehicle+0x6730` — a distinct local manager/subobject;
- `HDVehicle+0x3430`;
- `HDVehicle+0x35c8`;
- `HDVehicle+0x35f8`;
- `HDVehicle+0x36e0`.

The `+0x6730` path is important because it contains **positive pointer persistence**: `FUN_00a62940` stores the exact manager/subobject pointer into runtime-created nodes at `[node+0x24]` and `[node+0x34]`. This is not a selected wheel pointer, but the positive evidence is preserved rather than used to overstate the global runtime-pointer gate.

The four local-array families are proven HDVehicle-local rather than selected wheel roots/interiors. Their callee-facing lifetimes are still open and therefore are not used to promote broader escape gates.

## Gate

```text
FUN_00765c40 wheel+0x678 subset complete          = true
FUN_00765c40 wheel+0x7a8 subset complete          = true
post-derived identity inventory complete          = true
known wheel-alias target writer found             = false
known wheel-alias persistent escape found         = false
post-derived selected-wheel alias found           = false
non-wheel +0x6730 runtime backpointer store found = true
local-array callee lifetimes complete             = false

other derived aliases ruled out                   = false
reconstructed wheel pointers ruled out            = false
runtime-generated selected-wheel stores ruled out = false
callbacks / indirect entry ruled out               = false
stored-or-escaped aliases ruled out               = false
slot0 complete                                    = false
slot1 complete                                    = false
P1.3 complete                                     = false
provider count                                    = 7
```

## Reproduce

```bash
python3 tools/ghidra/build_p1a_slot01_fun00765c40_derived_alias_handoff.py \
  --output evidence/p1a_p13a_slot01_fun00765c40_derived_alias_handoff.json
```

The builder validates the exact slot identities, the four-wheel `+0x678/+0x7a8` sequences, normalized write surfaces, transient-stack overwrite, child-pointer non-forwarding, the positive non-wheel runtime backpointers, and incomplete local-array callee lifetimes.

## Next step

Trace the callee-facing lifetimes of `HDVehicle+0x3430/+0x35c8/+0x35f8/+0x36e0` through `FUN_007afd20`, `FUN_007baa70`, `FUN_00747b90`, and `FUN_007aefb0`. Separately consume the merged 16-carrier direct bulk-opcode absence and continue runtime-generated/copied selected-wheel pointers plus callback/indirect-entry surfaces.

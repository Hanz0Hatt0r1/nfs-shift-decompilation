# Process 1A / P1.3A: `0x005292db` computed `manager+0x374` receiver rejection

P1.3A owns computed forwarding sites `0x005292db` and `0x005f4ffa`. The latter is already closed; this proof closes the remaining computed site without opening any aggregate P1.3 gate.

`FUN_005292d0` captures entry `ECX` in `ESI`, materializes `ESI+0x374` at `0x005292db`, and passes that address as `ECX` to `FUN_00531fa0`, which ORs a selected bit into the pointed DWORD. The whole-image target entry surface is a single direct call at `0x005320c0`, with no absolute function-pointer occurrence for `FUN_005292d0`.

The caller obtains the target receiver through `FUN_00531ff0`: it loads `adapter+0x4`, then `FUN_0051b7b0` / `0x0040d4e6` returns `owner+0x218`. Thus `FUN_005292d0 this = adapter.owner+0x218`.

The adapter is the embedded `outer+0x1a90` object constructed by the unique `FUN_00532670` call at `0x0051b602`. `FUN_0051b660` binds `adapter+0x4` to the containing outer object via `FUN_008380d0`.

The outer class has exactly two constructor callsites. The static path constructs it at controller `0x00bdc570 + 0x3574 = 0x00bdfae4`, so the nested receiver is exactly `0x00bdfcfc` and its `+0x374` field is `0x00be0070`. The dynamic path allocates a fresh `0x1b54`-byte object and constructs the same class there, so its receiver is the separately owned heap subobject at `allocation+0x218`.

Participants Manager is the distinct image-global root `0x00bc9fc0` with vptr `0x00ab9190` and embedded-manager vptr `0x00ab916c`. Therefore `0x005292db` cannot be the Participants Manager `+0x374` writer. Numeric offset equality is not used as identity evidence.

Together with the merged `0x005f4ffa` contract, the P1.3A computed-site subfrontier is complete. Slot0 `HDVehicle+0x938` and slot1 `HDVehicle+0x13b8` selected-root provenance remain open, as do the aggregate manager/HDVehicle join, final `0x004b86cf`, P1.3 completion and provider removal. Provider count remains 7.
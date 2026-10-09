# Process 1A / P1.3A: `0x005f4ffa` computed `manager+0x374` receiver rejection

P1.3A owns computed forwarding sites `0x005292db` and `0x005f4ffa`. This closure handles only `0x005f4ffa`.

`FUN_005f4f50` enters its machine body at `0x005f4f55`, captures entry `ECX` in `ESI` at `0x005f4f6d`, then materializes `ESI+0x374` at `0x005f4ffa`. The pointer is passed as the destination to `FUN_00901cc5` for a `0x20`-byte copy from the same receiver's `+0x354` field.

The whole-image static entry surface for the wrapper is bounded to two direct calls (`0x005f79d7`, `0x005f7b85`) and one direct tail jump (`0x005f8aff`), with zero absolute function-pointer occurrences for either `0x005f4f50` or body entry `0x005f4f55`.

All three paths carry the separately allocated `0x1fe0` receiver class constructed by `FUN_005f78e0` with exact vptr `0x00ae2a60`. The teardown path `FUN_005f79c0` reinstalls that same vptr immediately before its call. The other two paths preserve the same receiver through `FUN_005f8950`; that object is allocated in `FUN_005fbbb0`, constructed by `FUN_005f78e0`, and stored at owner `+0x2448`. This receiver identity agrees with the independently merged P1.3B contract for the same `0x00ae2a60` class.

Participants Manager is a different exact object domain: root vptr `0x00ab9190`, embedded `+0x20` vptr `0x00ab916c`. Therefore `0x005f4ffa` cannot write Participants Manager `+0x374`; the shared numeric offset is not used as identity evidence.

P1.3A still has `0x005292db` plus slot0 `HDVehicle+0x938` and slot1 `HDVehicle+0x13b8` provenance open. Global manager/HDVehicle identity, final `0x004b86cf`, P1.3 completion and provider removal remain fail-closed; provider count remains 7.
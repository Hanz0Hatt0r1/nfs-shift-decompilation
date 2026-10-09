# Process 1B / P1.3B: `0x005f6eda` computed `manager+0x374` receiver rejection

`0x005f6eda` is the final computed forwarding site owned by P1.3B after `0x0070f62d` was closed.

The target lies in `FUN_005f6850`. Its computed `receiver+0x374` pointer is passed as a destination to `FUN_00901cc5`. The exact direct-call surface for `FUN_005f6850` contains one caller: `FUN_005f7df0` at callsite `0x005f7e9b`, and that call passes `FUN_005f7df0`'s own receiver unchanged as `FUN_005f6850`'s `this`.

The enclosing receiver class is separately constructed by `FUN_005f78e0` after a `0x1fe0` allocation in `FUN_005fbbb0`. The constructor writes vptr `0x00ae2a60`; `FUN_005f79c0` reinstalls the same vptr during teardown. The same object carries the state/string fields used throughout this path, including `+0x374`, `+0x1db4`, and the `+0x1fcc/+0x1fd0/+0x1fd4` string members.

Participants Manager is a different exact object domain: root vptr `0x00ab9190`, embedded `+0x20` vptr `0x00ab916c`. Therefore the `0x005f6eda` destination cannot be Participants Manager `+0x374`.

This closes both computed sites owned by P1.3B (`0x005f6eda`, `0x0070f62d`). Aggregate P1.3 computed closure still requires the P1.3A and P1.3D shard handoffs before Process 1B performs the final `manager+0x374 -> HDVehicle+0x4330` identity join and `0x004b86cf` / slot2 adjudication. Provider count remains 7.

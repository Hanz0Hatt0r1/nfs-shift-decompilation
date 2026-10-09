# Process 1D — slot3 stack exact-root alias closure

The preceding direct-storage pass found only two exact entry-root copies in the 15 proven slot3 carrier functions. Both are stack locals. This pass traces those two aliases through their complete hash-pinned PC retail decompiler functions.

## `FUN_00758b50`: `local_2c`

The complete alias-use surface is:

```text
local_2c = param_1
read [local_2c+0x33a0] for BODY transform input
read [local_2c+0x33a0] for vector add input
load [local_2c+0x33a0]
param_1 = local_2c
```

`local_2c` is never stored nonlocally and is never passed as the exact HDVehicle root. Its callee-facing uses first dereference `HDVehicle+0x33a0`, producing the separately proven chassis BODY pointer.

## `FUN_00763570`: `local_4c`

```text
local_4c = this
```

There are no later uses of `local_4c` in the function.

## Boundary

This closes only these two exact entry-root stack aliases. It does not cover derived wheel/base pointers, register aliases, aliases created in callees, aggregate stores, or callback registration. Therefore the global stored/escaped alias gate remains false.

Reproduce:

```bash
python3 tools/ghidra/analyze_p1d_slot3_stack_root_alias_source.py \
  /path/to/SHIFT.exe.c \
  --output out/p1d_slot3_stack_root_alias_closure.json
```

Slot3 writer provenance remains false, P1.3D remains false, and provider count remains 7.

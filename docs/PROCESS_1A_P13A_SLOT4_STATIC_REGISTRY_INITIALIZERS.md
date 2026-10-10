# Process 1A / P1.3A — slot4 static registry initializer result types

Merged `SHIFT.P1A.P13AFun0067b660Slot4DispatchAbiFrontier/1` isolates a possible ABI-compatible indirect `+0x4` dispatcher at `0x006145c4`, but the registry's initializer-callback result type is not known globally.

## Two static registrations

The retail PC 1.02 image contains two statically supplied registry initializer tables:

| Registry call | Table | Entry `+0x0` initializer | Successful result vptr |
|---|---|---|---|
| `0x005ff8c6` | `0x00ae7d84` | `0x00614700` | `0x00ae7d84` |
| `0x005ff8d5` | `0x00ae7d6c` | `0x00614130` | `0x00ae7d6c` |

The registry calls the initializer through `0x00614584: call edx` after loading its table entry `+0x0`. It then writes the initializer return value to registry record `+0x8` at `0x0061458b`. That returned pointer is the object later used as receiver **and** explicit stack argument by `0x006145c4`.

The two initializer functions allocate an object and set the returned object's vptr immediately before returning:

```text
0x0061472b  mov [eax],0x00ae7d84
0x0061473e  ret
0x00614170  mov [eax],0x00ae7d6c
0x00614183  ret
```

The second initializer may return null on allocation failure. Neither initializer can return an object with animation vptr `0x00af7544` on its successful construction path. Thus **the two statically registered result types do not explain `FUN_0067b660` invocation through this registry**.

## Boundary

The third registration-thunk call, `0x005ffc7a`, forwards dynamically supplied registration arguments. This contract does **not** prove the dynamic table types or rule out a dynamic registration of the animation object. Alternate indirect dispatch shapes also remain open. No global negative callback, stored alias, runtime-generated pointer, slot0, slot1 or P1.3 gate changes. External provider count remains 7.

Promoted only `p13a_slot4_static_registry_initializer_result_subset_complete=true`.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_slot4_static_registry_initializers.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun0067b660_slot4_dispatch_abi_frontier.json \
  --output evidence/p1a_p13a_slot4_static_registry_initializers.json
pytest -q tests/test_process1a_p13a_slot4_static_registry_initializers.py
```

The executable SHA-256 and individual `.text`/`.rdata` machine ranges are pinned, and the initializer call, return and vptr-store instructions are checked directly. The next blocker is dynamic registration at `0x005ffc7a` or a different virtual-dispatch shape.
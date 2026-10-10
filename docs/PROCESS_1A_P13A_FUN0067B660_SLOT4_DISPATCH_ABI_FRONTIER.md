# Process 1A / P1.3A — `FUN_0067b660` slot `+0x4` dispatcher ABI frontier

## Blocker and scope

Merged `SHIFT.P1A.P13AFun0067b660StaticVtableObject/1` proves `0x00af7544[+0x4] = FUN_0067b660`, but does **not** prove which indirect dispatcher reaches that slot or the identity of the callback's explicit `[EBP+0x8]` argument. The callback ends in a plain `ret`, not `ret 4`; a one-argument caller-cleaned invocation is a useful **bounded candidate shape**, not a global ABI theorem.

This contract inventories the exact PC retail 1.02 machine image for:

1. raw `call DWORD PTR [GPR+0x4]` instructions;
2. `call GPR` instructions whose target GPR was loaded from `[GPR+0x4]` in a bounded, branch/call/clobber-aware preceding window of at most 16 decoded instructions;
3. only the subset where the instruction immediately preceding the call is a `push` and the instruction immediately after is `add esp,0x4`.

This is intentionally narrower than all virtual dispatch, computed slot addressing, alternate cleanup, and stored/delayed aliases.

## Whole-image machine inventory

| Surface | Count |
|---|---:|
| Decoded instructions | 2,847,850 |
| Raw `call [GPR+4]` | 79 |
| Bounded register-loaded `+4` indirect calls | 1,832 |
| Raw memory calls with immediate one-argument caller cleanup | 0 |
| Bounded register-loaded calls with immediate one-argument caller cleanup | **2** |

The two bounded register candidates are `0x006022ee` and `0x006145c4`. Neither is currently proven to dispatch to the animation object's vtable.

### `0x006145c4`: fixed registry callback result

At `0x00614584`, the registry calls an initializer callback, then at `0x0061458b` stores its **return value** into registry record `+0x8`. The registry is based at `0x00be8730`, has 8 records of 12 bytes, and the consumer iterates from `0x00be8738`.

```text
0x006145b0  mov eax,[esi]        ; record+8: initializer callback result
0x006145be  mov ecx,[eax]        ; vptr from returned object
0x006145c0  mov edx,[ecx+0x4]    ; slot +4
0x006145c3  push eax             ; explicit argument = returned object
0x006145c4  call edx
0x006145c6  add esp,0x4
0x006145c9  mov [esi],0           ; clear registry result
```

The exact direct registration-thunk call surface for `0x006144f0` is `0x005ff8c6`, `0x005ff8d5`, and `0x005ffc7a`. The third forwards dynamically supplied registration arguments, so the set of possible initializer callback return types is **not** closed. The evidence does not establish that an instance of the `0x00af7544` class is in this registry.

### `0x006022ee`: function-table pointer argument

```text
0x006022e8  mov eax,[esi]        ; table pointer
0x006022ea  mov ecx,[eax+0x4]    ; slot +4
0x006022ed  push eax             ; explicit argument = table pointer
0x006022ee  call ecx
0x006022f0  add esp,0x4
```

This is an ABI-compatible call shape, but no machine evidence joins its table pointer to `0x00af7544` or its target to `FUN_0067b660`.

## Adjudication

Promoted **only**:

`p13a_fun0067b660_immediate_slot4_caller_cleanup_subset_complete = true`.

Still false: `fun0067b660_immediate_slot4_dispatch_target_proven`, callback argument provenance, selected-wheel rejection, global callback/incoming-indirect closure, runtime-generated selected-wheel pointer-store closure, stored aliases, slot0, slot1, and aggregate P1.3. The independently proven positive wheel queue store from #1909 remains authoritative. Provider count remains **7**.

## Reproduce

```bash
python tools/ghidra/analyze_p1a_fun0067b660_slot4_dispatch_abi.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun0067b660_static_vtable_object.json \
  --output evidence/p1a_p13a_fun0067b660_slot4_dispatch_abi_frontier.json
pytest -q tests/test_process1a_p13a_fun0067b660_slot4_dispatch_abi.py
```

The analyzer rejects a different executable SHA, wrong upstream format/vtable, machine range drift, changed registry thunk direct-call surface, or changed candidate set. Five focused tests cover the machine anchors, expected inventory, clobber/intervening-call boundaries, and fail-closed gates.

## Next work

Trace dynamic registration arguments through `0x005ffc7a` and the initializer callback's return type, or recover alternate indirect slot-4 invocation forms. Do **not** equate the registry result with the animation object until a concrete object/target join is proven.
# Process 1A / P1.3A — direct absolute writable transfer composition

## Scope

This contract composes every retail instruction of the form `call/jmp DWORD PTR ds:<absolute address>` whose target slot lies in the file-backed `.data` range `0x00b81000..0x00bbc600`.

It intentionally does **not** claim anything about pointers first loaded from writable memory into a register, base/index-addressed slots, heap objects, arbitrary aliases or runtime-generated addresses.

## Complete direct-absolute inventory

The whole image contains **334** such transfers through **259** unique writable slots. The unique slots partition exactly into three groups:

- **255** NVAPI QueryInterface slots / **255** transfers, classified by `SHIFT.P1A.P13AFun005ffc50NvapiWritableDispatchTable/1`;
- **2** callback-pair slots (`0x00b87b7c`, `0x00b87b80`) / **77** transfers, whose direct/static producer surface is classified by `SHIFT.P1A.P13AFun005ffc50WritableCallbackPairStaticProvenance/1`;
- **2** fixed bridge slots / **2** transfers.

The fixed bridge slots are:

| Slot | File-backed target | Direct transfer | Direct absolute writers |
|---|---|---:|---:|
| `0x00b87b64` | `0x00901707` | one `jmp` | 0 |
| `0x00b87b68` | `0x0090162a` | one `jmp` | 0 |

Neither fixed target is `FUN_005ffc50`. The callback pair has no bounded direct/static `FUN_005ffc50` value, and the NVAPI table contains no internal static `FUN_005ffc50` provider.

Therefore **no `FUN_005ffc50` provider exists in the complete direct-absolute `.data` indirect-transfer class**.

## Gate effect

Promoted only `p13a_fun005ffc50_direct_absolute_writable_indirect_transfer_slot_inventory_complete=true`.

Still fail-closed: register-loaded or base/indexed writable pointers, alias writers, external/runtime mutation, general writable-memory closure, return-value closure, unbounded phi, encoded/reconstructed callback entry, dynamic registry registration, callback/incoming-indirect closure, runtime-generated selected-wheel stores, stored aliases, slot0, slot1 and aggregate P1.3. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/compose_p1a_fun005ffc50_direct_absolute_writable_slots.py /path/to/SHIFT.exe \
  --pair evidence/p1a_p13a_fun005ffc50_writable_callback_pair.json \
  --nvapi evidence/p1a_p13a_fun005ffc50_nvapi_writable_table.json \
  --output evidence/p1a_p13a_fun005ffc50_direct_absolute_writable_slots.json
pytest -q tests/test_process1a_p13a_fun005ffc50_direct_absolute_writable_slots.py
```

## Next step

Focus writable-memory analysis on register-loaded/base-indexed/aliased sources. The direct-absolute `.data` indirect-transfer class no longer needs to be rescanned.

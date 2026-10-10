# Process 1A / P1.3A — `FUN_005ffc50` direct `creg` entry closure

## Scope

Merged static registry work leaves `0x005ffc7a` as a dynamic registration forwarder. This pass asks a narrower question: can the retail executable reach that `creg` branch through an ordinary direct call or a raw static pointer to `FUN_005ffc50`?

## Machine result

`FUN_005ffc50` is a 312-byte retail function. It loads its command from entry stack `+0x8`. Command `0x63726567` selects the `creg` branch at `0x005ffc69`; that branch forwards entry stack `+0xc` and `+0x10` to `0x006144f0` at `0x005ffc7a`.

Whole-image disassembly contains exactly **13** direct calls to `FUN_005ffc50`, from exactly three callers: `FUN_005b81a0`, `FUN_005b8210`, and `FUN_005be1b0`. Recovering the second stack argument at every call gives:

- `0x6d696372`: 3
- `0x63646563`: 3
- `0x636c6964`, `0x63726566`, `0x69646576`, `0x6f646576`, `0x706f7274`, `0x73657276`, `0x74696d65`: 1 each

There are **zero** direct calls with command `0x63726567` (`creg`).

The whole image also contains **zero** exact little-endian absolute-VA literals for `0x005ffc50` and **zero** exact RVA literals for `0x001ffc50`. Thus there is no ordinary raw static function-pointer seed for the dispatcher.

## Gate effect

Promoted only:

- `p13a_fun005ffc50_direct_creg_entry_subset_complete = true`.

The result proves only that direct calls and exact raw VA/RVA pointer literals do not reach `creg`. The branch remains machine-present and therefore any real invocation would require an indirect, reconstructed, encoded, or runtime-generated entry path not closed here.

Global callback/incoming-indirect, reconstructed callback entry, selected-wheel runtime-store negative, stored aliases, slot0, slot1, and aggregate P1.3 remain fail-closed. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_direct_creg_entry.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_slot4_static_registry_initializers.json \
  --output evidence/p1a_p13a_fun005ffc50_direct_creg_entry_closure.json
pytest -q tests/test_process1a_p13a_fun005ffc50_direct_creg_entry.py
```

## Next step

Trace reconstructed/indirect incoming entry to `FUN_005ffc50`, or recover another concrete `FUN_0067b660` slot `+0x4` dispatcher with explicit argument provenance.

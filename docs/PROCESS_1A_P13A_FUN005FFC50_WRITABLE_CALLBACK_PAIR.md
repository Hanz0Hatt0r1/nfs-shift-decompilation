# Process 1A / P1.3A — writable callback pair direct/static provenance

## Scope

The read-only/stack contract deliberately left writable `.data` function-pointer slots open. This pass classifies the two heavily used writable callback slots `0x00b87b80` and `0x00b87b7c` only on their complete **direct/static** producer surface.

The retail image performs 26 direct indirect transfers through `0x00b87b80` and 51 through `0x00b87b7c`. Their direct absolute writers are confined to the initialization/configuration family around `FUN_00616687`.

## Initial/default provenance

The file-backed initial values are:

- `0x00b87b80 = 0x006165b6`;
- `0x00b87b7c = 0x006165c0`.

Startup initializer-table entries at `0x00aa77b8/0x00aa77bc` point to `0x00a7fa5c/0x00a7fa67`. Those functions copy the callback pair into default snapshots `0x00be87dc/0x00be87e0`. Therefore the zero/null configuration path does not introduce an unrelated static callback value.

## Direct setter/config surface

`FUN_00616687` has exactly two direct callsites: `0x0060adde` and `0x0061ccbe`. `FUN_0060ad99`, which feeds the first one, itself has exactly two direct callsites:

- `0x005f3b7f`: the branch reaches the call with `EAX == 0` and pushes `NULL/NULL`, selecting defaults;
- `0x005f47b7`: pushes fixed callbacks `0x005f46f0` / `0x005f4760`.

The other direct setter call at `0x0061ccbe` pushes fixed callbacks `0x0061cb43` / `0x0061cbff`.

Thus, on this bounded direct/static producer surface, candidate values are:

- slot `0x00b87b80`: `{0x006165b6, 0x005f46f0, 0x0061cb43}`;
- slot `0x00b87b7c`: `{0x006165c0, 0x005f4760, 0x0061cbff}`.

None is `FUN_005ffc50` (`0x005ffc50`). There are also zero exact raw VA/RVA pointer literals for `FUN_00616687` or `FUN_0060ad99`, so no additional exact static address-taken entry is present.

## Boundary

This is not global writable-memory closure. Alias writes, reconstructed/indirect entry to the setter/config function, loader/external mutation and other writable callback slots remain open. Consequently `writable_memory_or_runtime_fun005ffc50_entry_ruled_out` stays false.

Promoted only `p13a_fun005ffc50_writable_callback_pair_direct_static_provenance_subset_complete=true`. Slot0, slot1, aggregate P1.3, callback/incoming-indirect, stored aliases and runtime-generated selected-wheel store gates remain fail-closed. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_writable_callback_pair.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_trivial_constant_return_producers.json \
  --output evidence/p1a_p13a_fun005ffc50_writable_callback_pair.json
pytest -q tests/test_process1a_p13a_fun005ffc50_writable_callback_pair.py
```

## Next step

Trace alias/indirect writers of this pair or classify the remaining writable function-pointer slots. The direct/static producer surface for `0x00b87b80/0x00b87b7c` no longer needs to be rescanned.

# Process 1A / P1.3A — NVAPI writable dispatch table

## Scope

The writable indirect-transfer inventory contains a dense 255-slot range `0x00bbbd0c..0x00bbc4fc`. This pass identifies and bounds that entire range so it is not confused with an internal game callback registry.

## Table shape

The retail image contains **255** records of stride 8:

- record `+0x0`: writable function pointer;
- record `+0x4`: NVAPI function ID.

All 255 initial pointer fields equal `0x00a61a48`. All 255 function IDs are nonzero and unique. The first ID is `0x6c2d048c`, the last is `0xb85de27c`, and the table includes anchor ID `0xe5ac921f` at index 5. The dword at `0x00bbc504` following the last record is zero and terminates the resolver loop.

There are exactly 255 direct thunk transfers, from `0x00a61ae8` through `0x00a620dc`, one per pointer slot.

## Resolver provenance

The resolver explicitly:

1. pushes the string `nvapi.dll` and calls imported `LoadLibraryA`;
2. pushes `nvapi_QueryInterface` and calls imported `GetProcAddress`;
3. keeps the returned query function in `EBP`;
4. initializes the provider using ID `0x0150e828`;
5. walks records from `0x00bbbd0c`, calls `nvapi_QueryInterface(function_id)`, and for each nonzero result stores `EAX` into the record pointer at `0x00a61ac2`;
6. advances by 8 bytes until the zero ID terminator.

Thus the bounded value class for these writable slots is either the initial internal status/failure stub `0x00a61a48` or a nonzero pointer returned by the external `nvapi_QueryInterface` provider. No internal static provider of `FUN_005ffc50` is present in this table.

## Gate effect

Promoted only `p13a_fun005ffc50_nvapi_writable_dispatch_table_subset_complete=true`.

This is not global writable-memory closure. Other writable slots, malicious/replaced external modules, arbitrary alias writes, runtime-generated pointers, general return/phi provenance, callback/incoming-indirect, stored aliases, slot0, slot1 and aggregate P1.3 remain fail-closed. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_nvapi_writable_table.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_writable_callback_pair.json \
  --output evidence/p1a_p13a_fun005ffc50_nvapi_writable_table.json
pytest -q tests/test_process1a_p13a_fun005ffc50_nvapi_writable_table.py
```

## Next step

After excluding the NVAPI table and the `0x00b87b7c/0x00b87b80` pair, inventory any remaining writable function-pointer sources or continue return/phi provenance relevant to `FUN_005ffc50`.

# Process 1B: HDVehicle+0x4330 direct absolute writable indirect recovery

## Scope

This contract reuses the complete PC retail 1.02 inventory of direct indirect transfers through absolute writable `.data` slots from Process 1A, but asks the Process 1B question: can the bounded internal/static value provenance of those slots produce one of the 15 canonical `HDVehicle+0x4330` carrier function addresses?

Upstream contracts:

- `SHIFT.P1A.P13AFun005ffc50DirectAbsoluteWritableTransferComposition/1`
- `SHIFT.P1A.P13AFun005ffc50WritableCallbackPairStaticProvenance/1`
- `SHIFT.P1A.P13AFun005ffc50NvapiWritableDispatchTable/1`

## Result

The complete direct-absolute writable transfer inventory contains **334 transfers through 259 unique `.data` slots**.

The bounded value classes are:

- two fixed bridge slots / two transfers, with initial targets `0x00901707` and `0x0090162a` and zero direct absolute writers;
- the two-slot callback pair / 77 transfers, whose six direct/static candidate values are `0x005f46f0`, `0x005f4760`, `0x006165b6`, `0x006165c0`, `0x0061cb43`, and `0x0061cbff`;
- the 255-slot NVAPI QueryInterface dispatch table / 255 transfers, whose internal initial value is status stub `0x00a61a48` and whose nonzero runtime values are returned by external `nvapi_QueryInterface`.

Across the **9 bounded internal/static candidate values**, exact intersection with the 15 canonical P1B carrier addresses is **zero**.

## Gate effect

Promoted only:

- `direct_absolute_writable_indirect_slot_inventory_complete=true`;
- `bounded_internal_static_provider_subset_complete=true`;
- `bounded_internal_static_provider_exact_carrier_hit_found=false`.

Still fail-closed:

- external/runtime NVAPI result identity;
- callback-pair alias or indirect writers;
- register-loaded/base-indexed writable targets;
- arbitrary runtime mutation;
- global indirect entry;
- runtime-generated/copied function pointers and generic stores/copies;
- `manager+0x374 -> HDVehicle+0x4330`;
- `0x004b86cf`/slot2 and aggregate P1.3.

Provider count remains **7**.

## Reproduction

```bash
python3 tools/ghidra/build_p1b_hdvehicle_4330_direct_absolute_writable_indirect_recovery.py \
  --output /tmp/p1b_hdvehicle_4330_direct_absolute_writable_indirect_recovery.json
```

The generated JSON must match `evidence/p1b_hdvehicle_4330_direct_absolute_writable_indirect_recovery.json` byte-for-byte after deterministic JSON formatting.

# Process 1B — static/source-visible exact-carrier pointer materialization coverage

This aggregate composes four already-bounded ways an exact P1B `HDVehicle+0x4330` carrier could appear as a static or source-visible function pointer.

| Class | Bounded surface | Exact carrier hits |
| --- | ---: | ---: |
| vtable candidate targets | 22,416 slots | 0 |
| static-table absolute pointers | 55,066 records / 684,472 raw bytes | 0 |
| whole-image VA/RVA literals | 8,801,792 retail bytes | 0 |
| Ghidra C exact-symbol references | 40 occurrences | 0 symbol-as-value/address-taken uses |

All four upstream contracts use the canonical 15-function P1B carrier set and remain provider-count 7.

## Reproduce

```bash
python3 tools/ghidra/build_p1b_hdvehicle_4330_static_pointer_materialization_coverage.py \
  evidence/p1b_hdvehicle_4330_exact_carrier_vtable_surface.json \
  evidence/p1b_hdvehicle_4330_exact_carrier_static_table_surface.json \
  evidence/p1b_hdvehicle_4330_whole_image_literal_pointer_surface.json \
  evidence/p1b_hdvehicle_4330_source_symbol_address_taking.json \
  --output evidence/p1b_hdvehicle_4330_static_pointer_materialization_coverage.json
```

The builder fails closed if an upstream format/readiness/provider gate drifts, if any vtable/static-table/whole-image exact carrier pointer appears, or if the C export gains a non-call exact-carrier symbol use.

## Gate discipline

This is **not** a global function-pointer closure. It does not rule out runtime-generated, copied, encoded, reconstructed, code-relative/EIP-derived, heap/global-written, table-transformed or otherwise decompiler-opaque exact-carrier pointers.

```text
static/source-visible pointer materialization coverage composed = true
bounded static exact-carrier materialization hit = false

generic function-pointer stores/copies ruled out = false
runtime-generated/copied pointers ruled out = false
computed/encoded pointers ruled out = false
runtime callback registration ruled out = false
indirect entry into carriers ruled out = false
manager+0x374 identity join complete = false
final 0x004b86cf rejection = false
P1.3 complete = false
provider count = 7
```

## Next step

Continue machine-level runtime pointer creation/stores and reconstructed pointer paths. This aggregate is the static/source-visible no-duplication baseline for that work.

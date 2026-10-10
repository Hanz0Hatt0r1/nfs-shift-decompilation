# Process 1B: image-backed exact-carrier table seed closure

## Scope

This contract closes one bounded `HDVehicle+0x4330` indirect-entry seed class: an image-backed table element that already contains either an exact canonical P1B carrier VA or its exact image-base-relative RVA.

It does **not** claim that all table-derived or memory-derived carrier pointers are impossible.

## Inputs

- `SHIFT.P1B.HDVehicle4330WholeImageLiteralPointerSurface/1`
- `SHIFT.P1B.HDVehicle4330ExactCarrierStaticTableSurface/1`

The whole-image contract scans all 8,801,792 retail bytes for little-endian 32-bit encodings of all 15 canonical P1B carrier absolute VAs and exact RVAs. Both hit counts are zero.

The Ghidra static-table cross-check covers 55,066 candidate records / 684,472 exported raw bytes and contains zero exact carrier absolute-VA pointers.

## Result

For the direct image-backed table forms:

- table element == exact carrier VA: **0 seeds**;
- table element == exact carrier RVA: **0 seeds**;
- therefore `preferred_image_base + [image-backed exact-RVA table element]` cannot produce an exact P1B carrier in the retail image.

The retail-byte whole-image scan is the authority for the zero direct VA/RVA encoding result. The Ghidra static-table export is retained only as a finite navigation/cross-check surface.

## Gates

Promoted only:

```text
image_backed_direct_table_exact_carrier_seed_subset_complete = true
image_backed_exact_carrier_va_table_seed_found               = false
image_backed_exact_carrier_rva_table_seed_found              = false
direct_imagebase_plus_image_table_exact_rva_seed_path_ruled_out = true
```

Still fail-closed:

```text
memory_table_derived_carrier_pointers_ruled_out              = false
computed_or_encoded_code_pointers_ruled_out                  = false
runtime_computed_carrier_pointers_ruled_out                  = false
runtime_copied_or_encoded_carrier_pointers_ruled_out         = false
generic_function_pointer_stores_copies_ruled_out             = false
indirect_entry_into_carriers_ruled_out                       = false
global_runtime_derived_4330_alias_surface_complete           = false
manager_374_join_to_hdvehicle_4330_complete                  = false
last_literal_0x004b86cf_rejected                             = false
p1_3_control_producer_complete                               = false
external_provider_count                                      = 7
```

## Remaining frontier

Still open are transformed/delta/encoded table entries, runtime-populated tables, cross-block reconstruction, opaque helper returns, runtime patching and pointer copies from runtime-created storage.

The next useful P1B step is to bound transformed/delta table entries or other cross-block memory-derived exact-carrier reconstruction, then classify any positive pointer store/copy sinks.

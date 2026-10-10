# Process 1B: bounded HDVehicle+0x4330 indirect-entry coverage v4

## Purpose

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/4` supersedes `/3` by composing two additional image-backed table seed classes into the current bounded exact-carrier indirect-entry baseline.

## Added bounded classes

### Direct image-backed exact VA/RVA table seeds

The retail whole-image literal scan covers all 8,801,792 bytes and contains zero little-endian exact canonical P1B carrier absolute VAs and zero exact carrier RVAs. The finite Ghidra static-table cross-check covers 55,066 records and also contains zero exact carrier absolute-VA pointers.

Therefore these direct image-backed forms have zero seeds:

```text
table_dword == exact carrier VA
table_dword == exact carrier RVA
pointer = preferred_image_base + exact carrier RVA table_dword
```

### `.text`-base delta table seeds

For each of the 15 P1B carriers the machine analyzer searches for:

```text
table_dword = carrier_va - 0x00401000
pointer = 0x00401000 + table_dword
```

There is one raw whole-image diagnostic and zero matches in non-executable sections. The one diagnostic is the rel32 displacement of:

```text
0x0059b76b CALL 0x009031bd
```

It is not a data-table element and the control target is not an exact P1B carrier.

## Aggregate bounded coverage

Version `/4` now contains seven bounded classes:

1. static/source-visible exact carrier materialization;
2. canonical computed/loader publication;
3. bounded runtime callback registration, including `_bsearch`;
4. exact preferred-imagebase + exact carrier-RVA immediate synthesis;
5. constant-only straight-line encoded carrier synthesis;
6. direct image-backed exact VA/RVA table seeds;
7. image-backed `.text`-base delta table seeds.

Bounded exact carrier hits remain **0**.

## Gates

Promoted only:

```text
bounded_indirect_entry_coverage_composed                    = true
image_backed_direct_table_seed_subset_included              = true
image_backed_text_base_delta_table_seed_subset_included     = true
bounded_indirect_entry_exact_4330_carrier_hit_found         = false
```

Still fail-closed:

```text
memory_table_derived_carrier_pointers_ruled_out             = false
computed_or_encoded_code_pointers_ruled_out                 = false
runtime_computed_carrier_pointers_ruled_out                 = false
runtime_copied_or_encoded_carrier_pointers_ruled_out        = false
runtime_generated_or_copied_function_pointers_ruled_out     = false
generic_function_pointer_stores_copies_ruled_out            = false
runtime_callback_registration_ruled_out                     = false
remaining_callback_api_families_ruled_out                   = false
indirect_entry_into_carriers_ruled_out                      = false
global_runtime_derived_4330_alias_surface_complete          = false
manager_374_join_to_hdvehicle_4330_complete                 = false
last_literal_0x004b86cf_rejected                            = false
p1_3_control_producer_complete                              = false
external_provider_count                                     = 7
```

## Remaining frontier

The remaining pointer-origin surface is now concentrated in transformed/delta chains beyond the closed direct forms, other section bases, runtime-populated tables, cross-block arithmetic, runtime-copied pointers, delayed module-base consumers, runtime patching, remaining callback families and opaque indirect dispatch.

The next P1B step is to bound cross-block or runtime-populated memory/table-derived exact-carrier reconstruction and classify any positive runtime store/copy sink before changing global indirect-entry gates.

# Process 1B: `.text`-base delta table seed surface

## Scope

This machine-level closure covers one transformed image-backed table encoding for the 15 canonical P1B `HDVehicle+0x4330` carriers:

```text
pointer = .text_base + table_dword
where table_dword == carrier_va - .text_base
```

Retail PC 1.02 has preferred image base `0x00400000`, `.text` RVA `0x1000`, therefore `.text_base = 0x00401000`.

## Machine scan

The hash/size-locked analyzer scans all 8,801,792 retail bytes for each exact `carrier_va - 0x00401000` little-endian dword and maps every match to the authoritative PE section table.

Result:

- exact P1B carrier count: 15;
- raw whole-image `.text`-base-delta matches: **1**;
- matches in non-executable image sections: **0**;
- unclassified executable matches: **0**.

The sole raw diagnostic is for `FUN_00768a4d`:

```text
carrier                  = 0x00768a4d
carrier - .text_base     = 0x00367a4d
file offset              = 0x0019ab6c
sequence VA              = 0x0059b76c
```

Exact machine bytes show the dword begins immediately after opcode `E8`:

```text
0x0059b76b  call rel32 0x009031bd
```

Therefore `4d 7a 36 00` is the signed rel32 displacement of that direct call, not a data-table element. The target `0x009031bd` is not one of the 15 exact P1B carriers.

## Adjudication

Promoted only:

```text
image_backed_text_base_delta_table_seed_subset_complete = true
image_backed_text_base_delta_table_seed_found           = false
all_raw_text_base_delta_diagnostics_classified          = true
```

Still fail-closed:

```text
memory_table_derived_carrier_pointers_ruled_out         = false
computed_or_encoded_code_pointers_ruled_out             = false
runtime_computed_carrier_pointers_ruled_out             = false
runtime_copied_or_encoded_carrier_pointers_ruled_out    = false
generic_function_pointer_stores_copies_ruled_out        = false
indirect_entry_into_carriers_ruled_out                  = false
global_runtime_derived_4330_alias_surface_complete      = false
manager_374_join_to_hdvehicle_4330_complete             = false
last_literal_0x004b86cf_rejected                        = false
p1_3_control_producer_complete                          = false
external_provider_count                                 = 7
```

## Remaining frontier

This result does not cover other section bases, transformed/delta chains, runtime-populated tables, cross-block arithmetic, runtime patching, opaque helper returns or copied pointers.

The next useful P1B step is to bound another transformed table/base class or cross-block memory-derived reconstruction, then classify any positive runtime pointer store/copy sink.

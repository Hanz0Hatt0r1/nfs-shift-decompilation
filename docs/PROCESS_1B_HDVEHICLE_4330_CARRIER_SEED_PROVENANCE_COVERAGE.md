# Process 1B — HDVehicle+0x4330 carrier seed provenance coverage

`SHIFT.P1B.HDVehicle4330CarrierSeedProvenanceCoverage/1` composes four already-bounded ways an exact canonical P1B carrier address could become a runtime function-pointer seed on PC retail 1.02.

## Closed bounded seed classes

| Class | Bounded surface | Exact carrier hits |
| --- | ---: | ---: |
| Static/source-visible materialization | 4 subclasses | 0 |
| Canonical computed/loader entry publication | 3 subclasses | 0 |
| Bounded runtime callback registration | 8 surfaces / 51 physical callsites / 36 entrypoints | 0 |
| Exact preferred-imagebase + exact carrier-RVA immediate synthesis | 2,847,850 decoded instructions, 16-carrier superset | 0 |

The static/source-visible aggregate already covers 22,416 vtable slots, 55,066 static-table records, all 8,801,792 retail file bytes for absolute VA/RVA literals, and 40 exact Ghidra carrier-symbol occurrences. None materializes any of the 15 canonical P1B carrier addresses.

The computed-entry aggregate covers canonical CALL-next/POP EIP capture, x87 saved-EIP extraction and PE loader-published entries. None yields a canonical P1B carrier.

Runtime callback coverage `/4` now includes eight bounded callback families, including `_qsort` and `_bsearch`, with 51 physical callback-capable callsites and 36 possible callback entrypoints. None intersects the P1B carrier set.

The P1A immediate construction closure scans a 16-carrier superset. It observes zero exact carrier-RVA scalar uses anywhere in 2,847,850 decoded instructions, therefore it also excludes exact `0x00400000 + carrier RVA` immediate synthesis for the 15-carrier P1B subset.

## Adjudication

The known bounded seed provenance surface is composed and contains zero exact P1B carrier hits.

This does **not** close split/table-derived RVAs, delayed consumers of a stored module base, encoded/XORed arithmetic, runtime-generated/copied pointers, runtime patching or opaque indirect dispatch. Therefore global `runtime_generated_or_copied_function_pointers_ruled_out`, `computed_or_encoded_code_pointers_ruled_out`, `indirect_entry_into_carriers_ruled_out`, manager identity and P1.3 gates remain fail-closed.

Provider count remains 7.

# Process 1B — materialized `+0x374` EBP-relative spill/reload probe

## Blocker

Merged `SHIFT.P1B.Manager374MaterializedPlus374WriterProbe/1` covers exact

```text
lea addr,[receiver+0x374]
[optional GPR MOV copies]
write/RMW [addr]
```

inside one straight-line region. It deliberately leaves memory spill/reload of the materialized address open. That class can hide a later writer even when the original address register is no longer live.

This successor bounds the smallest such class: exact `MOV` spill/reload through an unchanged **EBP-relative memory cell** before the next control boundary.

## Authority

The executable path accepted by the analyzer is SHA-locked to PC retail 1.02:

```text
eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

No committed retail result is fabricated. The analyzer is ready for authoritative execution when the raw executable is available.

## Exact tracked grammar

The probe tracks only:

1. `lea addr,[receiver+0x374]` with one 32-bit GPR receiver and no index;
2. exact GPR `mov` copies of that address;
3. `mov [ebp+/-imm],tracked_reg` or `mov [ebp],tracked_reg`;
4. exact reload `mov reg,[ebp+/-same_imm]`;
5. exact GPR copies after reload;
6. a first-memory-operand zero-displacement dereference `[reloaded_reg]`.

Only dereferences whose provenance has crossed at least one EBP-relative reload are reported as this successor's new candidates. Direct/copy-only dereferences remain predecessor coverage and are intentionally not counted again.

The term "EBP-relative cell" is syntactic. This contract does **not** infer that EBP is a canonical compiler frame pointer or that the cell is semantically a stack local. It proves only equality of the unchanged EBP-relative effective address within the bounded straight-line region.

## Fail-closed invalidation

- any control transfer clears all register and EBP-cell state;
- any explicit EBP write invalidates all tracked EBP-relative cells;
- an overwrite of a tracked EBP-relative cell with an untracked value kills that cell;
- full and partial tracked-register writes kill exact address provenance;
- selected implicit x86 GPR clobbers are modeled conservatively;
- `lock`/`rep*` prefixes are normalized before mnemonic classification.

An explicit write/RMW mnemonic allowlist is used for recovered `[reg]` destinations. Other first-memory-operand dereferences are emitted separately and remain fail-closed.

## Deliberate limits

Not covered here:

- ESP-relative spill/reload or ESP normalization;
- implicit push/pop transport;
- EBP-relative state across CFG edges;
- arbitrary non-stack/non-EBP memory storage of the materialized pointer;
- helper return values;
- indexed LEA;
- arithmetic reconstruction of `receiver+0x374`;
- runtime mutation or generated code.

A recovered `receiver_register` is only syntactic provenance. A numeric `+0x374` offset does not establish Participants Manager identity.

## Gate effect

The only positive subset gate is:

```text
materialized_plus_374_ebp_spill_reload_subset_complete = true
```

The following remain false:

```text
ebp_reload_write_candidate_receivers_classified
computed_plus_374_address_writer_surface_complete
unknown_or_unrelated_manager_root_alias_surface_complete
global_helper_non_vtable_indirect_setter_surface_complete
global_manager_root_origin_surface_complete
manager_374_join_to_hdvehicle_4330_complete
last_literal_0x004b86cf_rejected
p1_3_control_producer_complete
```

External provider count remains `7`.

## Next step

Run the probe on authoritative PC retail 1.02 `SHIFT.exe`. Classify only positive reload-derived write receivers. Extend another carrier class only if the retail result leaves a concrete survivor; otherwise compose this negative subset into the bounded `manager+0x374` setter frontier without promoting global identity gates.

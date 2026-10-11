# Process 1B — materialized `+0x374` EBP-relative spill/reload probe

## Blocker

Merged `SHIFT.P1B.Manager374MaterializedPlus374WriterProbe/1` covers exact

```text
lea addr,[receiver+0x374]
[optional GPR MOV copies]
write/RMW [addr]
```

inside one straight-line region. It deliberately leaves memory spill/reload of the materialized address open. This successor bounds the smallest such class: exact `MOV` spill/reload through an unchanged **EBP-relative memory cell** before the next control boundary.

## Authority

The analyzer accepts only PC retail 1.02 `SHIFT.exe` with SHA-256:

```text
eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

No retail result is fabricated when the raw executable is unavailable.

## Exact tracked grammar

The probe tracks only:

1. `lea addr,[receiver+0x374]` with one 32-bit GPR receiver and no index;
2. exact full 32-bit GPR `mov` copies of that address;
3. `mov [ebp+/-imm],tracked_32bit_gpr` or `mov [ebp],tracked_32bit_gpr`;
4. exact reload into a full 32-bit GPR from the same EBP-relative cell;
5. exact full-GPR copies after reload;
6. a first-memory-operand zero-displacement dereference `[reloaded_reg]`.

Partial registers (`AL/AH/AX`, `BL/BH/BX`, `CL/CH/CX`, `DL/DH/DX`, `SI/DI/BP/SP`) never establish or preserve pointer provenance. They are clobber-only for their 32-bit parent register.

Only dereferences whose provenance crossed at least one EBP-relative reload are reported as new candidates. Direct/copy-only dereferences remain predecessor coverage and are not counted again.

`EBP-relative cell` is a syntactic statement only. The contract does not infer a canonical compiler frame pointer or semantic stack-local identity; it requires only the same unchanged EBP-relative effective address inside the bounded straight-line region.

## Fail-closed invalidation

- any control transfer clears register and EBP-cell state;
- any explicit EBP write invalidates all tracked EBP-relative cells;
- any unmodeled EBP-relative write/RMW invalidates **all** tracked EBP-relative cells conservatively;
- exact tracked full-GPR `MOV` spill first invalidates older cells, then installs the new tracked cell;
- this whole-cell invalidation intentionally avoids unsound byte/word overlap assumptions;
- full and partial tracked-register writes kill exact address provenance;
- selected implicit x86 GPR clobbers are modeled conservatively;
- `lock`/`rep*` prefixes are normalized before mnemonic classification.

An explicit write/RMW mnemonic allowlist is used for recovered `[reg]` destinations. Other first-memory-operand dereferences are emitted separately and remain fail-closed.

## Deliberate limits

Not covered here:

- ESP-relative spill/reload or ESP normalization;
- implicit push/pop transport;
- EBP-relative state across CFG edges;
- arbitrary non-EBP memory storage of the materialized pointer;
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

Run the probe on authoritative PC retail 1.02 `SHIFT.exe`. Classify only positive reload-derived write receivers. Extend another carrier class only if retail evidence leaves a concrete survivor; otherwise compose the negative subset into the bounded `manager+0x374` setter frontier without promoting global identity gates.

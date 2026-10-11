# Process 1B — materialized `+0x374` normalized ESP spill/reload probe

## Blocker

Merged Process 1B coverage now includes direct materialized `receiver+0x374` writes and the conservative EBP-relative MOV spill/reload subset. A separate carrier remains open when the exact materialized address is persisted through an ESP-relative cell whose textual displacement changes as ESP is adjusted.

This probe closes only the bounded straight-line form:

```text
lea addr,[receiver+0x374]
mov DWORD PTR [esp+off1],addr
[exact add/sub esp,imm or lea esp,[esp+/-imm]]
mov reg,DWORD PTR [esp+off2]   ; same normalized logical DWORD cell
write/RMW [reg]
```

## Authority

The executable path is accepted only when SHA-256 equals PC retail 1.02:

```text
eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

No retail result is committed or inferred while the raw executable is unavailable.

## Exact stack coordinate model

The analyzer keeps an abstract `sp_position`, initially zero for each straight-line region.

- `sub esp,N` changes `sp_position -= N`;
- `add esp,N` changes `sp_position += N`;
- `lea esp,[esp+N]` changes `sp_position += N`;
- an ESP-relative cell `[esp+off]` is keyed as `sp_position + off`.

Therefore a store at `[esp+0x8]`, followed by `sub esp,0x10`, is the same logical address as a reload from `[esp+0x18]`.

Only immediate adjustments are normalized. Arbitrary ESP writes are barriers and start a fresh stack generation after clearing tracked cells.

## Pointer transport grammar

- materialization destination must be a full 32-bit GPR other than ESP;
- spill/reload memory width must be exactly DWORD;
- GPR copies must use full 32-bit registers;
- candidate dereferences are exact zero-displacement `[reg]` operands after at least one successful ESP reload;
- XCHG is checked in both memory operand positions; ordinary destination-write/RMW instructions require the tracked memory operand in destination position;
- read-only dereferences are emitted separately instead of being treated as writes.

## Cell alias safety

Tracked ESP cells are 4-byte ranges, not scalar offset labels. Every exact DWORD store invalidates any tracked DWORD cell whose byte range overlaps the new store before optional new provenance is installed. An adjacent store at `+4` is non-overlapping; stores shifted by 1–3 bytes overlap and invalidate.

Any ESP-relative memory reference outside the exact DWORD two-operand MOV spill/reload grammar clears tracked ESP-cell state conservatively. This avoids incomplete width/opcode alias reasoning.

## Fail-closed barriers

This subset deliberately does not normalize:

- push/pop/pushf/popf/pusha/popa;
- enter/leave;
- arbitrary register-sized or masked ESP rewrites;
- CFG stack-state merges or branch carry;
- non-ESP memory storage of the materialized pointer;
- helper-returned pointers;
- indexed `receiver+0x374` construction;
- arithmetic pointer reconstruction;
- runtime mutation or generated code.

Control transfers clear all pointer/cell state. Partial-register destinations and selected implicit x86 clobbers kill tracked GPR pointer provenance.

`receiver_register` remains syntactic provenance only. Numeric `+0x374` equality does not establish Participants Manager identity.

## Gate effect

Only the bounded subset gate is true:

```text
materialized_plus_374_esp_spill_reload_normalized_subset_complete = true
```

The following remain fail-closed:

```text
esp_reload_write_candidate_receivers_classified
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

Run the probe against authoritative PC retail 1.02 `SHIFT.exe`. Classify only positive normalized ESP reload-derived writers. Extend another carrier class only when that retail evidence leaves a concrete survivor; otherwise compose this negative subset into the bounded `manager+0x374` setter frontier without promoting global identity gates.

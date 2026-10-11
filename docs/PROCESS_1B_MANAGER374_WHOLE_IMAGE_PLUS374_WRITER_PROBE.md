# Process 1B: whole-image `+0x374` writer probe

## Blocker

P1.3B still cannot complete the exact `manager+0x374 -> HDVehicle+0x4330` identity adjudication because independent/opaque manager-root origins and helper/non-vtable setter paths remain fail-closed.

The useful finite reduction is not another generic manager-root alias scan. Any surviving unknown root matters only if machine code can write through a receiver-relative `+0x374` target. This probe inventories that syntactic machine surface across the full retail image.

## Probe

`tools/ghidra/analyze_p1b_manager374_whole_image_plus374_writers.py` is SHA-locked to authoritative PC retail 1.02 `SHIFT.exe`.

It scans GNU objdump Intel syntax and records every instruction whose first memory operand:

- has an exact positive `+0x374` displacement;
- contains at least one 32-bit GPR base/index;
- uses an explicit write/RMW mnemonic allowlist.

Every other first-memory-operand mnemonic with the same exact displacement is reported separately instead of being guessed as a write.

This catches direct forms such as:

- `mov [ecx+0x374], eax`;
- `add [esi+edx*4+0x374], 1`.

It intentionally does not treat neighboring offsets (`+0x1374`, `-0x374`) as hits.

## Gate effect

The probe can establish a complete *syntactic candidate inventory* for exact `+0x374` write/RMW forms after it is run on the pinned executable. It does **not** establish Participants Manager receiver identity.

These remain fail-closed:

- `all_plus_374_candidate_receivers_classified`;
- `unknown_or_unrelated_manager_root_alias_surface_complete`;
- `global_helper_non_vtable_indirect_setter_surface_complete`;
- `global_manager_root_origin_surface_complete`;
- `manager_374_join_to_hdvehicle_4330_complete`;
- final `0x004b86cf` / slot2 rejection;
- aggregate P1.3.

Provider count remains 7.

## Limits

Computed-address stores such as `lea eax,[ecx+0x374]` followed later by `mov [eax],...` are not part of this syntactic displacement class. Runtime receiver identity, opaque external memory, generated/self-modifying code and arbitrary process mutation also remain outside this proof.

## Next

Run the probe on authoritative retail `SHIFT.exe`. Classify each positive `+0x374` write candidate receiver against the Participants Manager root. Only surviving manager-root-capable sites should be followed into the final identity join and slot2 adjudication.

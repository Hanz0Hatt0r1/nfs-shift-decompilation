# Process 1A / P1.3A — single-TOP secondary-operand inventory

## Scope

This pass partitions the 2,686 `single_top_only` callback-slot memory-use sites after the congruence refinement. It identifies a concrete source of remaining imprecision: two-GPR memory expressions where the original may-state has one `TOP` operand but does not represent the other GPR in at least one observation.

It is an inventory contract only. Missing state is not interpreted as an arbitrary runtime value and no callback alias is ruled out by this pass.

## Retail result

Authority: PC retail 1.02 `SHIFT.exe`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

- single-TOP sites: 2,686
- one-GPR address expressions: 1,564
- two-GPR address expressions: 1,122
- two-GPR sites with an absent secondary operand in at least one may-state observation: 1,095
- two-GPR sites with the secondary operand represented in every observation: 27
- observations belonging to the 1,095 absent-secondary sites: 2,405
- unique expressions in that class: 331

Missing-secondary register site counts: EAX 293, EDX 265, ECX 232, ESI 106, EBX 81, EDI 81, EBP 37. The most common TOP side is EDI (311 sites), followed by EAX (262), EBX (217), ESI (203), ECX (87), and EDX (15).

Leading instruction classes in this frontier are MOV 474, CMP 272, LEA 152, FLD 53, FSTP 50, MOVZX 35 and FST 29.

## Gate effect

Promoted only:

- `p13a_fun005ffc50_writable_callback_pair_single_top_secondary_operand_inventory_subset_complete`
- `writable_callback_pair_single_top_two_gpr_secondary_absence_classified`

The secondary-operand frontier is not empty. Single-TOP closure, overall TOP closure, multi-edge/global alias closure, writable-memory/runtime-entry closure, callbacks, slot0/slot1 and aggregate P1.3 remain fail-closed. External provider count remains 7.

## Next

Track the missing secondary GPR for the 1,095 sites with a dedicated bounded provenance/value domain. Keep the 27 fully represented two-GPR sites as a separate small refinement class.

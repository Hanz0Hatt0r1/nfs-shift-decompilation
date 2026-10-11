# Process 1A / P1.3A — callback pair TOP-site inventory

## Scope

This pass classifies the complete static `TOP` memory-use frontier emitted by `SHIFT.P1A.P13AFun005ffc50WritableCallbackPairMayStateWideningFrontier/1` on PC retail 1.02 `SHIFT.exe` (`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`).

It does not try to prove a widened site irrelevant. Instead it records which static instructions depend directly on one or more `TOP` registers versus sites where the abstract evaluator returned `TOP` only because finite candidate combinations exceeded the cap.

## Retail inventory

- 2,793 static `TOP` memory-use sites
- 6,401 abstract-state observations of those sites
- 893 unique memory expressions

Static site classes:

- 2,686 `single_top_only`
- 90 `mixed_single_top_and_finite_overflow`
- 15 `contains_two_top`
- 2 `finite_combination_overflow_only`

Unique static sites touched by each `TOP` register:

- ESI: 751
- EAX: 701
- EDI: 550
- ECX: 352
- EBX: 320
- EDX: 111
- EBP: 21

The most common instruction classes are `mov` (1,160 sites), `lea` (630), `cmp` (465), `fstp` (171), and `fld` (158).

## Consequence

The next refinement should begin with the 2,686 single-`TOP` sites: they have only one widened register per observed expression and therefore admit a provenance-preserving replacement for unconstrained `TOP` without immediately requiring relational reasoning between multiple widened registers.

A separate conservative modular-reachability experiment treated `TOP` as any 32-bit value and eliminated **zero** of the 2,793 static sites. Therefore low-bit/address-coefficient reasoning alone is insufficient; origin/provenance information must be retained.

## Adjudication

Promote only:

- `p13a_fun005ffc50_writable_callback_pair_top_site_inventory_subset_complete=true`
- `writable_callback_pair_top_site_frontier_classified=true`

The frontier is not empty and no multi-edge/global alias, writable-memory/runtime-entry, callback, slot0/slot1, or aggregate P1.3 gate is promoted. External provider count remains 7.

## Next step

Refine the 2,686 `single_top_only` sites with provenance-preserving widened value classes. Keep the 90 mixed sites, 15 two-`TOP` sites, and 2 finite-overflow-only sites fail-closed until their own models are implemented.

# Process 1B — Participants Manager root reconstruction coverage

This composition narrows the remaining non-getter Participants Manager root reconstruction frontier after the exact `FUN_00489ad0()` alias surface was closed.

## Closed bounded classes

Three existing machine-level contracts are composed:

- static exact-pointer cells: zero preinitialized pointer cells to `0x00bc9fc0` outside the three known `.text` immediate operands;
- simple same-register arithmetic: 38,128 immediate seeds, 499 arithmetic transitions, zero non-literal exact-root reconstructions;
- constant-only multi-register synthesis: 834 tracked constant arithmetic transitions, zero non-literal exact-root productions.

Together these bounded classes produce no additional Participants Manager root alias and therefore cannot introduce a new `manager+0x374` writer outside the already-closed writer and exact-getter alias surfaces.

## Remaining frontier

This is not a global reconstruction proof. Still open:

- memory-load-derived roots;
- externally initialized or relocated pointer representations;
- opaque helper returns;
- indirect-call-produced roots;
- unrecognized arithmetic/bitwise transforms;
- helper/non-vtable indirect setters reached through those paths.

Accordingly `manager_374_join_to_hdvehicle_4330_complete`, `last_literal_0x004b86cf_rejected`, and aggregate P1.3 remain fail-closed. Provider count remains **7**.

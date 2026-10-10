# Process 1B — render-manager copy/return closure

This composition closes two post-construction exact-root persistence classes for the outer render-manager object stored at `DAT_00bc185c`.

## Machine CFG exact-root copies

The cross-block machine replay starts from 112 direct exact loads of `DAT_00bc185c` and follows exact register identity over reachable intra-function CFG edges. It finds:

- exact-root memory stores: **0**;
- exact-root pushes: **0**;
- unmodelled exact-alias transfers: **0**;
- LEA-derived subobject transitions: **3**.

Therefore the bounded direct exact-global post-construction copy/persistence surface is closed-negative.

## Returned-root residue

Seven functions can conditionally return with the exact outer root still resident in EAX. Their six direct callsites have no pointer consumer before EAX is clobbered. The two table-only callbacks are separately closed by exact table ownership/registration and dispatch provenance; none of their four runtime dispatches persists or consumes the exact EAX residue as a pointer.

Thus the known returned-root consumer surface is closed-negative for persistence or indirect dispatch.

## Remaining frontier

The three LEA-derived paths remain distinct child/subobject identities and are not promoted back to the outer root. Opaque callees, unknown-memory loads, external initialization and helper-created exact-root aliases remain open.

Accordingly `manager+0x374 -> HDVehicle+0x4330`, final `0x004b86cf`, aggregate P1.3 and provider removal remain fail-closed. Provider count remains 7.

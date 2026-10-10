# Process 1B — render-manager derived-subobject closure

## Scope

This aggregate consumes the cross-block exact-root replay plus the two already-merged derived-alias closures for the exact render-manager outer root `DAT_00bc185c`.

The cross-block replay leaves exactly three root-derived LEA transitions:

- `0x0040d83d`: `outer+0x4`;
- `0x00498b93`: `outer+0x780`;
- `0x004995bf`: `outer+0x780`.

## Adjudication

`outer+0x4` is a distinct secondary interface. `FUN_0045ef50` installs vptr `0x00ab55f0` at that address. The complete persisted-interface surface contains no `this-4` reconstruction back to the exact outer root.

`outer+0x780` is a separately constructed subobject. `FUN_00633080` installs vptr `0x00aebdbc`; the runtime item chain can persist and recover the same derived pointer, but never reconstructs `outer = derived-0x780`.

Therefore all three root-derived transitions are closed-negative as sources of a recreated exact outer root. They cannot create a new route to a `manager+0x374` writer by themselves.

## Remaining fail-closed frontier

This does not close exact outer roots created or returned inside opaque callees, external/unknown-origin aliases, opaque helper state, or non-vtable indirect setters. The `manager+0x374 -> HDVehicle+0x4330` identity join, final `0x004b86cf` rejection, aggregate P1.3 completion, and provider removal remain open. Provider count remains 7.

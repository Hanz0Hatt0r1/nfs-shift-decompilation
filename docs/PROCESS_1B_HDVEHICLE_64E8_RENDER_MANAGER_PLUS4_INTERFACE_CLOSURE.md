# Process 1B — render-manager `outer+0x4` interface closure

## Scope

The cross-block exact-root scan leaves three derived LEA transitions. One is persistent: `FUN_0040d6a0` loads the exact render-manager outer root from `0x00bc185c`, forms `outer+0x4`, then stores that pointer in the singleton returned by `FUN_0080bfb0` at `+0x574`.

This slice proves what that persistent derived pointer is used for and whether any consumer reconstructs the exact outer root by subtracting four.

## Exact owner field

`FUN_0080bfb0` returns fixed singleton `0x00c24d80`. An exact-owner scan over direct getter calls finds 26 accesses to `[singleton+0x574]`: one writer, two guard compares and 23 loaded consumers. No consumer performs `pointer-4`, returns the pointer, or stores it to non-stack memory.

One consumer saves it to `[ebp-0x64]` at `0x0081d306`, but keeps the same value in `EDI` and uses it locally as an interface receiver.

## Secondary interface identity

`FUN_0045ef50` installs vptr `0x00ab55f0` at `outer+0x4` (`0x0045ef7e`). The three reached dispatches from the persisted pointer are:

- `0x0050ad2a`, slot `+0x2c` -> `FUN_0045d870`;
- `0x0081d328`, slot `+0x1c` -> `FUN_0045da00`;
- `0x0082357f`, slot `+0x04` -> `FUN_0045d900`.

All three target bodies ignore incoming `ECX` as an owner/root source. None performs `this-4`, stores the incoming interface pointer as a root, or returns the exact outer root. Where manager state is needed, the targets independently call `FUN_00489ad0`.

## Adjudication

The persistent `outer+0x4` secondary-interface alias is closed-negative as an alternate exact outer-root reconstruction path. The two separate `outer+0x780` LEA-derived call paths remain open, as do callee-created/external aliases and two-unknown-origin `HDVehicle+0x4330` provenance.

`manager+0x374 -> HDVehicle+0x4330`, literal `0x004b86cf`, P1.3 completion and provider-count reduction remain fail-closed. Provider count remains 7.

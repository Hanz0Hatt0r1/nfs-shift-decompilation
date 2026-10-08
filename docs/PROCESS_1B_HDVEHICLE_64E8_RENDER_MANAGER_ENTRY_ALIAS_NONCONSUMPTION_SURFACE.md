# Process 1B — render-manager entry-alias non-consumption surface

## Scope

This corrected slice closes four bounded direct targets from the frozen 17-target `SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2` worklist. At each target the exact outer render-manager root `0x00bc185c` is proven to cross the direct CALL boundary in `ECX` or `EDX`; retail machine transfer then shows that value is ignored or overwritten before it can become a persistent exact-root alias.

PC retail 1.02 `SHIFT.exe` machine transfer is authoritative. Ghidra SQLite contributes only navigation/fingerprint support.

## Closed targets

### `0x00449630`

The exact root enters in `EDX` at callsites `0x004be25d`, `0x004bf71b` and `0x004c06e6`. `FUN_00449630` first writes `EDX` at `0x00449639` with `[ebp+0x0c]`; there is no earlier `EDX` read. The root cannot survive the callee entry.

### `0x00459140`

The exact root enters in `ECX` at `0x004d4c87`. Control jumps to `0x0045b51b`, where `ESI` is set to fixed object `0x00bc8e30`, then returns to the loop and executes `mov ecx,esi` at `0x0045915b`. Entry `ECX` is never read.

### `0x0045abe0`

The exact root enters in `ECX` at `0x00498c55` and `0x00499531`. The first instruction calls `FUN_00886980`; this nested helper is only `mov eax,[0x00c29634]; ret` and does not read `ECX`. The caller then executes `lea ecx,[eax+0x78]` at `0x0045abe5`, replacing the root before the tail jump.

### `0x00468ed0`

The exact root enters in `ECX` at `0x004d6015`. Both entry paths kill it before any read: the one-time initialization path writes `ecx=0x00bbc600` at `0x00468ee9`, while the already-initialized path reaches `lea ecx,[ebp-0xa0]` at `0x00468f08`.

## Reopened getter-residue targets

The earlier version of this contract incorrectly treated `0x00489ad0` and `0x00493fb0` as closed merely because they return unrelated singleton pointers in `EAX`.

That is insufficient. On their already-initialized hot paths, both getters can return without overwriting incoming `ECX`. Therefore an exact `ECX=0x00bc185c` arriving at the call boundary can physically survive as caller-visible register residue even though `EAX` contains `0x00bc9fc0` or `0x00bcae00`.

The exact-root callsites to be adjudicated are:

- `0x00489ad0`: `0x004989c6`, `0x00498ac4`;
- `0x00493fb0`: `0x004d1a1f`.

Those getter-like targets are explicitly **open** until their post-call `ECX` use is bounded.

## Worklist transition

Before this corrected slice, ten bounded direct targets remained after the merged opaque-path closures. These four negatives leave six:

```text
0x0045bfc0
0x0045cc50
0x0045db50
0x00462400
0x00489ad0
0x00493fb0
```

A separate 15/17 contract closes the first four and keeps the two getter-residue targets open.

External/unknown-origin exact-root aliases and two-unknown-origin/cross-control-flow `HDVehicle+0x4330` reconstruction remain explicitly open. The manager `+0x374 -> HDVehicle+0x4330` identity join, literal `0x004b86cf`, P1.3 completion and provider removal remain fail-closed. External provider count remains 7.

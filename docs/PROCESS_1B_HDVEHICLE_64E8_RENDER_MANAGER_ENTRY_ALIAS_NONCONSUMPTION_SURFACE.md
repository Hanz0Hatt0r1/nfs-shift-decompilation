# Process 1B — render-manager entry-alias non-consumption surface

## Scope

This slice closes six bounded direct targets from the frozen 17-target `SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2` worklist. At each target the exact outer render-manager root `0x00bc185c` is proven to cross the direct CALL boundary in `ECX` or `EDX`; the retail callee machine transfer then shows that value is ignored, overwritten, or replaced by a distinct pointer before it can become a persistent exact-root alias.

PC retail 1.02 `SHIFT.exe` machine transfer is authoritative. Ghidra SQLite contributes only function names, calling-convention navigation, sizes and mnemonic fingerprints.

## Closed targets

### `0x00449630`

The exact root enters in `EDX` at callsites `0x004be25d`, `0x004bf71b` and `0x004c06e6`. `FUN_00449630` first writes `EDX` at `0x00449639` with `[ebp+0x0c]`; there is no earlier `EDX` read. The root cannot survive the callee entry.

### `0x00459140`

The exact root enters in `ECX` at `0x004d4c87`. Control jumps to `0x0045b51b`, where `ESI` is set to fixed object `0x00bc8e30`, then returns to the loop and executes `mov ecx,esi` at `0x0045915b`. Entry `ECX` is never read.

### `0x0045abe0`

The exact root enters in `ECX` at `0x00498c55` and `0x00499531`. The first instruction calls `FUN_00886980`; this nested helper is only `mov eax,[0x00c29634]; ret` and does not read `ECX`. The caller then executes `lea ecx,[eax+0x78]` at `0x0045abe5`, replacing the root before the tail jump.

### `0x00468ed0`

The exact root enters in `ECX` at `0x004d6015`. Both entry paths kill it before any read: the one-time initialization path writes `ecx=0x00bbc600` at `0x00468ee9`, while the already-initialized path reaches `lea ecx,[ebp-0xa0]` at `0x00468f08`.

### `0x00489ad0`

The exact outer root enters in `ECX` at `0x004989c6` and `0x00498ac4`, but the thunk/body never reads that entry value. It replaces `ECX` with `0x00bc9fc0` and returns `0x00bc9fc0` in `EAX`. That pointer is the independently proven Participants Manager singleton, not `0x00bc185c`; this path therefore does not return or persist the outer render-manager root.

### `0x00493fb0`

The exact outer root enters in `ECX` at `0x004d1a1f`. The thunk/body ignores entry `ECX`, later writes `ecx=0x00bcae00`, and returns `0x00bcae00` in `EAX`. The returned singleton is numerically distinct from `0x00bc185c`, so the outer root is not exported.

## Worklist transition

Before this slice, ten bounded direct targets remained after the merged opaque-path closures. These six negatives leave four:

```text
0x0045bfc0
0x0045cc50
0x0045db50
0x00462400
```

This is only the bounded direct-target opaque-callee frontier. External/unknown-origin exact-root aliases and two-unknown-origin/cross-control-flow `HDVehicle+0x4330` reconstruction remain explicitly open.

The manager `+0x374 -> HDVehicle+0x4330` identity join, literal `0x004b86cf`, P1.3 completion and provider removal remain fail-closed. External provider count remains 7.

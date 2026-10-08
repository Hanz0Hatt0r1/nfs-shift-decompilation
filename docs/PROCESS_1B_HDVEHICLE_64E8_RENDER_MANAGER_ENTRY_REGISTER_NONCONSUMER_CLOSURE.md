# Process 1B — render-manager entry-register nonconsumer closure

## Scope

This bounded slice continues the exact 17-target direct render-manager worklist after the seven opaque targets already closed by the merged Process 1B contracts. It asks only whether four additional target entries can observe, persist, forward, or return the exact outer render-manager root when that value arrives in a caller-saved entry register.

PC retail 1.02 `SHIFT.exe` machine transfer is authoritative. Ghidra data is navigation-only.

## Closed targets

### `0x00459140`

The entry executes `push esi; jmp 0x0045b51b`. The jump target sets `ESI=0x00bc8e30` and returns to the body. No entry `ECX`/`EDX` value is read on that path; `ECX` is later replaced with `ESI` before use. The incoming exact root therefore cannot escape through this target.

### `0x0045abe0`

The first operation is a call to `0x00886980`. That helper is exactly `mov eax,[0x00c29634]; ret` and does not consume `ECX` or `EDX`. The caller then computes `ECX=EAX+0x78` and tail-transfers to `0x00458520`. The tail receiver is helper-derived, not the incoming exact root.

### `0x00489ad0`

This thunk enters through `0x00444fcc`, writes `EAX=1`, and jumps to the singleton-getter body without reading entry `ECX`/`EDX`. The initialization path explicitly overwrites `ECX` with `0x00bc9fc0`; the return path returns `0x00bc9fc0`. That address is the already-proven Participants Manager singleton, not render-manager outer root `0x00bc185c`.

### `0x00493fb0`

This thunk enters through `0x004300ae`, writes `EAX=1`, and jumps to its singleton body without reading entry `ECX`/`EDX`. Its initialization path overwrites `ECX` with `0x00bcae00`, and the return path returns `0x00bcae00`. That value is distinct from `0x00bc185c`.

## Result

These four direct targets are closed-negative as exact render-manager-root persistence/return sources. Together with the seven previously explicit Process 1B closures, **11 of 17** bounded direct targets now have explicit opaque-alias closure.

Six direct targets remain. The global external/unknown-origin and two-unknown-origin `HDVehicle+0x4330` surfaces remain open. The manager `+0x374 -> HDVehicle+0x4330` join, literal `0x004b86cf`, P1.3 completion and provider removal remain fail-closed. Provider count remains 7.

# Process 1B — render-manager forwarded receiver closure

## Scope

This slice closes two additional bounded direct-target paths from `SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2` where the exact render-manager outer root could otherwise survive into an opaque callee chain.

PC retail 1.02 machine transfer is authoritative.

## `0x00458760 -> 0x00476af0`

The thunk at `0x00458760` tail-jumps to `0x00476af0` without changing `ECX`. The body does not read, copy, store or otherwise consume entry `ECX`: it reads stack arguments and globals, then calls `0x00493fb0` at `0x00476b04`. After that call, `0x00476b1a mov ecx,eax` replaces `ECX` with the helper result.

Therefore the exact outer root arriving in `ECX` is not forwarded or persisted by this target.

## `0x0045f980 -> 0x004785f0 -> 0x0045bfc0 -> 0x00d51560`

The thunk at `0x0045f980` reaches `0x004785f0`. The body preserves the exact entry receiver with `0x004785f4 mov esi,ecx`, then destroys exact caller-saved `ECX` identity with the partial write at `0x004785f6`. At `0x00478608` it restores `ECX` from `ESI` and calls `0x0045bfc0`, which tail-jumps to `0x00d51560`.

The leaf captures the exact receiver in `EDI` (`0x00d51561 mov edi,ecx`). Its exact-root uses are only field-base operations at `root+0xc`: the comparison at `0x00d5157f` and load at `0x00d515ec`. The leaf does not store, return, or forward the exact outer root itself. The value loaded from `root+0xc` is a derived field value and is not promoted back to root identity.

## Adjudication

Both named forwarding paths are closed-negative as persistent or returned exact-root sources. The broader opaque-callee surface remains open, as do external/unknown-origin and two-unknown-origin `HDVehicle+0x4330` aliases.

The manager `+0x374 -> HDVehicle+0x4330` join, literal `0x004b86cf`, P1.3 completion, and provider removal remain fail-closed. Provider count remains 7.

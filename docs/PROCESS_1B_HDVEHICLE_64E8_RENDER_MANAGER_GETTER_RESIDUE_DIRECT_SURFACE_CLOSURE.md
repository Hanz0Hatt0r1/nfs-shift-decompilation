# Process 1B — render-manager getter-residue direct surface closure

## Scope

After the 15/17 direct-target closure, the only remaining bounded targets are getter-like `0x00489ad0` and `0x00493fb0`. Their hot paths can physically leave incoming `ECX` unchanged, so they cannot be rejected by an ABI-clobber assumption. This slice instead performs an independent 112-seed machine receiver replay and classifies every exact-root receiver-like callsite plus all post-call residual-ECX paths.

PC retail 1.02 machine transfer is authoritative. Decompiled source is navigation-only.

## Independent receiver inventory

A whole-text replay starts from all 112 exact direct loads of `[0x00bc185c]`, follows direct `jcc/jmp` control flow and exact full-register copies, records direct calls while `ECX`/`EDX` still carries the exact outer root, and applies caller-saved invalidation only **after** the call boundary. No state cap is hit.

The resulting getter inventory is finite:

- `0x00489ad0`: exactly two receiver-like callsites, `0x004989c6` and `0x00498ac4`, both with exact root in `ECX`;
- `0x00493fb0`: exactly one receiver-like callsite, `0x004d1a1f`, with exact root in `ECX`.

## `0x00489ad0`

The getter returns Participants Manager singleton `0x00bc9fc0` in `EAX`, not the outer root `0x00bc185c`. Its initialization branch explicitly overwrites `ECX`; its already-initialized branch may leave incoming `ECX` physically intact.

At `0x004989c6`, post-call code uses only returned `EAX` through manager `+0x374` / optional `+0x100`, then `0x004989e7 mov ecx,esi` destroys residual root before the next call. No post-call read of residual exact-root `ECX` occurs.

At `0x00498ac4`, the same pattern holds; `0x00498ae5 mov ecx,esi` destroys residual root before the next call.

## `0x00493fb0`

This getter returns singleton `0x00bcae00`, not the outer root. Its hot path can preserve incoming `ECX`. The sole exact-root receiver callsite is `0x004d1a1f`.

After the call, `0x004d1a24` tests returned `EAX` state and branches:

- zero branch `0x004d1a2b -> 0x004d1a3f`: residual exact-root `ECX` reaches `0x0045db50`. The same PR's 15/17 contract proves that target stores the pointer in an output local whose first helper dereference is a zero-overwrite before any read, so the original root cannot escape;
- nonzero branch: `0x004d1a2d` calls getter `0x00427470`, which does not read incoming `ECX`; `0x004d1a32 mov ecx,eax` then replaces residual root with singleton `0x00bc6160` before the next call.

Thus all physical residual-ECX paths are closed without relying on ABI assumptions.

## Adjudication

Together with merged #1654/#1655 and the same-PR 15/17 contract, all **17/17** bounded direct targets emitted by `SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2` are explicitly closed-negative as alternate exact outer-root persistence/return paths.

This is not a global unknown-origin closure. External/unknown-origin exact-root aliases and two-unknown-origin/cross-control-flow `HDVehicle+0x4330` reconstruction remain open. The manager `+0x374 -> HDVehicle+0x4330` join, literal `0x004b86cf`, P1.3 completion, and provider removal remain fail-closed. Provider count remains 7.

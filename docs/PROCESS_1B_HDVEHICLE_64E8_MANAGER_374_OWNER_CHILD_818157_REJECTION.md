# Process 1B — manager+0x374 `0x00818157` owner-child rejection

## Scope

This slice closes literal store `0x00818157` without relying on ABI clobber rules. The receiver is joined physically to the already-proven owner+`0x56c` child object with vptr `0x00b16158`.

## Receiver continuity

`FUN_008184e0` and `FUN_008185d0` capture entry `ECX` in `ESI`, call `FUN_00816570`, and then reach the only two direct calls to `FUN_00818000` at `0x0081851f` and `0x0081860f`.

`FUN_00816570` uses the same `ECX` throughout. Its only nested call is `FUN_00816550` at `0x008165c9`. That leaf reads through `ECX` but never writes it, and `FUN_00816570` immediately uses the same register again at `0x008165d1`. After returning to either caller no instruction changes `ECX` before `FUN_00818000`.

Thus the receiver physically reaching `FUN_00818000` is the same owner-child pointer passed into the outer method; this is not an ABI inference.

## Identity

The upstream owner lifecycle already proves that pointer is the object stored at owner+`0x56c`, constructed by `FUN_008167f0` with final vptr `0x00b16158`. That vptr is distinct from both manager root `0x00ab9190` and embedded Participants Manager `0x00ab916c`.

Inside `FUN_00818000`, `EBX` captures the receiver and `ESI` is cleared before:

```text
0x00818157 mov [ebx+0x374],esi
```

The store therefore writes zero to a non-manager object.

## Adjudication

`0x00818157` is closed-negative as a Participants Manager `+0x374` write. Relative to the upstream 8-site literal worklist, seven literal sites remain. Computed-address writer forms and the manager+0x374 -> HDVehicle+0x4330 identity join remain open. Literal `0x004b86cf`, P1.3 and provider removal remain fail-closed; provider count stays 7.

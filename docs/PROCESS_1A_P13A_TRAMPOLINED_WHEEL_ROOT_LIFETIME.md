# Process 1A / P1.3A — trampolined exact wheel-root lifetime

This contract resolves the anti-disassembly control-flow chain around `FUN_007653f0` and `FUN_00760d70` and closes exact wheel-root persistence for that bounded path.

## Control flow

The vehicle receiver is captured by `FUN_007653f0`:

```text
0x007653f1  ESI = ECX
0x007653f3  jmp FUN_00419031
0x00419031  EAX = [ESI+0x824]
0x00419037  jmp FUN_007653f9
```

`FUN_007653f9` materializes all four exact roots `vehicle+0x400/+0xe80/+0x1900/+0x2380` and makes six branch-dependent calls to `FUN_00760d70`.

The root callee has a second trampoline:

```text
0x00760d8a  ESI = ECX        ; exact wheel root
0x00760d8c  jmp FUN_0043dbbd
0x0043dbbd  cmp byte [ESI+0x504],0
0x0043dbc4  jmp FUN_00760d93
```

All six machine fragments are byte-range/SHA-256 pinned. The direct `FUN_007653f0` entry surface is also exhaustively scanned and contains exactly four calls at `0x00765831`, `0x00765944`, `0x00765ae8`, and `0x007712c6`. Existing P1A topology evidence already qualifies the `FUN_00765850` and `FUN_00765aa0` calls as vehicle-root calls, while the global identity composition pins the vehicle address at `0x00c13700`.

## Exact-root lifetime

After `0x00760d8a`, the exact wheel root remains in callee-saved ESI. Across the trampoline and complete `FUN_00760d93` body there are:

- zero stores of bare ESI;
- zero pushes of bare ESI;
- zero copies of bare ESI into another register;
- zero calls with an explicit `ECX = ESI` exact-root receiver.

Ghidra ABI metadata for every directly called target while the root is live is pinned to the supplied SQLite database and uses standard `__thiscall`/`__fastcall` argument locations rather than ESI.

The function does produce derived aliases. `wheel+0x508` is passed to `FUN_007b1790`, `wheel+0x9b0` is used as the `FUN_00753710` receiver, and child pointers `[wheel+0x420]`/`[wheel+0x424]` are loaded repeatedly and passed onward. These are positive derived aliases, not the exact wheel-root value, so they remain open rather than being silently folded into this closure.

## Gate effect

Promoted only:

- `p13a_trampolined_wheel_root_exact_lifetime_subset_complete = true`.

Positive materialization remains recorded, but persistent exact-root escape on this path is false. The following global gates remain fail-closed: reconstructed wheel pointers, runtime-generated selected-wheel pointer stores, derived/stored aliases, callbacks/indirect entry, slot0, slot1, and aggregate P1.3. Provider count remains 7.

Next work is the positive derived-alias surface (`+0x508`, `+0x9b0`, `+0x420`, `+0x424`) and the independent indexed materializer `FUN_00757318`.

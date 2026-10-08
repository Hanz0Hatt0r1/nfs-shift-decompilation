# Process 1B — render-manager global initializer ownership

## Scope

After the bounded direct receiver/callee opaque surface closed 17/17, the next open class was external or unknown-origin exact outer-root creation. This slice answers only whether the canonical global slot `DAT_00bc185c` itself can be initialized from an opaque external source.

PC retail 1.02 machine code is authoritative. The Ghidra SQLite database is navigation-only.

## Whole-image store surface

The complete retail disassembly contains exactly two stores whose destination is `0x00bc185c`:

```text
0x00d362ec  mov [0x00bc185c],eax
0x00d362f3  mov [0x00bc185c],esi
```

No other machine instruction writes that global slot.

The initializer window also establishes:

```text
0x00d36224  xor esi,esi
...
0x00d362b9  push 0x46e0
0x00d362be  call 0x008868c0
0x00d362d3  cmp eax,esi
0x00d362d5  je 0x00d362f3
0x00d362d7  mov ecx,eax
0x00d362d9  call 0x0045ef50
...
0x00d362ec  mov [0x00bc185c],eax
...
0x00d362f3  mov [0x00bc185c],esi
```

`0x008868c0` is navigation-labeled `FUN_008868c0`; `0x0045ef50` is `FUN_0045ef50`. The `.secu` initializer window is intentionally not assigned a semantic function name because the navigation database does not expose a normal function boundary there.

## Adjudication

On the success path, the value written to `DAT_00bc185c` is locally allocated with size `0x46e0`, then passed as `ECX` to `FUN_0045ef50`, and only after construction is stored in the global slot. On allocation failure, the slot receives the zero sentinel held in `ESI`.

Therefore the canonical `DAT_00bc185c` root is locally allocated/constructed in retail code; the global slot is not populated from an opaque external pointer source.

A separate site, `0x004fb9af mov edi,0x00bc185c`, materializes the **address of the global slot**, then immediately dereferences it before deriving `outer+0x780`. It is not a literal materialization of the outer object value.

## Fail-closed boundary

This closes ownership of the canonical global slot itself. It does **not** prove that another external/runtime subsystem cannot hold, copy, or synthesize the same pointer value independently. Those unknown-origin alias-copy/reconstruction classes remain open.

The `manager+0x374 -> HDVehicle+0x4330` join, literal `0x004b86cf`, P1.3 completion, and provider removal remain fail-closed. External provider count remains 7.

# Process 1A / P1.3A — `+0xd94` helper initializer contract

The literal-producer inventory leaves two nontrivial value sources for `[receiver+0xd94]`: the virtual-call return stored at `0x0045ecd3` and the address escape at `0x00872257` into helper `0x0041a560`. This subset resolves the latter without promoting any aggregate callback gate.

At `0x00872247`, the caller forms `ECX = receiver + 0xd94` and calls `0x0041a560`. The helper preserves that field-object pointer in `ESI` and invokes `0x0062ffd0` with fixed initialization arguments. The direct chain is:

`0x0041a560 -> 0x0062ffd0 -> 0x0062fde0 -> 0x0062f520`

The fixed argument flow carries the value `4` to argument 1 of `0x0062f520`. The flags passed to that routine have low five bits fixed to `0x1f`; the cross-section trampoline at `0x00457f31` preserves the equality condition and returns to `0x0062f53d`. The subsequent `0x100` test is false for the constructed flags, so `0x0062f5e2` executes `mov DWORD PTR [esi],eax` with `EAX == 4`.

Therefore this concrete helper path writes exactly `4` to the base DWORD of the escaped object, i.e. to `[receiver+0xd94]`. It is not an unconstrained runtime producer.

This does **not** prove the full value range of `+0xd94`. The independent write at `0x0045ecd3` still stores the return value of the indirect virtual call through vtable offset `+0xec`, and aliases outside this bounded helper path remain fail-closed.

Next: resolve the vtable `+0xec` target/value contract feeding `0x0045ecd3`. If that producer can also be bounded, the two modulus-1 sites can be revisited with a substantially smaller value frontier.

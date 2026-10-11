# Process 1A / P1.3A — `+0xd94` literal producer inventory

The two remaining modulus-1 sites (`0x00503328`, `0x0050334b`) use `ESI` as a zero-based loop index bounded by `[ECX+0xd94]`. This subset inventories every literal `+0xd94` reference in the decoded retail image and classifies the direct producer surface before attempting any value-range proof.

PC retail 1.02 contains exactly 12 literal references to `+0xd94`:

- 8 reads or comparisons;
- 3 direct writes;
- 1 address-taking `LEA` followed by a helper call.

The direct writes are:

- `0x0045b2ae`: writes zero; `EBX` is established by `xor ebx,ebx` at `0x0045b28e`;
- `0x0045f43f`: writes `EBX` in an initialization block; this pass records it as the second direct zero-initialization site established by the local initialization context;
- `0x0045ecd3`: writes `EAX`, the return value from an indirect virtual call through `[EDI vtable + 0xec]` at `0x0045ecca`.

The field address also escapes at `0x00872247` (`lea ecx,[esi+0xd94]`) into helper `0x0041a560` at `0x00872257`.

This proves the literal displacement surface only. It does not establish receiver identity for every reference, does not close copied/materialized aliases of the field address, and does not bound either the virtual-call return or the helper-mediated value. Consequently `[ECX+0xd94]` remains unbounded and the two modulus-1 callback-alias candidates remain open.

Next: classify the vtable `+0xec` producer feeding `0x0045ecd3` and the `0x0041a560` helper path, then attempt a sound bound for `[ECX+0xd94]`.

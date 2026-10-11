# Process 1A / P1.3A — remaining modulo-4/8 allocation provenance

This subset classifies the concrete base/index provenance at the four modulo-4/8 callback-slot candidates that remain after the local induction and zero-guard passes. It deliberately does **not** convert allocator provenance into a negative alias proof.

PC retail 1.02 proves:

- `0x007a6e9e` / `0x007a6ea5`: `ESI` is loaded directly from allocator call `0x008868d0`; requested size is `EDI * 8`; `EBX` is a local zero-based record index.
- `0x007f25a0`: `EBX` is loaded directly from allocator call `0x008868d0`; requested size is `[EBP+8] * 4`; `EDI` is reset to zero and iterates while `EDI < [EBP+8]`.
- `0x0080b696`: `0x008868c0` allocates `(old_count + requested_count) * 8 + 4`; `EDX` becomes the payload base `alloc_return + 4` (or zero on the allocation-failure branch); `EAX` is the zero-based copy index.

Therefore all four remaining modulo-4/8 sites are container/allocation-backed accesses rather than direct static callback-table address formation in their local functions. However, this alone does not prove that allocator returns can never numerically overlap the mapped PE image. The callback slots `0x00b87b7c/0x00b87b80` remain fail-closed until allocator/image-range disjointness is established from an allocator contract, OS address-space evidence, or an authoritative runtime allocation-range capture.

The two remaining modulus-1 sites `0x00503328` and `0x0050334b` are unchanged and still require provenance/range analysis of the runtime count at `[ecx+0xd94]`.

Next: prove address-range disjointness for `0x008868c0/0x008868d0` or capture authoritative runtime heap ranges; independently trace `[ecx+0xd94]` for the two modulus-1 sites.

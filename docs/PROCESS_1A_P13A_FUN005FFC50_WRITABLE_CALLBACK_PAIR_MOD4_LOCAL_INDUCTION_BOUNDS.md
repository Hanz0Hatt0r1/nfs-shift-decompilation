# Process 1A / P1.3A — modulo-4 local induction bounds

This subset follows the modulus-1 local-induction pass and closes four additional target-compatible sites whose primary `EAX` is an explicitly bounded four-byte string-scan counter.

Retail PC 1.02 proves:

- `0x00572951`: `EAX` starts at zero, advances by four, and loops only while `EAX < 0x100`; use range `0..252`.
- `0x00878f82`, `0x00a64930`, `0x00a64e40`: `EAX` starts at zero, advances by four, and loops only while `EAX < 0x400`; use range `0..1020`.
- the non-TOP operand at each site is the previously proven singleton `0x00aa9b60`.
- resulting effective addresses are at most `0x00aa9f5c`, below callback slots `0x00b87b7c/80`.

After composing this with the preceding four modulus-1 exclusions, seven of the original fifteen target-compatible sites remain: `0x00503328`, `0x0050334b`, `0x005d5621`, `0x007a6e9e`, `0x007a6ea5`, `0x007f25a0`, and `0x0080b696`.

This is an exact retail-pattern proof, not general range analysis. Runtime counts, producer provenance, missing-secondary aliases, heap/stack aliases, and aggregate P1.3 gates remain fail-closed.

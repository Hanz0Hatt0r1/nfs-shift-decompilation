# Process 1B — HDVehicle+0x4330 whole-image literal pointer surface

After direct external receiver provenance closes, this P1.3B slice bounds the simplest remaining indirect-entry mechanism: a literal function pointer to one of the 15 exact `HDVehicle+0x4330` carrier entrypoints.

The authoritative PC retail 1.02 executable is scanned byte-for-byte, not only through Ghidra-defined vtables or static-table candidates.

Two encodings are checked for every exact carrier:

- little-endian 32-bit absolute virtual address;
- little-endian 32-bit image-base-relative RVA (`VA - 0x00400000`).

## Result

The complete retail file is **8,801,792 bytes**. Across all 15 exact carriers:

```text
absolute VA literal hits = 0
RVA literal hits         = 0
```

Therefore no retail file byte sequence contains a direct 32-bit absolute address or a direct 32-bit RVA for any exact carrier. This rules out ordinary literal forms such as `mov reg, carrier`, `push carrier`, `mov [slot], carrier`, static absolute callback cells, and simple `image_base + carrier_rva` schemes that retain the RVA as a literal.

Direct `CALL rel32` / `JMP rel32` instructions are intentionally not pointer literals; their displacement is relative to the instruction end and does not encode the target VA or RVA.

## Fail-closed boundary

This does **not** rule out:

- code-relative/EIP-derived address synthesis;
- a pointer computed from transformed constants;
- pointers copied from runtime inputs or returned by another routine;
- encoded pointers decoded at runtime;
- indirect entry whose target cannot be recovered statically.

Accordingly `indirect_entry_into_carriers_ruled_out`, global runtime-derived `+0x4330` alias closure, the `manager+0x374 -> HDVehicle+0x4330` identity join, final `0x004b86cf`, aggregate P1.3 and provider removal remain false. Provider count remains 7.

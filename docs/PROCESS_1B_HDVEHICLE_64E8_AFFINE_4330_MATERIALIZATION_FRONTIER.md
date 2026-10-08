# Process 1B — HDVehicle +0x4330 affine materialization frontier

## Scope

This slice follows the fixed `HDVehicle` root `0x00c13700` into direct PC-retail affine constructions of `root+0x4330`, then bounds the immediate receiver-preserving consumers for possible writes to `+0x21b8` (`HDVehicle+0x64e8`).

The executable is authoritative. The Ghidra SQLite export is used only for navigation and fingerprints.

## Three direct affine materializers

Among exact-root consumers, three direct bodies construct `root+0x4330`:

- `FUN_00769520` at `0x00769551`, passed to `FUN_00756050` at `0x0076955b`.
- `FUN_0076b130` at `0x0076b241`, passed to `FUN_00772200` at `0x0076b247`.
- `FUN_0076df50` at `0x0076e1c1`, then passed to `FUN_007c3b00` three times and to `FUN_0076b280` / `FUN_007618f0`.

## Bounded negative consumers

`FUN_00756050` touches only `+0x2128`, `+0x219c`, and `+0x21a0` under this receiver. It does not access `+0x21b8` and does not forward the exact receiver.

`FUN_00772200` initializes the subobject and does not access `+0x21b8`. Its same-receiver helper `FUN_00771c30` writes only `+0x2364..+0x2374`.

`FUN_0076b280` and `FUN_007618f0` do not directly access `+0x21b8`. Their currently identified exact-parameter consumers also have no direct target access.

`FUN_007c3b00` is different: its direct body reads `+0x21b8` when applying a configuration mode, but does not write it. It also forwards the exact `+0x4330` receiver to parser/helper callees. Those deeper calls must still be classified for computed or derived-alias writes.

## Remaining parser frontier

The following exact-receiver parser descendants remain open for computed/derived alias analysis: `FUN_007715f0`, `FUN_007be420`, `FUN_007c3920`, `FUN_007bf0e0`, `FUN_007bf590`, `FUN_007bfbe0`, `FUN_007bf790`, `FUN_007bf6e0`, `FUN_007c2110`, `FUN_007bf430`, and `FUN_007bf310`.

None of those direct decompiled bodies contains a literal `+0x21b8` access, but that is not enough to exclude writes through a pre-adjusted pointer or another computed alias. Therefore the overall non-literal writer surface remains fail-closed. The last literal candidate `0x004b86cf` is not rejected, and provider count remains 7.

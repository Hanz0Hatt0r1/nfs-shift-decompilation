# Process 1B — HDVehicle +0x4330 affine materialization frontier

## Scope

This slice follows the fixed `HDVehicle` root `0x00c13700` into direct PC-retail affine constructions of `root+0x4330`, then bounds the immediate receiver-preserving consumers for possible writes to `+0x21b8` (`HDVehicle+0x64e8`). The executable is authoritative; Ghidra SQLite is navigation/fingerprint support only.

## Three direct affine materializers

Among exact-root consumers, three direct bodies construct `root+0x4330`: `FUN_00769520` at `0x00769551`, `FUN_0076b130` at `0x0076b241`, and `FUN_0076df50` at `0x0076e1c1`.

The first two pass the subobject to `FUN_00756050` and `FUN_00772200`. The third passes it to `FUN_007c3b00`, `FUN_0076b280`, and `FUN_007618f0`.

## Bounded negative consumers

`FUN_00756050` touches only `+0x2128`, `+0x219c`, and `+0x21a0` and does not forward the exact receiver. `FUN_00772200` does not access `+0x21b8`; its same-receiver helper `FUN_00771c30` writes only `+0x2364..+0x2374`.

`FUN_0076b280` and `FUN_007618f0` do not directly access `+0x21b8`, and their currently identified exact-parameter consumers also have no direct target access.

`FUN_007c3b00` directly reads `+0x21b8` when applying one configuration mode, but it does not write it. It forwards the exact receiver to deeper parser/helper callees, so those computed/derived-alias paths remain explicitly open.

## Remaining frontier

The open exact-receiver parser descendants are `FUN_007715f0`, `FUN_007be420`, `FUN_007c3920`, `FUN_007bf0e0`, `FUN_007bf590`, `FUN_007bfbe0`, `FUN_007bf790`, `FUN_007bf6e0`, `FUN_007c2110`, `FUN_007bf430`, and `FUN_007bf310`.

None of those direct bodies contains a literal `+0x21b8` access, but this contract does not treat that as sufficient to exclude a pre-adjusted pointer write. Full non-literal writer closure, unrelated `manager+0x374` aliases, and rejection of `0x004b86cf` remain fail-closed. Provider count remains 7.

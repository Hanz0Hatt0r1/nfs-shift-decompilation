# Process 1A / P1.3A — `FUN_007572f0` indexed exact wheel-root lifetime

This contract closes exact wheel-root persistence for the split `FUN_007572f0` / `FUN_00757318` wheel-configuration body already identified by the merged same-function topology contract.

## Split entry and materialization

`FUN_007572f0` captures the vehicle receiver in EDI. Configuration selector 0/1 takes the anti-disassembly branch through `0x004066a5`, while other selectors load the sibling configuration field directly. Both paths join at the `0x00757310 -> 0x00757318` thunk.

The body reloads the wheel index from `[EBP+0x8]`, multiplies it by `0xA80`, and at `0x00757348` executes:

```text
EDI = vehicle_root + 0x400 + index*0xA80
```

Thus index 0/1 reproduce the P1.3A roots `HDVehicle+0x400` and `HDVehicle+0xe80`.

## Exact-root lifetime

From `0x00757348` through the complete 2259-byte continuation, the only bare exact-root copy is:

```text
0x00757b55  ECX = EDI
0x00757b87  call FUN_00752fc0
```

There are no bare-root memory stores and no pushes of EDI. `FUN_00752fc0` is a complete 37-byte leaf and performs only FPU reads/writes relative to ECX (`+0x7c8/+0x7d0/+0x7d8/+0x7f0/+0x7e8/+0x5b8`); it never stores, copies, pushes, returns, or further forwards the pointer itself.

The body does create positive interior aliases `wheel+0x610`, `+0x638`, `+0x5e8`, `+0x6a0`, and `+0x6c0`. Those remain separate derived-alias work and are deliberately excluded from the exact-root closure.

## Gate effect

Promoted only:

- `p13a_fun007572f0_indexed_wheel_root_lifetime_subset_complete = true`.

The exact indexed wheel-root materialization remains positive, while persistent exact-root escape on this path is false. Global reconstructed/runtime-generated/stored-alias, callback/indirect-entry, slot0, slot1, and aggregate P1.3 gates remain fail-closed. Provider count remains 7.

Next work is to classify the positive interior aliases and then compose the independent exact-root materializer closures before considering the global runtime-generated selected-wheel pointer-store gate.

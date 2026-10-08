# Process 2 P2.4 — `FUN_00765c40` wheel-pair refresh

This slice internalizes the four-entry pair-state refresh that executes after `FUN_007584f0` and the `+0x407c` positive-load count in the retail `FUN_00765c40` pass.

The destination geometry is exact and repeats every `0x0a80` bytes:

- `+0x0ba0/+0x0ba8`;
- `+0x1620/+0x1628`;
- `+0x20a0/+0x20a8`;
- `+0x2b20/+0x2b28`.

The first lane is fully source-backed. Retail narrows the qwords at `HDVehicle+0x8` and `HDVehicle+0x28` to `float`, clamps each value to `[0,1]`, selects the larger value, multiplies by `100.0f`, and stores the float result widened to double. The same first-lane value is written to all four entries.

The second lane is also common to all four entries, but its value is an x87 `__CIsqrt` result produced before the loop. The source slice does not establish the exact square-root operand strongly enough for Process 2 to synthesize it. The native contract therefore accepts that already-computed finite result explicitly and only owns its four destination writes.

This moves another deterministic portion of the residual pass into native code without changing the top-level provider frontier. `FUN_00765c40` is still not completely internalized; `NativeVehicleExternalProviderBundle.fun_00765c40` remains present and the external-provider count remains seven.

# Process 1B: Massive thread callback wrapper

`FUN_0061cdf0` is an application-owned runtime callback wrapper layered on top of a fixed `CreateThread` entrypoint.

The pinned SQLite callgraph has exactly two direct callers:

- `FUN_0060b54e @ 0x0060b6e5`
- `FUN_0061a780 @ 0x0061a7ce`

The pinned Ghidra source resolves their callback arguments to:

- `FUN_0060b457` for `"Massive Shutdown"`
- `FUN_0061d300` for `"Massive DNS"`

`FUN_0061cdf0` allocates an 8-byte record, stores the callback in `record[0]` and its argument in `record[1]`, then starts fixed `lpStartAddress_0061cd93`. The thread entry executes the stored callback as `(*(code*)record[0])(record[1])` and frees the record.

Neither concrete callback (`0x0060b457`, `0x0061d300`) nor the fixed thread start (`0x0061cd93`) belongs to the canonical 15-function P1B exact `HDVehicle+0x4330` carrier set.

This closes only this internal wrapper. Other application-owned callback wrappers, generic function-pointer stores/copies, computed/encoded pointers and unresolved indirect dispatch remain open. Therefore global runtime-callback and indirect-entry gates remain fail-closed and provider count stays 7.

# Process 1B: P1.3 computed-forwarding integration frontier

The six computed destination/receiver paths left by `SHIFT.HDVehicle64e8Manager374SourceOnlyForwardingBatch/1` are now partially integrated under the current shard ownership.

Closed-negative handoffs already present on `main`:

- P1.3B `0x0070f62d` via `SHIFT.HDVehicle64e8Manager374P13B0070f62dVptrRejection/1`;
- P1.3B `0x005f6eda` via `SHIFT.HDVehicle64e8Manager374P13B005f6edaReceiverRejection/1`;
- P1.3D `0x0070fb45` and `0x0070fdeb` via `SHIFT.P1D.P13D.B04524ComputedReceiverRejections/1`.

Therefore the aggregate computed forwarding frontier is reduced from six sites to exactly two:

- `0x005292db`;
- `0x005f4ffa`.

Both remaining sites belong to Process 1A / P1.3A. Process 1B remains the integration owner but does not take over those proofs or infer their result.

The known positive exact-manager writer remains `FUN_00d60660`, which stores a selected allocator-owned `manager+0x2a0` entry into `manager+0x374`. That selected-entry domain is already disjoint from fixed `HDVehicle+0x4330`. However, the global `manager+0x374 -> HDVehicle+0x4330` identity join cannot be promoted until the final two computed forwarding paths are closed.

Accordingly, aggregate computed closure, the manager/HDVehicle join, final `0x004b86cf` / slot2 adjudication, P1.3 completion, and provider removal all remain fail-closed. Provider count remains 7.

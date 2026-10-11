# Process 1B: P1.3 computed-forwarding integration closure

The six computed destination/receiver paths left by `SHIFT.HDVehicle64e8Manager374SourceOnlyForwardingBatch/1` are now fully integrated under the current P1.3 shard ownership.

## Consumed shard handoffs

All six sites are closed-negative on authoritative PC retail 1.02:

- P1.3A `0x005292db` via `SHIFT.HDVehicle64e8Manager374P13A005292dbReceiverRejection/1`;
- P1.3A `0x005f4ffa` via `SHIFT.HDVehicle64e8Manager374P13A005f4ffaReceiverRejection/1`;
- P1.3B `0x005f6eda` via `SHIFT.HDVehicle64e8Manager374P13B005f6edaReceiverRejection/1`;
- P1.3B `0x0070f62d` via `SHIFT.HDVehicle64e8Manager374P13B0070f62dVptrRejection/1`;
- P1.3D `0x0070fb45` and `0x0070fdeb` via `SHIFT.P1D.P13D.B04524ComputedReceiverRejections/1`.

The aggregate computed-forwarding frontier is therefore reduced from six sites to **zero**. This agrees with `SHIFT.P1B.Manager374ComputedRuntimeClosure/1`, which independently reports six of six receiver/destination forwarding paths closed and zero remaining computed runtime paths.

## Gate effect

Promoted only within this finite subfrontier:

```text
p1_3a_computed_forwarding_complete = true
p1_3b_computed_forwarding_complete = true
p1_3d_computed_forwarding_complete = true
aggregate_computed_forwarding_complete = true
remaining_site_count = 0
```

The known positive exact-manager writer remains `FUN_00d60660`, whose value domain is an allocator-owned `manager+0x2a0` selected entry rather than fixed `HDVehicle+0x4330`.

This closure does **not** prove the global manager/HDVehicle identity. The exact getter-derived storage/stack alias surface and canonical Participants lifecycle are already bounded separately, but unrelated/unknown manager-root origins and the global helper/non-vtable setter surface remain fail-closed.

Therefore these gates stay false:

```text
manager_374_join_to_hdvehicle_4330_complete
last_literal_0x004b86cf_rejected
p1_3_control_producer_complete
```

Provider count remains **7**. No identity is inferred from matching numeric offsets.

## Next

Compose the zero computed-forwarding frontier with `SHIFT.P1B.Manager374ExactRootAliasClosure/1` and `SHIFT.P1B.Manager374ParticipantsLifecycleClosure/1`. Close the remaining unrelated/unknown manager-root and global helper/non-vtable setter classes; then perform the final `manager+0x374 -> HDVehicle+0x4330` identity adjudication and `0x004b86cf` / slot2 rejection.

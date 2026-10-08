# Process 1B — bound the known `manager+0x20` helper surface

## Blocker

After the direct root/vtable/literal/bulk-copy writer surfaces for `manager+0x374` were exhausted, one explicitly excluded adjusted receiver remained easy to root: `FUN_00489ad0()+0x20`.

## Exact owner

The PC-retail constructor `FUN_00488dc0` initializes the embedded subobject at `manager+0x20` with `FUN_00647a10` and then names it through:

```text
FUN_00647820(manager+0x20, "Participants Manager")
```

For this adjusted receiver, `manager+0x374` would be subobject-relative `+0x354`.

## Setup calls

`FUN_0040e630` contains the bounded setup sequence:

```text
0x0040e83a  call FUN_00489ad0
0x0040e846  call FUN_00648890 with receiver manager+0x20

0x0040e84b  call FUN_00489ad0
0x0040e855  call FUN_00647800 with receiver manager+0x20
```

The corresponding direct helper writes are all far below subobject `+0x354`:

- `FUN_00648890`: `+0x15c`, `+0x34`, `+0x35`, `+0x158`;
- `FUN_00648730`, called on the same receiver: conditional `+0x30`;
- `FUN_00647800`: `+0x35`.

Normalized to the manager root, these are `+0x17c`, `+0x54`, `+0x55`, `+0x178`, and `+0x50`. None is `manager+0x374`.

## Important positive escape

The adjusted pointer is not dead after setup. Both helper paths register the same `manager+0x20` pointer through `FUN_004f5e60`:

```text
FUN_00648730 -> FUN_004f5e60(FUN_0065bf80()+0x24, manager+0x20)
FUN_00648890 -> FUN_004f5e60(FUN_0065bf80()+0x44, manager+0x20)
```

Therefore the direct setup writes are rejected as the `manager+0x374` producer, but the escaped alias path remains live and must be traced through later registry consumers/dispatch.

## Result

This closes only the immediate adjusted-receiver setup/helper writes. It does not close the escaped alias, computed-offset, or non-vtable indirect surfaces, does not join `manager+0x374` to `HDVehicle+0x4330`, and does not change the external provider count of 7.

## Next step

Trace consumers/removers/dispatch of the two `FUN_004f5e60` registry insertions and test whether any later operation writes `manager+0x20+0x354 == manager+0x374`. Do not reopen the already exhausted direct root/vtable/bulk-copy scans.

# Process 2 P2.4 — `FUN_007bf790` caster record materialization

## BLOCKER

`SHIFT.Fun00769640TrigSourceWriter/1` owns the final writer arithmetic for the trig-source qwords at `HDVehicle+0x0738/+0x11b8`, but its selected record inputs at `+0x54b8..+0x551c` were still supplied as six already-materialized values.

Retail source and machine code show that records 12 and 13 are the left/right caster records created by `FUN_007bf790` through `FUN_007c5a20`.

## SOURCE AUTHORITY

PC retail `SHIFT.exe` SHA-256:

`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`

Decompiler source SHA-256:

`512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

Exact machine spans:

- selected left/right caster calls `0x007bf983..0x007bf9d3`, 80 bytes, SHA-256 `12049fc9876432475c2ee2b34705372173dd2e6aec68842a42141ef3a30ea258`;
- `FUN_007c5a20` record materializer `0x007c5a20..0x007c5aba`, 154 bytes, SHA-256 `cf994c54d1a693fd2a1091fa553cc0da632082e25e3ba549143b9bf8443963f0`.

The source-backed VehicleLoadData fields are:

| side | Range | Setting | destination record |
| --- | --- | --- | --- |
| left | `+0x1e8` `LeftCasterRange` | `+0x3d8` `LeftCasterSetting` | `(HDVehicle+0x4330)+0x1188` |
| right | `+0x200` `RightCasterRange` | `+0x3e0` `RightCasterSetting` | `(HDVehicle+0x4330)+0x11d8` |

The destination fields consumed later by `FUN_00769640` are therefore the already-proven absolute triples `+0x54b8/+0x54c0/+0x54cc` and `+0x5508/+0x5510/+0x551c`.

## RECOVERED MATERIALIZATION

For one caster record, `FUN_007c5a20`:

1. copies `Range[0]` to record base and `Range[1]` to record slope;
2. evaluates `Range[1]^2 + Range[0]^2 + Range[2]^2` in retail component order;
3. when that value is positive, obtains `count = FUN_00901310(Range[2])` and multiplies base/slope by `0.017453292519943295`;
4. obtains requested index `FUN_00901310(Setting)`;
5. clamps it to `[0, count-1]`, with `count < 1` forcing zero.

A zero-length Range is a subtle case: machine code does not rewrite `record+0x10`. The native contract therefore takes `prior_count` explicitly instead of inventing an initialization value.

`FUN_007bf790` calls the left record before the right record, so the conversion-boundary observation order is preserved.

## INTEGER CONVERSION BOUNDARY

`FUN_00901310` is intentionally **not** replaced by `std::round`, a cast, or another guessed rule. Existing repository evidence already proves that this function contains environment-dependent x87 conversion branches and has not promoted a single rounding semantic.

The new materializer accepts a typed integer-conversion callback. It owns all source-visible arithmetic and clamping around that callback, while the callback remains the explicit machine boundary.

## OUTPUT

`SHIFT.Fun007bf790CasterRecordMaterialization/1` now turns typed left/right caster config inputs into the exact `{base, slope, coefficient}` inputs consumed by `SHIFT.Fun00769640TrigSourceWriter/1`.

This removes six opaque table scalars from the P2.4 frontier and replaces them with four source-backed caster config fields plus one already-known conversion boundary.

## LIMITS

This slice does not yet claim:

- native lifetime/acquisition of `LeftCasterRange/Setting` or `RightCasterRange/Setting`;
- native ownership of `FUN_00901310` conversion semantics;
- ownership of the unrelated `record+0x18` mirror side effect controlled by `DAT_00c1c560`.

Therefore `FUN_007584f0_computed_payloads` remains incomplete, no residual-producer promotion bit is set, top-level `FUN_00765c40` remains present, the lower scene query remains external, and provider count stays **7**.

## NEXT STEP

Bind the four caster config fields to authoritative native VehicleLoadData/session state. Keep `FUN_00901310` as a typed boundary until its environment-dependent conversion behavior has a separate proof suitable for promotion.

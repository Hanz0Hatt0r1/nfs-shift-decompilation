# Process 2 P2.4 — `FUN_007bf790` VehicleLoadData caster binding

## BLOCKER

The caster materializer is native, including `FUN_00901310` value conversion, but it still accepted four already-extracted caster values. Phase738 already proves the owner chain `HDVehicle+0x66b4 -> VehicleLoadData*`, while `SHIFT.VehicleCDFRuntime/1` pins the exact caster destination offsets.

This slice closes the byte-to-typed-value binding without claiming ownership of the VehicleLoadData lifetime itself.

## SOURCE AUTHORITY

PC retail `SHIFT.exe` SHA-256:

`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`

Upstream contracts:

- `SHIFT.Fun007618f0VehicleLoadDataOwnership/1`: `VehicleLoadData* = *(HDVehicle+0x66b4)`, allocation size `0x3848`, constructor `FUN_007c3170`;
- `SHIFT.VehicleCDFRuntime/1`: source-backed suspension parser layout;
- `SHIFT.Fun007bf790CasterRecordMaterialization/1`: native caster record construction;
- `SHIFT.Fun00901310Cvttsd2si/1`: native integer value conversion.

The selected BMW resource identity remains `vehicles\\physics\\chassis\\bmw_m3_e36.cdf`, decoded SHA-256 `bbee83f0d2fdcbfc2bbd62ddb2a10bf6fed71bb1b4fa78f303a4730d038b970d`. This slice does not invent numeric caster values from that resource.

## BOUND LAYOUT

The VehicleLoadData snapshot fields are:

```text
LeftCasterRange   +0x1e8  +0x1f0  +0x1f8   f64 x3
LeftCasterSetting +0x3d8                    f64
RightCasterRange  +0x200  +0x208  +0x210   f64 x3
RightCasterSetting+0x3e0                    f64
```

The minimum byte image needed is therefore `0x3e8` bytes.

## OUTPUT

`SHIFT.Fun007bf790VehicleLoadDataCasterBinding/1` accepts a byte-backed VehicleLoadData snapshot and explicit prior record counts. It:

- reads each retail f64 field using explicit little-endian byte assembly;
- avoids unaligned pointer reinterpret-casts;
- does not depend on host endianness;
- validates the typed caster values;
- builds `Fun007bf790CasterPairInput`;
- can compose directly into the already-native caster materializer and `FUN_00901310` value path.

The former four opaque caster scalar/vector inputs are therefore replaced by one source-backed VehicleLoadData snapshot boundary.

## FAIL-CLOSED BEHAVIOR

The binding rejects:

- null snapshot storage;
- snapshots shorter than `0x3e8`;
- non-finite caster source values.

Zero-range prior-count behavior remains explicit exactly as required by `FUN_007c5a20`.

## LIMITS

This slice does not yet own:

- the actual `HDVehicle+0x66b4` pointer dereference in the native vehicle session;
- VehicleLoadData snapshot allocation/lifetime;
- native decoding of the retail CDF/BFF resource;
- selected BMW caster numeric values.

Accordingly the positive-qword producer family is still incomplete, `FUN_007584f0_computed_payloads` remains on the residual frontier, no promotion bit is set, top-level `FUN_00765c40` remains present, the lower scene query remains external, and provider count stays **7**.

## NEXT STEP

Wire the authoritative VehicleLoadData snapshot into `NativeVehicleProviderSession`, or separately source-back the selected BMW caster values from the pinned retail CDF. Do not promote resource numeric values without exact decoded-resource evidence.

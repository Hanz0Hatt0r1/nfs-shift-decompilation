# Process 2 P2.4 — `FUN_007c5a20` selected trig-record materializer

## BLOCKER

`SHIFT.Fun00769640TrigSourceWriter/1` owns the arithmetic that writes `HDVehicle+0x0738/+0x11b8`, but it still accepted three already-materialized table fields for records 12 and 13: base qword, slope qword, and current index.

Retail `FUN_007c5a20` is the common materializer for those record fields. The two selected call sites are in `FUN_007bf790`.

## SOURCE AUTHORITY

Retail executable SHA-256:

`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`

Exact `FUN_007c5a20` machine span:

`0x007c5a20..0x007c5ab8`, 152 bytes, SHA-256
`46a5c431c573c83d21c64e135c884f40521cbbbd74724706479fb3541f184713`.

The two selected `FUN_007bf790` call sites are covered by:

`0x007bf983..0x007bf9d3`, 80 bytes, SHA-256
`12049fc9876432475c2ee2b34705372173dd2e6aec68842a42141ef3a30ea258`.

## SELECTED SOURCE GEOMETRY

`FUN_007c3b00` receives `HDVehicle+0x4330` as its destination table. It invokes `FUN_007bf790` with that pointer while the `FUN_007bf790` receiver is the load object subobject rooted at:

```text
*(HDVehicle+0x66b4) + 0x0fe8
```

The two records consumed later by `FUN_00769640` come from:

| loop | load-object source vec3 | load-object selector | table record from `HDVehicle+0x4330` | absolute table base |
| --- | --- | --- | --- | --- |
| 0 | `+0x11d0` | `+0x13c0` | `+0x1188` | `HDVehicle+0x54b8` |
| 1 | `+0x11e8` | `+0x13c8` | `+0x11d8` | `HDVehicle+0x5508` |

Both selected calls use the double constant at `0x00b09258`, equal to `0.017453292519943295`.

## MATERIALIZER SEMANTICS

The source vec3 is kept positional:

```text
[source_base, source_slope, source_count]
```

Retail always copies source base/slope first. It then evaluates:

```text
source_base^2 + source_slope^2 + source_count^2 > 0
```

When true:

```text
count = trunc_toward_zero(source_count)
base  = source_base  * 0.017453292519943295
slope = source_slope * 0.017453292519943295
```

When false, the destination count is not overwritten. The native contract therefore accepts `previous_count` explicitly instead of assuming zero initialization.

The selector qword is converted to integer and clamped exactly by the observed branch structure:

```text
count < 1       -> 0
selector < 0    -> 0
selector >= count -> count - 1
otherwise       -> selector
```

The resulting base, slope, and selected index are exactly the fields used downstream by `SHIFT.Fun00769640TrigSourceWriter/1`.

## OUTPUT

`SHIFT.Fun007c5a20TrigRecordMaterializer/1` internalizes:

- selected record call geometry;
- base/slope copy and scale;
- count refresh on nonzero source;
- previous-count preservation on zero source;
- valid-domain integer conversion;
- selector clamping;
- handoff to the already-native `FUN_00769640` writer.

## LIMITS

This slice does **not** yet own the load-object values themselves. The pointer provenance is known, but the source vec3 values at `+0x11d0/+0x11e8` and selectors at `+0x13c0/+0x13c8` still require writer/lifetime ownership.

Therefore `FUN_007c5a20` and `FUN_007bf790` are not globally complete, the positive-qword producer family remains incomplete, `FUN_007584f0_computed_payloads` remains on the residual frontier, top-level `FUN_00765c40` remains present, lower scene query remains external, and external provider count remains **7**.

## NEXT STEP

Trace the selected load-object source vec3/selector writers. The downstream chain from those four source regions through table materialization, trig-source writer, x87 trig bridge, vector construction, final ratio reduction, and persistent writes is now explicit.

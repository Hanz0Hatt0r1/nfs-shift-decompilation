# Process 2 P2.4 — `FUN_007584f0` trig boundary

## BLOCKER

After native A/B/C vector construction, the A vector still receives precomputed `cosine_f32` and `sine_f32` values. Retail does not consume the wheel `+0x738` qword directly as a trigonometric argument: it first narrows that qword to f32, reloads the same f32 value, calls cosine and then sine wrappers, and stores each wrapper result back to f32.

## SOURCE AUTHORITY

Retail executable SHA-256:

`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`

Caller surface `0x00758560..0x0075858b` is 43 bytes with SHA-256:

`65d14dcffa1b71078029c5675f57374bb9c3f1a2fb46cc5ca25d55f0d765a27f`

It proves:

- source qword `[HDVehicle + loop_index*0x0a80 + 0x0738]`;
- qword → f32 narrowing before either call;
- cosine wrapper `0x00900b10` executes before sine wrapper `0x00900c40`;
- both wrappers consume the same f32 source;
- each result is stored to f32 before the caller later widens it for the BODY transform.

The wrapper spans are also pinned independently:

- cosine `0x00900b10..0x00900bf9`, SHA-256 `0de3a2479ceb44dc4eeb1eba23ab27c53407c3fd7eb2052f7fc9a7df1790dbbd`;
- sine `0x00900c40..0x00900d29`, SHA-256 `cae7003b4b9682164685955c7aa4c877b523f3ed0a72844b3b0c1d71312fb81f`.

Both wrappers contain FP-environment checks and an `FPREM1` range-reduction fallback around their `FCOS`/`FSIN` core instruction.

## OUTPUT

`SHIFT.Fun007584f0TrigBoundary/1` owns only the caller-visible boundary:

- source qword finite validation;
- exact f64→f32 narrowing;
- one cosine call followed by one sine call;
- reuse of the same f32 source;
- finite f32 results handed to `SHIFT.Fun007584f0PositiveQwordVectorConstruction/1`.

The wrapper implementations are explicit callbacks. This prevents a host `std::cos/std::sin` implementation from being silently treated as retail-equivalent.

## LIMITS

This slice does **not** internalize:

- the cosine wrapper implementation;
- the sine wrapper implementation;
- CRT/x87 FP-environment handling;
- `FPREM1` range fallback behavior;
- acquisition/lifetime ownership for the HDVehicle `+0x738` source.

Therefore the positive-qword producer family remains incomplete, `FUN_007584f0_computed_payloads` remains on the P2.4 frontier, no producer promotion bit is set, the top-level `FUN_00765c40` provider remains present, and external provider count remains **7**.

## NEXT STEP

Either prove a source-equivalent native implementation of the two x87 wrappers, including the relevant valid-domain/FP-environment contract, or keep those two math operations as explicit lower boundaries while moving the positional HDVehicle/BODY source reads into authoritative native session state.

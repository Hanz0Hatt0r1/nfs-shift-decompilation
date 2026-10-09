# Process 2 P2.4 — `FUN_007584f0` positive-qword trig bridge

## BLOCKER

`SHIFT.Fun007584f0PositiveQwordVectorConstruction/1` owns the A/B/C vector arithmetic, but A still accepted precomputed `cosine_f32` and `sine_f32` values.

The retail trig sequence is now recovered directly from the pinned PC executable and can reuse the already-native Phase748 x87 `FCOS`/`FSIN` implementation.

## SOURCE AUTHORITY

Retail executable SHA-256:

`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`

The exact trig span is `0x00758560..0x0075858b`, 43 bytes, SHA-256:

`65d14dcffa1b71078029c5675f57374bb9c3f1a2fb46cc5ca25d55f0d765a27f`

For each `loop_index in {0,1}`, retail reads:

```text
HDVehicle + loop_index*0x0a80 + 0x0738
```

so the two absolute source offsets are `HDVehicle+0x0738` and `HDVehicle+0x11b8`.

The machine sequence is:

1. load source qword;
2. explicitly spill to f32;
3. reload that f32 and call `0x00900b10` (`FCOS`) at `0x0075856f`;
4. spill cosine to f32;
5. reload the same source f32 and call `0x00900c40` (`FSIN`) at `0x00758580`;
6. spill sine to f32.

## NATIVE REUSE

Phase748 already proves and implements the wrappers used here:

- `fun_00713630_retail_cos_f32()` executes x87 `FCOS` under retail control word `0x027f` and spills to f32;
- `fun_00713630_retail_sin_f32()` executes x87 `FSIN` under the same control word and spills to f32.

`SHIFT.Fun007584f0PositiveQwordTrig/1` therefore owns only the source-visible bridge around those already-proven primitives: f64-to-f32 narrowing, retail call order `FCOS -> FSIN`, and the two f32 results passed into vector construction.

The deterministic `0.25f` witness reuses Phase748 parity:

```text
angle   = 0x3e800000
cosine  = 0x3f780aa5
sine    = 0x3e7d5777
```

## IMPORTANT OWNERSHIP DISTINCTION

This source is **not** `Fun00765c40LoadTerms`.

`Fun00765c40LoadTerms` comes from the wheel array rooted at `HDVehicle+0x400`, so its first two absolute fields are `+0x0b38` and `+0x15b8`. The trig source is rooted directly at `HDVehicle`, producing `+0x0738` and `+0x11b8`.

The retail writer for the trig source is `FUN_00769640`; that producer is not internalized by this slice.

## LIMITS

This slice does **not** claim native acquisition of the `+0x0738/+0x11b8` source qwords or complete ownership of the other positional wheel/BODY values consumed by vector construction.

Therefore:

- the trig arithmetic boundary is internalized;
- source acquisition remains explicit;
- the positive-qword producer family is not complete;
- `FUN_007584f0_computed_payloads` remains on the P2.4 frontier;
- no residual-producer promotion bit is set;
- top-level `FUN_00765c40` remains present;
- lower scene query remains external;
- external provider count remains **7**.

## NEXT STEP

Bind authoritative native source acquisition for the remaining positional inputs, starting with the `FUN_00769640` writer for `HDVehicle+0x0738/+0x11b8` and reusing existing native BODY-frame state where ownership is already proven.

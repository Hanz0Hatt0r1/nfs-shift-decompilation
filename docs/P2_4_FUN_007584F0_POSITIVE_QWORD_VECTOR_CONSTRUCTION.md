# Process 2 P2.4 — `FUN_007584f0` positive-qword vector construction

## BLOCKER

`SHIFT.Fun007584f0PositiveQwordReduction/1` owns the final retail ratio `dot(A,B)/dot(A,C)`, but A/B/C were still explicit precomputed vec3 values.

Direct analysis of the exact PC-retail `SHIFT.exe` now recovers the arithmetic that constructs those three positional vectors.

## SOURCE AUTHORITY

Retail executable SHA-256:

`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`

Two caller spans are pinned:

- axis-transform setup `0x0075850c..0x0075853c`, 48 bytes, SHA-256 `2f8a8303545bad3b90e57c80dcac011a78d6370dc0cc1e044e44d114b2842925`;
- loop vector construction `0x0075858b..0x007586f9`, 366 bytes, SHA-256 `e261e763d2d493ad9f3f59242b4a7ee5d90a066ff5b59fafba8aad56a06dc270`.

The called helper implementations are independently pinned as exact machine spans for vec3 add (`0x00753590`), scale (`0x007535f0`), cross (`0x00753650`) and BODY-frame transform (`0x007aefb0`).

## RECOVERED POSITIONAL CONSTRUCTION

For each loop index `i in {0,1}`, with `esi = HDVehicle + i*0xa80`:

```text
axis = transform(body_frame, [1, 0, 0])
A    = transform(body_frame, [0, cosine_f32, sine_f32])

first_sum =
    vec_8a0 * (scalar_818 + global_b09138)
  + vec_888 * ((i == 0 ? global_aa9afc_f32 : 1) * global_aadd68)

second_sum =
    vec_888 * scalar_7e8
  + vec_8a0 * scalar_7f0
  + vec_8d0 * load_b38

B = cross(first_sum, second_sum) + vec_8d0 * scalar_900_f32
C = cross(vec_8a0 * global_b03df8, axis)
```

The BODY transform uses the exact `FUN_007aefb0` row accumulation order `1,0,2`.

## OUTPUT

`SHIFT.Fun007584f0PositiveQwordVectorConstruction/1` owns the recovered vector arithmetic and produces `Fun007584f0PositiveQwordReductionInput{A,B,C}` directly for the already-native final reduction.

All source names remain positional/address-derived. No physical interpretation is assigned to `+0x8a0`, `+0x888`, `+0x8d0`, the scalar offsets, or the four globals.

## LIMITS

This slice intentionally does **not** claim:

- native acquisition/lifetime ownership for the HDVehicle/BODY source fields;
- reimplementation of x87 cosine/sine wrappers `0x00900b10/0x00900c40`;
- semantic physical names for the source values;
- complete positive-qword producer ownership.

The f32-rounded cosine and sine values are explicit inputs, matching the caller after the wrapper results are stored to float and widened again.

Therefore `FUN_007584f0_computed_payloads` remains on the P2.4 frontier, residual producer promotion remains unauthorized, the top-level `FUN_00765c40` provider remains present, and external provider count remains **7**.

## NEXT STEP

Bind the positional source reads to active native HDVehicle/BODY session state and recover the exact f32 cosine/sine wrapper behavior or a source-equivalent native path. Once those inputs are native-owned, the two positive-load qword producers can be completed end-to-end.

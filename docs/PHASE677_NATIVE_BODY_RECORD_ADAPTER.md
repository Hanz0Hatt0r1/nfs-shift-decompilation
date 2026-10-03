# Phase 677 — native raw BODY record adapter

Phase 677 bridges the typed Phase 674/676 BODY integrator to the source-backed
retail BODY storage layout.  The new path accepts a contiguous byte buffer of
`FUN_007b2270` BODY records, decodes only proven producer fields, runs the
already ported integration core, and writes back only fields that
`FUN_007bab70` is proven to mutate.

No original game execution or new runtime capture is used.

## Source-backed record layout

The existing BODY ABI/static contracts establish:

- BODY stride: `0x170` bytes;
- `origin`: f64x3 at `+0x00/+0x08/+0x10`;
- `cross_vector`: f64x3 at `+0x18/+0x20/+0x28`;
- `prepared_vector`: f64x3 at `+0x30/+0x38/+0x40`;
- accumulator A: f64x3 at `+0x48/+0x50/+0x58`;
- accumulator B: f64x3 at `+0x60/+0x68/+0x70`;
- `motion_triplet`: f64x3 at `+0x78/+0x80/+0x88`;
- scalar producer at `+0x90`: f64;
- symmetric tensor: f32x9 at `+0xb0..+0xd0`;
- basis: f32x9 at `+0xd4..+0xf4`;
- reciprocal coefficients: f64x3 at `+0x138/+0x140/+0x148`.

The adapter uses explicit little-endian bit assembly for f32/f64.  It does not
reinterpret an unpacked C++ struct as the retail object.

## Native API

`shift_body_record_adapter.hpp` adds:

```text
BodyRecordBytes decode/apply boundary
execute_fun_007b2270_body_buffer_with_basis_callback(...)
```

The buffer executor requires:

```text
body_bytes.size() == body_count * 0x170
```

and rejects multiplication overflow before computing the required size.

For every record, in ascending source-array order:

```text
raw 0x170 BODY record
  -> decode proven producer lanes
  -> FUN_007bab70 pre-basis arithmetic
  -> mandatory external FUN_007afdd0 basis provider
  -> FUN_007bab70 post-basis arithmetic
  -> write proven persistent lanes
  -> next record
```

The Phase 676 provider boundary remains mandatory and external, so Phase 677
still does not invent the arithmetic or precision behavior of `FUN_007afdd0`.

## Exact writer mask

The adapter writes only:

- origin (`+0x00..+0x17`);
- cross vector (`+0x18..+0x2f`);
- prepared vector (`+0x30..+0x47`);
- motion triplet (`+0x78..+0x8f`);
- symmetric tensor (`+0xb0..+0xd3`);
- basis (`+0xd4..+0xf7`).

This is 168 bytes total.  Every byte outside that mask is copied unchanged from
the input record.  In particular accumulator A/B, scalar `+0x90`, reciprocal
coefficients, unknown/intermediate fields, and record tail bytes are not
rewritten by this adapter.

## Fail-closed behavior

The native path rejects:

- missing basis provider;
- non-finite timestep;
- byte-size/body-count mismatch;
- body-count multiplication overflow;
- NaN/Inf in every consumed f64/f32 producer lane;
- NaN/Inf in every writer lane before serialization.

A non-finite raw BODY producer is rejected before the external basis provider is
called.

## Reference oracle and tests

`src/physics/body_record_adapter_runtime.py` is the reference byte-layout codec.
It independently freezes:

- exact little-endian offsets and widths;
- exact `0x170` record size;
- exact 168-byte writer mask;
- buffer/record boundary checks;
- preservation of all unrelated bytes;
- non-finite rejection.

Regression coverage:

- `tests/test_body_record_adapter_runtime.py`;
- `native_runtime/tests/body_record_adapter_check.cpp`;
- CTest target `shift_runtime_body_record_adapter`;
- `.github/workflows/native-physics-phase677.yml`.

The native fixture uses two adjacent records with different sentinel fill bytes,
verifies callback order and deterministic state results, and then checks every
non-writer byte against the original record.

## Scope

This phase closes a storage/integration boundary needed for persistent native
vehicle state:

```text
source-backed BODY bytes
  -> typed native integration
  -> source-backed BODY bytes
```

It does not prove:

- `FUN_007afdd0` arithmetic parity;
- full `FUN_00765470` orchestration parity;
- `FUN_00770e80` rendered-frame cadence;
- vehicle ownership or scene bootstrap.

Those remain separate evidence-gated boundaries.

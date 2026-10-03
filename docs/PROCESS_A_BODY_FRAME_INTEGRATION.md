# Process A — BODY frame integration boundary

This document records the static writer bridge recovered from the retail
`SHIFT.exe.c` decompile and corroborated directly against the matching x86 PE.
It supersedes the earlier Process B statement that the transition from BODY
accumulators into persistent motion/pose had no identified writer.

Evidence identity:

- `SHIFT.exe` MD5: `705af8b420e5eb1e3834ac43d5533c6b`;
- `SHIFT.exe.c` SHA256: `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`;
- no game execution;
- no runtime capture.

The machine-readable contract is
`src/physics/body_frame_integration_static.py` with format
`SHIFT.BodyFrameIntegrationStatic/1`.

## Proven scheduling path

`FUN_00770e80` performs two `FUN_0076d100` passes. After each pass it calls
`FUN_00765470` with half of the outer timestep (`0.5` is the f64 constant at
`0x00aa9a20`), then calls `FUN_007b8810`.

```text
FUN_00770e80
  -> FUN_0076d100
  -> FUN_00765470(0.5 * dt)
  -> FUN_007b8810
  -> FUN_0076d100
  -> FUN_00765470(0.5 * dt)
  -> FUN_007b8810
```

Inside `FUN_00765470` the relevant ordering is:

```text
0x007657b2 -> FUN_00763570
0x007657bd -> FUN_007b3f40
0x007657c8 -> FUN_007b4110
...
0x0076582a -> FUN_007b2270
```

This establishes that the BODY integration loop executes after the SDF solve and
post-solve accumulator feedback inside each half-step boundary.

## BODY array topology

`FUN_007b2270` is a direct, compact array loop:

- count: owner `+0x10`;
- body-array pointer: owner `+0x14`;
- BODY stride: `0x170` bytes;
- each element receives the same f64 timestep;
- each element is passed to `FUN_007bab70`.

The exact retail bytes for `0x007b2270..0x007b22a9` have SHA256
`e4e1b6ae89ba26017f9ac5a29e8043d6335899c9dc4b0789c62f2c9208b6a639`.

This closes the previously uncertain connection between the physics-system BODY
array and the persistent integration primitive.

## `FUN_007bab70`: proven persistent BODY integration

The exact retail function bytes at `0x007bab70..0x007bac53` have SHA256
`097bcfc9b1fd8127a14c7808c2c39cb680924354f3cb6e5672517ab1af20179f`.

The following storage relationships are direct source/machine-code facts.
Names below describe the already established structural lanes rather than
introducing retail method names.

### Translation lane

For `dt = param_1`:

```text
BODY +0x00/+0x08/+0x10 += dt * BODY +0x78/+0x80/+0x88
```

Therefore the previously read-only `origin` lane now has a proven persistent
writer, and the `motion_triplet` is directly the rate integrated into it.

The same primitive then performs:

```text
scale = BODY[+0x90] * dt
BODY +0x78/+0x80/+0x88 += scale * BODY +0x60/+0x68/+0x70
```

This closes the previously missing `accumulator_b -> motion_triplet` bridge.
The physical name/unit of scalar `+0x90` is intentionally not promoted here;
only its multiplicative role is proven.

### Basis / rotational lane

The primitive forms:

```text
rotation_increment = dt * BODY +0x18/+0x20/+0x28
FUN_007afdd0(BODY +0xd4, rotation_increment)
```

`FUN_007afdd0` normalizes a non-zero input vector, uses its magnitude in
sine/cosine construction, forms a 3x3 rotation, and multiplies the existing
`+0xd4..+0xf4` basis by it. Thus the `cross_vector` is a proven incremental
rotation-rate input to the persistent basis writer.

The primitive also performs:

```text
BODY +0x30/+0x38/+0x40 += dt * BODY +0x48/+0x50/+0x58
FUN_007ba630(BODY)
BODY +0x18/+0x20/+0x28 =
    matrix(BODY +0xb0..) * vector(BODY +0x30/+0x38/+0x40)
```

The final relationship needed machine-code corroboration because the decompiler
assigned `FUN_007ba630` a `void` signature even though its caller relies on EAX
surviving that call:

```text
0x007bac12  lea  eax,[esi+0x30]
0x007bac36  call FUN_007ba630
0x007bac3c  push eax
0x007bac3d  lea  ecx,[esi+0xb0]
0x007bac43  call FUN_007aefb0
```

The exact `FUN_007ba630` function bytes
(`0x007ba630..0x007ba7de`, SHA256
`4d7c11507756faf8213747d354ff9ab30ec1162693286afb69de241718f9080c`)
do not write EAX. Therefore the vector argument forwarded to
`FUN_007aefb0` is still `BODY+0x30`, while the output pointer prepared by the
caller is `BODY+0x18`.

`FUN_007aefb0` itself is the source/machine-code-backed 3x3 f32 matrix times
f64x3 vector operation; its exact bytes at `0x007aefb0..0x007af003` hash to
`76c52235cce08d3ec131d43e1b62cda623ac8528944e44f902846a0a71b14f29`.

This closes both:

```text
accumulator_a -> prepared_vector
prepared_vector -> cross_vector
cross_vector -> basis
```

without guessing a retail class or method name.

## Persistent graph now closed

For the already reconstructed solver/contact lanes, the static graph now has a
continuous writer path:

```text
wheel/contact contributions
  -> BODY +0x48..+0x70 accumulators
  -> FUN_007b3f40 solve
  -> FUN_007b4110 post-solve feedback
  -> FUN_007b2270 BODY-array loop
  -> FUN_007bab70
       +0x60..+0x70 -> +0x78..+0x88 -> origin +0x00..+0x10
       +0x48..+0x58 -> +0x30..+0x40 -> +0x18..+0x28 -> basis +0xd4..+0xf4
```

This is the persistent state-evolution bridge that was missing from the earlier
BODY writer frontier.

## Other state writers are lifecycle/reset paths

Static review also found direct writers to the same lanes outside the normal
half-step integration chain:

- `FUN_0076ef10` iterates the BODY array at `owner+0x14`, stride `0x170`, zeros
  `+0x78/+0x80/+0x88`, calls `FUN_007bbb60` to zero `+0x18/+0x20/+0x28`, and
  clears accumulator-related vehicle storage. Its caller context is reset-like,
  not the recovered normal integration loop.
- `FUN_00770a90` iterates the same BODY array and assigns
  `+0x78/+0x80/+0x88` from an input vector, then calls `FUN_007bbb60` with a
  zero vector. Its observed callers are state/setup transitions, not the
  `FUN_00770e80` half-step path.
- `FUN_007b8630` can restore BODY origin and clear motion/accumulator lanes when
  the system-location validation path fails. This is a recovery path, not the
  normal integrator.
- `FUN_007b7840` is a broader model/body state setter capable of writing origin,
  basis, motion and cross-vector state under explicit flags; it is not used as
  the normal `FUN_00770e80` integration primitive.

These functions are useful lifecycle evidence, but they are kept separate from
the frame-evolution path.

## Verify the retail binary offline

No Ghidra rerun is required to verify the exact functions above. Given the retail
`SHIFT.exe`:

```bash
python3 tools/ghidra/verify_body_frame_integration_binary.py \
  /path/to/SHIFT.exe \
  --json-out out/body_frame_integration_binary_verification.json
```

The verifier fails closed on executable-MD5 mismatch, PE mapping failure, or any
function-byte hash mismatch.

Generate the machine-readable static contract with:

```bash
python3 src/physics/body_frame_integration_static.py \
  --json-out out/body_frame_integration_static.json
```

## Remaining static unknowns

This result deliberately does not prove:

- retail semantic names/classes for `FUN_00765470`, `FUN_007b2270`, or
  `FUN_007bab70`;
- a stronger physical unit/name for BODY `+0x90` than its observed scale role;
- that `FUN_00770e80` is called exactly once per rendered frame;
- targets of the two unresolved indirect calls in `FUN_007b3f40`;
- higher-level input/control ownership before the recovered vehicle update
  boundary.

Those remain separate static-analysis frontiers. No Linux runtime implementation
is changed by this contract.

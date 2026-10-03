# Process B — BODY persistent-state ABI and writer frontier

This document freezes the current static/runtime ABI evidence needed to continue
vehicle physics without inventing the missing pose integrator.  The original game
was not launched for this work.  Evidence is composed from the current `main`, the
recovered retail source/machine-code contracts, existing Phase documents, and the
already ported solver/contact primitives.

The machine-readable contract is `SHIFT.BodyPersistentStateABI/1` in
`src/physics/body_persistent_state_abi_runtime.py`.

## Main result

The repository now proves several persistent BODY accumulator writers, including a
direct wheel BODY-compatible state writer, but it still does **not** prove the
function that advances chassis BODY origin/orientation or the `+0x78/+0x80/+0x88`
motion triplet between simulation ticks.

This distinction is important.  The six `FUN_007b4110` feedback lanes are persistent
across fixed steps, but persistence alone is not evidence that they alias the
read-side motion/pose lanes.

## BODY layout — proven storage lanes

| Lane | Offsets | Proven use | Proven writers | Evidence | Writer status |
|---|---|---|---|---|---|
| origin | `+0x00/+0x08/+0x10` | world-point origin; `body.position` in solver projection | none indexed | source-backed read side | **unresolved** |
| cross vector | `+0x18/+0x20/+0x28` | cross term in `FUN_007537b0`; `body.axis` operand in projection; Phase 663 BODY response source | none indexed | cross-consumer structural | **unresolved** |
| prepared vector | `+0x30/+0x38/+0x40` | transformed/scaled output of `FUN_007ba7e0` | `FUN_007ba7e0` | source-backed | proven |
| accumulator A | `+0x48/+0x50/+0x58` | angular accumulator in BODY contribution code; persistent solver feedback; wheel shared triplet in `FUN_00755f80` | `FUN_007ba9e0`, `FUN_007baa70`, `FUN_007baaf0`, `FUN_007b4110`; wheel-domain `FUN_00755f80` | source-backed, object-domain alias noted | proven for those domains |
| accumulator B | `+0x60/+0x68/+0x70` | linear accumulator; persistent solver feedback | `FUN_007ba9e0`, `FUN_007baa70`, `FUN_007baaf0`, `FUN_007b4110` | source-backed | proven accumulator writer |
| motion triplet | `+0x78/+0x80/+0x88` | machine-code-backed BODY velocity read in `FUN_007682c0`; X/Z speed source in `FUN_007675f0`; translation term in `FUN_007537b0` | none indexed | machine code + cross-consumer read side | **unresolved** |
| symmetric tensor | `+0xb0..+0xd0` | `B*diag(D)*B^T` prepared tensor | `FUN_007ba630` | source-backed | proven |
| basis | `+0xd4..+0xf4` | 3x3 float transform frame used throughout solver/contact/wheel paths | none indexed | source-backed read side | **unresolved** |
| diagonal coefficients | `+0x128/+0x12c/+0x130` | BODY preparation coefficients | `FUN_007ba860` | source-backed | proven |
| reciprocal coefficients | `+0x138/+0x140/+0x148` | double reciprocals of the coefficient inputs | `FUN_007ba860` | source-backed | proven |

The `+0x78` lane has inconsistent historical labels in older contracts
(`correction` in projection-oriented descriptions versus `velocity` in the
machine-code-backed vehicle-rate path).  This process therefore records its
observable roles and offset identity, not a stronger physical unit/semantic claim.

## Confirmed state writers and call boundaries

### `FUN_00755f80` — direct wheel BODY-compatible triplet writer

- address: `0x00755f80`;
- immediate caller: `FUN_00763570`;
- direct transform callees: `FUN_007af0a0`, `FUN_007af010`;
- reads: pose/frame at `+0xd4`, shared triplet at `+0x48/+0x50/+0x58`;
- writes: the same `+0x48/+0x50/+0x58` triplet;
- exact write: `shared_triplet -= reconstructed_transformed_longitudinal_vector`;
- evidence: source-backed, existing Python oracle in
  `wheel_longitudinal_velocity_runtime.py`.

`FUN_00763570` applies this to four objects starting at `vehicle+0x400` with
`0xA80` stride.  This is a real frame-state mutation, but it is **not** evidence
that `+0x48` aliases chassis `+0x78`, and it is not a pose writer.

### `FUN_00758b50` — four-wheel update into BODY accumulator helpers

- address: `0x00758b50`;
- caller: `FUN_0076d100`;
- important callees: `FUN_00755950`, then final `FUN_007baa70` /
  `FUN_007baaf0` applications;
- wheel-state view: `vehicle+0x848 + slot*0xA80`;
- wheel-runtime view: `vehicle+0x400 + slot*0xA80`;
- writes known wheel runtime fields such as `+0x528/+0x530/+0x548` and pair
  destinations, then reaches BODY accumulator helpers.

This closes a proven `wheel state -> BODY accumulator` boundary inside a
`FUN_0076d100` pass.

### `FUN_007675f0` -> `FUN_007ba9e0`

- address: `0x007675f0`;
- source line: `SHIFT.exe.c:759784`;
- reads BODY X/Z motion values from `+0x78/+0x88` for its speed gate;
- downstream recovered helpers include `FUN_00783a30`, `FUN_00759210`,
  `FUN_00759c90`;
- performs two source-visible `FUN_007ba9e0` submissions;
- `FUN_007ba9e0` writes BODY `+0x48..+0x70` from a world-point contribution.

The two world-point/contribution vectors and caller-side scheduling are still
unresolved, so no larger native scheduling claim is made.

### `FUN_00766510` contact-response path

Phase 663 proves the BODY-source response input using `BODY+0xd4` and
`BODY+0x18`.  Phase 664 proves two `FUN_00758fc0` auxiliary records at
`this+0x37d8` and `this+0x3858`, with the first accumulator result carried into
the second.  The auxiliary path reaches `FUN_007baa70` and therefore the
`+0x48..+0x70` accumulator lanes.

The caller ownership/timing of `FUN_00766510`, and the exact primary response
application transform, remain incomplete.

### `FUN_007b4110` post-solve writer

The exact SDF frame remains:

```text
FUN_007b3f40
  -> FUN_007b3ed0
  -> FUN_007bb8d0
  -> FUN_007bc680
  -> FUN_007ba570
  -> FUN_007b2210
  -> provider slot +0x18 or FUN_007b0f20
  -> FUN_007b4110
```

`FUN_007b4110` applies solved JOINT/HINGE/BAR scalars back through
`FUN_007baa70/FUN_007baaf0`, changing `+0x48..+0x70`.  Phases 651–653 prove
that these six lanes persist and feed the next fixed solver step.

No indexed evidence proves a subsequent copy/integration from those six lanes
into `+0x18`, `+0x78`, origin, or basis.

## Vehicle / wheel / spindle / axle topology

Raw disassembly plus `FUN_0076ed60` and Phase 634 establish four component
slots:

| Slot | Component base | wheel BODY ptr | spindle BODY ptr |
|---:|---:|---:|---:|
| FL | `+0x400` | `+0x820` | `+0x824` |
| FR | `+0xe80` | `+0x12a0` | `+0x12a4` |
| RL | `+0x1900` | `+0x1d20` | `+0x1d24` |
| RR | `+0x2380` | `+0x27a0` | `+0x27a4` |

The component-relative BODY fields are `+0x420` (wheel) and `+0x424`
(spindle); slot stride is `0xA80`.  The named rear-axle BODY pointer is
`vehicle+0x2e00`.

Additional arrays/views relevant to this writer frontier:

- wheel state: base `+0x848`, stride `0xA80`, count 4;
- wheel runtime: base `+0x400`, stride `0xA80`, count 4;
- `FUN_00766510` auxiliary records: `+0x37d8`, `+0x3858`, count 2;
- `FUN_00765c40` contact-factor records: count 4, stride `0x150`, previous
  base `+0xa70`, factor base `+0xa78`.

## Outer update ordering

The recovered source proves that `FUN_00770e80` (`SHIFT.exe.c:765608`) executes
two `FUN_0076d100` physics passes (`SHIFT.exe.c:762992`) with half-timestep
helper work between them, then performs per-wheel post-pass work including
`FUN_00755a60` and `FUN_00760b50`.

This makes `FUN_00770e80` / `FUN_0076d100` the highest-priority static frontier
for the missing state-evolution bridge.  It does not by itself prove where the
SDF solver or pose integration occurs inside/around those passes.

## Explicit frame-to-frame graph

```text
input/control
  -?-> vehicle update / FUN_00770e80 frontier
       -> 2 x FUN_0076d100
       -> FUN_00758b50 wheel path --------------------+
       -> contact paths FUN_00765c40/00766510/007675f0|
                                                        v
                                              BODY +0x48..+0x70
                                                        |
                                                        v
       FUN_007bc680 -> FUN_007ba570 -> reset -> solve -> FUN_007b4110
                                                        |
                                                        v
                                              persistent accumulators
                                                        |
                                   UNKNOWN WRITER BRIDGE +------+
                                                        v      |
                                         BODY +0x18 / +0x78     |
                                                        |      |
                                   UNKNOWN POSE INTEGRATION     |
                                                        v      |
                                      origin +0x00 / basis +0xd4
                                                        |
                                                        v
                                   next-frame contact/solver reads
```

The two unknown arrows are the principal Process B blockers.  They are kept
explicit rather than filled with `position += velocity*dt` or guessed quaternion
integration.

## Evidence levels

- **source-backed** — exact recovered source/control-flow/arithmetic exists;
- **machine-code-backed** — instruction stream resolves a decompiler loss or
  establishes the read directly;
- **cross-consumer structural** — multiple exact consumers agree on an offset
  relationship, but the physical name/unit is not promoted;
- **unresolved** — no indexed writer/caller ordering closes the transition.

## Static handoff for the missing writer

Priority addresses for targeted Ghidra callgraph/instruction review are:

```text
00770e80  0076d100  00763570  00755f80
00758b50  00765c40  00766510  007675f0
007b3f40  007b4110  007537b0  00753810
007ba7e0  007ba9e0  007baa70  007baaf0
```

The static review should search callers/callees around these functions for stores
to the unresolved offset groups while preserving pointer provenance.  A raw
`[register+offset]` store is only a candidate until that register is independently
proven to hold the same BODY object.

Particularly valuable evidence would be a function that, in one proven BODY
object domain, reads any of `+0x48..+0x70` and writes `+0x18..+0x28` or
`+0x78..+0x88`, or reads those motion-side lanes and writes origin/basis.

## Native-port gate

No new C++ pose integrator is added here.  Native pose integration remains
fail-closed until the writer ABI and update order are source/machine-code backed.
The existing Python oracles for the proven writers remain the executable reference:

- `wheel_longitudinal_velocity_runtime.py` — `FUN_00755f80` triplet mutation;
- `sdf_body_state_primitives_runtime.py` — `FUN_007ba9e0` point contribution;
- existing post-solve/body-feedback runtimes — `FUN_007b4110` accumulator
  persistence;
- contact/aux-contact runtimes — proven contribution paths into the same
  accumulator domain.

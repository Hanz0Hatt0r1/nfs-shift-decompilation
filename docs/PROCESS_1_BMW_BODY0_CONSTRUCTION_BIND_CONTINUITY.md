# Process 1 — BMW BODY0 construction bind continuity

## Playable-slice blocker reduced

The first playable Linux vertical slice still needs a retail BMW vehicle world
transform.  The remaining transform blocker is `SHIFT.BMWBody0BindFrameProof/1`.

The previous Process 1 stage rejected the resolved-direct `FUN_007b7840`
construction-bind hypothesis and added a machine/p-code STORE discovery pass for
the actual BODY construction lane.  The full saved `SHIFT.exe.c` plus raw IA-32
from the supplied retail executable now closes the next semantic join:

```text
SDF BODY pos/ori
       |
       v
FUN_007b6900 descriptor
       |
       v
FUN_007b3670 / FUN_007bbb10 / FUN_007b00a0
       |
       v
persistent BODY origin + basis
```

The machine-readable contract is:

```text
SHIFT.BMWBody0ConstructionBindContinuity/1
```

implemented by:

```text
tools/ghidra/build_bmw_body0_construction_bind_continuity.py
```

This is a static construction proof.  It does not execute the original game and
requires no new runtime capture.

## Exact BODY descriptor semantics

`FUN_007b6900` parses each `[BODY]` into one local descriptor and passes that
same descriptor to `FUN_007b3670` at direct callsite `0x007b6e8f`.

The audited descriptor layout is now:

| SDF field | BODY descriptor offsets |
| --- | --- |
| `pos` | `+0x00 / +0x08 / +0x10` |
| `rot` | `+0x18 / +0x20 / +0x28` |
| `vel` | `+0x78 / +0x80 / +0x88` |
| `name` | `+0x100` |
| `ori` | `+0x108 / +0x110 / +0x118` |
| `mass` | `+0x120` |
| `inertia` | `+0x128 / +0x12c / +0x130` |

This resolves the deliberately opaque Phase 424 names:

```text
group_a = BODY.ori
group_b = BODY.rot
```

Phase 424 was correct to keep those names opaque before this source/machine
join; the new contract supersedes only that semantic uncertainty.

## `BODY.pos` -> persistent origin

`FUN_007b3670` receives the descriptor and emits three exact qword copies:

```text
descriptor +0x00 -> runtime BODY +0x00
descriptor +0x08 -> runtime BODY +0x08
descriptor +0x10 -> runtime BODY +0x10
```

The retail machine sequence is the block around:

```text
0x007b3797 .. 0x007b37b1
```

and therefore establishes:

```text
SDF BODY.pos == persistent BODY origin at construction time
```

No physical-unit or renderer-frame interpretation is added.

## `BODY.ori` -> persistent basis

`FUN_007b3670` forms `descriptor +0x108` and calls `FUN_007bbb10` at
`0x007b37c8`.

`FUN_007bbb10` copies those three qwords to the BODY orientation cache and then
uses the same source vector to build the persistent 3x3 basis:

```text
0x007bbb21  push BODY.ori pointer
...         ECX = persistent BODY +0xd4
0x007bbb3a  call FUN_007b00a0
```

`FUN_007b00a0` reads the three f64 orientation scalars and writes nine f32
values at:

```text
+0xd4 +0xd8 +0xdc
+0xe0 +0xe4 +0xe8
+0xec +0xf0 +0xf4
```

Its trigonometric imports are independently visible in the retail IA-32:

```text
0x00900c40 -> x87 fsin
0x00900b10 -> x87 fcos
```

The exact direct-call sequence is frozen by the contract and its retail
mnemonic fingerprints.

## Exact-zero orientation shortcut

If the exact decoded BMW SDF proves:

```text
BODY[0].ori = (0, 0, 0)
```

then `FUN_007b00a0` produces the identity 3x3 basis exactly.  The analyzer may
therefore materialize:

```text
BODY0-local -> SDF-model-construction-frame
```

as the row-vector affine matrix whose translation is the exact `BODY[0].pos`.

For non-zero `ori` the current pass intentionally does not replace retail x87
transcendental evaluation with an unvalidated host `sin/cos` implementation.
The resource values may be known while exact basis materialization stays
blocked.

## BMW resource identity gate

The optional `--sdf` input is accepted only when SHA-256 matches the already
measured Phase 404 retail resource:

```text
archive: BMW_M3_E36.bff
archive SHA-256:
  c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70
SDF: vehicles/physics/suspension/aarm_multilink.sdf
SDF SHA-256:
  fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed
BODY count: 11
BODY[0]: body
```

The raw decoded resource is not currently committed to the repository.  Phase
404 intentionally stored only measured hashes and derived topology, so the
current checked-in evidence cannot invent numeric BODY0 `pos/ori` values.

## Remaining frame boundary

The construction proof ends in the **SDF model construction frame**.  Phase 645
uses the **VHF vehicle-root/assembly frame**.  Equality between those frames is
not currently proven.

Therefore the contract always keeps these separate:

```text
BODY0-local -> SDF model frame             construction proof
SDF model frame -> VHF vehicle root        still unknown
BODY0-local -> VHF vehicle root            not ready
```

Even if the exact BODY0 SDF pose is the identity matrix, this pass does not use
that fact to assume the two parent frames are the same.

## Current handoff

With current repository evidence and without the raw decoded SDF:

```text
BODY_descriptor_pos_ori_semantics_ready              = true
construction_origin_continuity_ready                 = true
construction_basis_continuity_ready                  = true
BODY0_resource_pos_ori_values_ready                  = false
BODY0_local_to_SDF_model_bind_pose_ready             = false
SDF_model_to_VHF_vehicle_root_frame_relation_ready   = false
BODY0_bind_frame_proof_ready                         = false
vehicle_world_transform_ready                        = false
```

The remaining direct blockers are now finite:

1. recover the exact already-measured `aarm_multilink.sdf` bytes and extract
   `BODY[0].pos/ori`;
2. prove the static frame relation from the SDF model construction frame to the
   VHF vehicle-root/assembly frame.

The first item is a data-availability problem, not a writer/ABI discovery
problem.  The second is the remaining semantic frame join.

## Run

Without raw SDF, to verify the static continuity only:

```bash
python3 tools/ghidra/build_bmw_body0_construction_bind_continuity.py \
  out/shift_ghidra_database \
  evidence/bmw_m3_e36_physics_intake_phase404.json \
  --json-out out/bmw_body0_construction_bind_continuity.json
```

When the exact decoded SDF is available:

```bash
python3 tools/ghidra/build_bmw_body0_construction_bind_continuity.py \
  out/shift_ghidra_database \
  evidence/bmw_m3_e36_physics_intake_phase404.json \
  --sdf /path/to/vehicles/physics/suspension/aarm_multilink.sdf \
  --json-out out/bmw_body0_construction_bind_continuity.json
```

The pass fails closed on PE identity drift, function mnemonic drift, required
callsite drift, BMW archive/body-order drift, SDF hash drift, malformed numeric
BODY0 vectors, or any attempt to derive a nonzero-orientation basis without the
retail evaluator boundary being explicitly solved.

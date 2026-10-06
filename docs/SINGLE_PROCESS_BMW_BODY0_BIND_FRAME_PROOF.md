# Single-process S3 — positive BMW BODY0 bind-frame proof

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

S3 closes `BMW-BODY0-bind-frame-composition`: the selected-session BMW
BODY0-local frame can now be mapped numerically into the exact canonical BMW VHF
vehicle-root frame.  The next blocker is S4 consumption into the already-built
persistent world-transform/admission path.

## INPUT

Positive contracts already on `main`:

- `SHIFT.BMWBody0VehicleRootBindRelation/1` — source-backed symbolic
  `BODY0-local -> outer-Vehicle-root`, identity rotation and translation
  `-offset33b`;
- `SHIFT.BMWOffset33bNativeSessionSelection/1` — exact selected
  Silverstone+BMW numeric `BODY0 -> outer` matrix;
- `SHIFT.BMWOuterVHFNumericRelation/1` — exact selected first-bootstrap
  `outer Vehicle -> canonical BMW VHF Root` numeric matrix.

The last relation is numerically identity for this selected first bootstrap, but
its semantic authority remains the separately proven setup-fixed affine relation.
Numeric identity is not used to infer semantic identity.

## OUTPUT

`tools/ghidra/build_bmw_body0_bind_frame_proof.py` publishes:

```text
SHIFT.BMWBody0BindFrameProof/1
```

Committed artifact:

```text
evidence/bmw_body0_bind_frame_proof.json
```

Under the established D3D row-vector convention:

```text
q_outer = q_BODY0 * M_BODY0_to_outer
q_vhf   = q_outer * M_outer_to_vhf_root

M_BODY0_to_vhf_root = M_BODY0_to_outer * M_outer_to_vhf_root
```

For the selected session:

```text
M_BODY0_to_outer.translation
  = (0,
     -0.004956085581085581,
     -0.01147086247086247)

M_outer_to_vhf_root = I4
```

Therefore:

```text
M_BODY0_to_vhf_root =
[ 1  0  0  0 ]
[ 0  1  0  0 ]
[ 0  0  1  0 ]
[ 0 -0.004956085581085581 -0.01147086247086247 1 ]
```

The equality of the final numeric matrix with `M_BODY0_to_outer` is a consequence
of the independently proven selected outer->VHF matrix, not an identity-bind
assumption.

## CONSUMER

The artifact uses the frozen schema already required by
`src/physics/bmw_body0_bind_frame_proof_packet.py`.  The existing positive-only
BBFP builder validates BODY index/name, frame relation, row-vector affine form,
static source targets, scope flags, finiteness and non-singularity before native
runtime admission.

Immediate continuation:

```text
SHIFT.BMWBody0BindFrameProof/1
-> SHIFT.NativeBMWBody0BindFrameProofPacket/1
-> existing runtime admission / Phase 704 composition
-> persistent fresh BMW world transform
```

## GATES_CHANGED

Positive:

```text
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready = true
BODY0_bind_frame_proof_ready                         = true
```

Still fail-closed:

```text
vehicle_world_transform_ready = false
retail_cadence_admitted       = false
```

## LIMITS

- No BODY0/VHF identity matrix is assumed.
- Numeric outer/VHF identity is not promoted to semantic identity.
- The selected first-primary-player-bootstrap scope of the outer/VHF numeric
  relation is preserved.
- The explicit native session selector is not claimed as an observed retail
  live-session default.
- No new runtime capture or original-game execution is used.
- No scheduler/cadence, control-chain, camera, or world-transform gate is
  promoted by this proof alone.

## TESTS

`tests/test_ghidra_bmw_body0_bind_frame_proof.py` locks:

- exact regeneration of the committed proof;
- a non-commuting matrix fixture proving multiplication order rather than relying
  on the selected identity-valued outer/VHF matrix;
- `translation == -offset33b` continuity;
- fail-closed outer/VHF gate and matrix-convention validation;
- acceptance by the existing positive-only BBFP packet builder while
  `vehicle_world_transform_ready` remains false.

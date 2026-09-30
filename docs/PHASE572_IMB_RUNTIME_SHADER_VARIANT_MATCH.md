# Phase 572 — IMB same-instance shader-variant matcher

Phase 571 completes the static handoff required by the Silverstone D3D9
attribution path. Phase 572 implements the final fail-closed matcher over one
exact IMB resource runtime report.

## Contract

The new contract is:

`SHIFT.IMBRuntimeShaderVariantMatch/1`

implemented in:

`src/scene/imb_runtime_shader_variant_match.py`.

Inputs:

- `SHIFT.IMBRuntimeShaderTargetSet/1` from Phase 571;
- `SHIFT.D3D9RuntimeBindingEvidence/1` built for one exact IMB resource using
  the Phase 571 runtime-resource adapter and the recovered D3D9 Usage map.

## Resource scope

The runtime report identifies one resource by decoded IMB path + SHA-256.

The matcher ignores target bindings for every other resource. This is
important for the 428-binding Silverstone target set: a runtime report for one
IMB is judged only against the primitive bindings belonging to that exact IMB
identity.

## Required same-instance proof

A runtime draw is eligible only when its `(frame, draw_index)` occurs in a
`same_instance_gate.candidate_frames` row that proves all of:

- exact resource identity;
- a known and valid bound D3D9 declaration;
- at least one source-descriptor → runtime-declaration match;
- valid draw-snapshot schema.

The matcher also rechecks the draw-local vertex-declaration resource path/SHA
instead of trusting the gate flag alone.

## Primitive identity

For every binding belonging to the runtime IMB, the draw must match the
Phase 570 source-backed range exactly:

- `start_index == first_index`;
- `primitive_count * 3 == index_count`.

This separates the only known two-primitive Silverstone IMB as well as all
single-primitive resources.

## Shader-variant scoring

Each Phase 571 `candidate_variants[]` row is compared with the draw-local
`SHIFT.ShaderPermutationIdentity/1` hashes.

| Evidence | Score | Attribution strength |
|---|---:|---|
| exact permutation identity | 100 | strong |
| exact VS+PS pair byte SHA-256 | 90 | strong |
| both vertex and pixel byte SHA-256 | 80 | strong |
| pixel byte SHA-256 only | 40 | prefilter only |
| vertex byte SHA-256 only | 35 | prefilter only |

Attribution requires a unique strongest static variant with score >= 80.

A pixel-only Phase 568/569 hit remains useful for capture reduction, but cannot
select a retail permutation.

## Ambiguity policy

If two preserved variants obtain the same strongest score, the binding stays
blocked with `multiple-strong-variants`.

The matcher never breaks ties by FXO filename, archive order, program offset or
the representative row retained by an earlier hash-dedup step.

## Output scope

The report is per exact IMB resource and records:

- number of target bindings for that resource;
- observed/attributed/blocked binding counts;
- same-instance candidate draw count;
- every matching frame/draw and runtime hash set;
- all static variants matching each draw;
- selected variant only when unique and strong.

## Boundary

Phase 572 implements attribution logic but does not manufacture runtime
evidence.

A real Silverstone D3D9 capture is still required to produce the
`D3D9RuntimeBindingEvidence/1` reports consumed here.

Once a binding is attributed, its static material/render pipeline may use that
runtime-proven variant in a later admission phase. Phase 572 itself performs no
RenderCommand or Vulkan admission.

## Next

Run the Phase 569 prefilter on an authentic Silverstone frame, build runtime
binding evidence for retained exact IMB resources, and execute this matcher.

For bindings that become uniquely attributed, feed the selected FXO/VS/PS
identity back into the existing RenderBinding/RenderCommand pipeline and begin
native Silverstone scene loading.

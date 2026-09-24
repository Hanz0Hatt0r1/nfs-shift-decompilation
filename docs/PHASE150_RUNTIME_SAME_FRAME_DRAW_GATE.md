# Phase 150 — same-frame indexed draw requirement

`SHIFT.D3D9RuntimeBindingEvidence/1.same_instance_gate` now requires an indexed draw
event in the same captured frame as the bound declaration/resource/descriptor match.

This prevents a declaration-only frame from being promoted as proof that the mesh
instance was actually submitted.

## Strict requirements

- same MEB resource identity;
- frame-bound declaration was created in the capture;
- bound declaration decoder status is `match`;
- explicit MEB Usage→D3D9 Usage mapping;
- at least one descriptor match on the bound declaration;
- at least one `draw_indexed_primitive` event in that frame.

`--require-same-instance` remains the hard CLI mode.

## Boundary

This still does not prove that the trace is authentic or that it came from the retail
process. It only strengthens the semantic acceptance of an already supplied capture.
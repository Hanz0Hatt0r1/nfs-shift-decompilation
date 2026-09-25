# Phase 253 — MATRIX runtime semantics

FUN_00698d50/FUN_00698f40 and their helpers establish one reusable MATRIX contract used by scene/object runtime branches.

`Offset` is parsed as three floats. `Orientation` consumes four floats and the runtime stores them as `[w,x,y,z] = [input3,input0,input1,input2]`. `Scale` is optional and defaults to `1.0`.

`matrix_runtime.py` exposes this representation and a deterministic 4x4 conversion. It does not infer parent composition or an alternate axis convention.

Renderer and RENDER.bff are untouched.

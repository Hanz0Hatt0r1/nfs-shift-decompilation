# Retail D3D9 startup frontier — 2026-10-19

## What the latest probe demonstrates

The bounded retail probe now accepts the game's 1280×720 fullscreen
`IDirect3D9::CreateDevice` request through the Vulkan-backed adapter. The guest
then passes a run of compatibility calls for shader state, texture and render
target queries, backbuffer access, surface description, and `Clear`.

The adapter models the guest-visible results needed to continue startup. Its
`Clear` implementation validates and records the request, but does not issue a
Vulkan clear command. The host still draws the converted MGEO smoke mesh. No
retail D3D9 draw, frontend, or offline race has been demonstrated by this
probe.

## Current stop

With the recovered supplements for `0x008329d0` and `0x00835050`, probes v161
and v162 reach 48,532 P-code dispatches across 1,221 guest functions. They stop on a
read at guest address zero in `0x00838410`, called from `0x00853790`.

Ghidra shows `0x00853790` populating resource arrays, including a factory call
through a device-like object's vtable slot `+0x234`. It passes the resulting
array element into `0x00838410`. That function reads fields at offsets `+0x18`
and `+0x8`, and in one branch calls a method at the resource object's vtable
slot `+0x48`. The exact factory interface and why it returns a null pointer are
not established yet. This must be resolved before modeling a texture/surface
object; inventing a successful resource would hide the observed failure.

## Revenginstr contribution

Both missing guest functions were exported from the Ghidra program and compiled
as one-function portable P-code supplements with `revenginstr` revision
`e15b05437a56f0401e7676866d07deecbe384043`:

| Function | Lowered | Rejections | Result |
| --- | ---: | ---: | --- |
| `0x008329d0` | 1/1 | 0 | Retail probe advanced from `GetBackBuffer` to `GetDesc` |
| `0x00835050` | 1/1 | 0 | Retail probe advanced into resource construction at `0x00853790` |

The shared lowerer made the function-recovery loop short and repeatable. It did
not implement D3D9 object behavior, solve the null factory result, or translate
retail rendering to Vulkan. The complete frozen corpus remains 41,538/41,538
lowerable; full-corpus coverage is infrastructure evidence, not game
readiness.

## Probe records

The v143–v161 bounded logs are stored in
[`evidence/retail_frontier_20261019/`](../evidence/retail_frontier_20261019/).
The latest summary is
[`entrypoint_probe_v162_d3d9_resource_null.json`](../evidence/retail_frontier_20261019/entrypoint_probe_v162_d3d9_resource_null.json).
Ghidra pseudocode, portable instruction inputs, and the two lowerer build
reports are in
[`ghidra_resource_functions_20261019/`](../evidence/retail_frontier_20261019/ghidra_resource_functions_20261019/).

The `shift_runtime` and `shift_runtime_recompiled_pcode_module_check` targets
build successfully. The focused CTest case
`shift_runtime_recompiled_pcode_module` passes 1/1.

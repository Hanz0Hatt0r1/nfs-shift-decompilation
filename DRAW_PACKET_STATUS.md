# SHIFT DrawPacket IR

## Current boundary

The importer now has two composition layers:

`VHF/CAR -> MEB -> BMT -> DDS -> FX/FXO -> RenderBinding -> DrawPacket`

`SHIFT.RenderBinding/1` resolves scene hierarchy/world transforms, MEB primitives,
BMT materials and FX/FXO shader candidates. `SHIFT.DrawPacket/1` is the runtime-facing
packet schema used by the next renderer stage.

## Resolved data

Each packet preserves:
- scene/node identity and world matrix;
- resolved MEB path and primitive/index range;
- BMT material reference;
- FX source and deterministic FXO selection metadata;
- D3D9 sampler registers when CTAB reflection proves them;
- VS/PS semantic linkage and vertex-format evidence when available;
- texture references and DDS metadata.

Path resolution uses slash/case normalization, `.mtx <-> .bmt` aliases and
same-archive preference for basename fallback.

## Selection policy

FXO candidates are sorted using explicit evidence:

1. exact expected sampler set;
2. sampler coverage;
3. valid VS/PS semantic + vertex-format pair;
4. vertex-pair score;
5. material uniform coverage;
6. specialization evidence;
7. contradictions/unexpected features;
8. stable file/program offsets.

If multiple distinct shader pairs remain tied, the result is marked
`selection_status=ambiguous` rather than depending on incidental filesystem order.

## Remaining render work

1. Prove exact MEB vertex packing/D3DDECLTYPE, especially raw color properties `460/461`.
2. Validate generated GLES shaders with a real compiler for the target BMW permutations.
3. Build the minimal desktop reference renderer.
4. After static rendering is stable, connect blend weights/indices to BAS/BAB skinning.

This document intentionally no longer lists semantic linkage as an unresolved
future layer: it is implemented and regression-tested in `shader_interface.py`.


## StaticDraw/1 readiness contract

static_draw.py now converts each runtime-facing draw packet into SHIFT.StaticDraw/1. A packet is marked ready only when the MEB SHIFT.VertexLayout/1 is valid, the VS/PS selection is unique and its semantic/vertex-format evidence is valid, material texture bindings have explicit D3D9 sampler registers from FXO/CTAB, and there are no blocking unresolved references.

Renderer-global samplers are preserved as explicit external requirements rather than being silently treated as material textures. This keeps the static BMW path deterministic while leaving environment/shadow resources for the renderer resource manager.

## Phase 17: linked shader propagation

`SHIFT.DrawPacket/1` now preserves `linked_shader_pair` and any `linked_shader_error` from `MaterialBinding/1`. StaticDraw readiness requires a valid `SHIFT.LinkedShaderPair/1` for each selected material, preventing a packet from becoming renderer-ready when permutation selection succeeded but GLSL translation did not.
## Phase 19: DrawPacket -> reference renderer

`reference_renderer.py` now exposes `build_static_draw_from_packet()` and `render_draw_packet()`. The reference renderer consumes the same `SHIFT.StaticDraw/1` validation boundary as the future GPU backend, then rasterizes only neutral mesh data.

This keeps renderer validation separate from source-game resource access and gives us a deterministic desktop oracle for the first BMW static-render milestone.
## Phase 20: canonical DrawPacket -> StaticDraw

`draw_packets.py` now attaches a `SHIFT.StaticDraw/1` contract to every canonical `SHIFT.DrawPacket/1` packet. Aggregate stats expose `ready_static_draws` and `blocked_static_draws` so unresolved renderer prerequisites are visible without a second conversion pass.
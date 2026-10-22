# Process 2 — D3D9 alpha-blend render-state contract for a future Vulkan guest-draw path

- **Date:** 2026-10-22
- **Mode:** report-only, renderer-side bounded analysis; no code edits and no tests executed.
- **Source baseline:** [main `53d82df46d6a4fe69ae7e52d2750fa00d5477d7e`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/tree/53d82df46d6a4fe69ae7e52d2750fa00d5477d7e).
- **Boundary:** D3D9 `SetRenderState` raw-value cache upstream, then as-yet-unimplemented translated guest draw packet downstream. No work on SetViewport, Clear/Present, DrawPrimitiveUP, DXT3, vertex buffers, textures, P-code, Win32, scheduler, or frontend.
- **Evidence status:** v791 = 360 original-PE P-code replay *host* frames, zero reported Vulkan validation errors, `guest_draw_translation=false` and `retail_rendering_proven=false`. Neither a native launch nor proof of an executed retail draw.

## 1. Minimum state and three distinct representations

| D3D9 raw render-state ID | Role | Effective Vulkan field / action |
| --- | --- | --- |
| `D3DRS_ALPHABLENDENABLE = 27` | boolean master enable | `VkPipelineColorBlendAttachmentState.blendEnable` |
| `D3DRS_SRCBLEND = 19` | RGB source factor | `srcColorBlendFactor` |
| `D3DRS_DESTBLEND = 20` | RGB destination factor | `dstColorBlendFactor` |
| `D3DRS_BLENDOP = 171` | RGB operation | `colorBlendOp` |
| `D3DRS_SEPARATEALPHABLENDENABLE = 206` | alpha selection switch | **not** an independent Vulkan field: selects effective alpha triple |
| `D3DRS_SRCBLENDALPHA = 207` | alpha source factor when 206 is true | `srcAlphaBlendFactor` |
| `D3DRS_DESTBLENDALPHA = 208` | alpha destination factor when 206 is true | `dstAlphaBlendFactor` |
| `D3DRS_BLENDOPALPHA = 209` | alpha operation when 206 is true | `alphaBlendOp` |
| `D3DRS_BLENDFACTOR = 193` | `D3DCOLOR` / DWORD constant for `D3DBLEND_BLENDFACTOR` (14) and `INVBLENDFACTOR` (15) | four normalized float constants, R/G/B/A, in `vkCmdSetBlendConstants` with `VK_DYNAMIC_STATE_BLEND_CONSTANTS`, or static `blendConstants` if purposely not dynamic |

These nine IDs are the **minimum blend-specific raw state set**; ID 168 (`D3DRS_COLORWRITEENABLE`) affects the final attachment output mask but is a separate render-target write-state contract, not a blend factor or operation. The current captured-bundle path includes it and rejects non-`0xF` masks. More render targets and per-target masks are not established by this analysis.

**A. Raw state storage (P1):** per-device `state_id -> exact DWORD` register cache, with effective D3D9 initialization/reset/stateblock provenance and command order if/when those capabilities exist. Preserve values even if blending is currently disabled or separate alpha is false. The raw constant stays packed `0xAARRGGBB`. Keep absent/unobserved distinct from explicit zero; a missing capture is not proof of a zero state. This preserves future enable toggles without reinterpreting calls upstream.

**B. Effective per-draw state (P2):** resolve a consistent *draw-time snapshot* against authoritative D3D9 defaults, then validate/translate the resulting `blend_enable`; RGB (source,destination,op); alpha (source,destination,op); and RGBA blend constants when referenced. When `206=0`, alpha factors/op **inherit RGB** irrespective of stored 207–209. When `206=1`, alpha uses 207–209, with D3D9 defaults only if their provenance is valid. When `27=0`, blending is disabled for the draw, with all raw state preserved for a later draw. Failure to resolve required effective state or an unsupported factor must be reported as a blocker, not silently guessed.

D3D9 documented defaults: enable=false; RGB src=`ONE` (2), dst=`ZERO` (1), op=`ADD` (1); separate-alpha=false; alpha src=`ONE`, dst=`ZERO`, op=`ADD`; blend factor=`0xffffffff`. These are **API-derived defaults**, not observations of live guest initialization.

**C. Vulkan pipeline key:** partition by effective attachment `blendEnable` and the six effective factors/operations. Include the usual *other* pipeline compatibility dimensions (shader/program, render pass/attachment formats/sample count, compatible pipeline layout and any other fixed state) in the actual full key; the blend subkey alone never uniquely identifies a pipeline. The source `separate_alpha` flag does not need its own key bit if the **effective** alpha triple is identical. With `VK_DYNAMIC_STATE_BLEND_CONSTANTS`, packed blend-factor color is **per draw / command-buffer dynamic state, not part of the pipeline key**. Without that dynamic declaration, it is a pipeline-create value and must enter the key for constant-factor draws. Disabled blending can be canonicalized to one nonblending variant while retaining raw factors, provided no other render states are accidentally collapsed. Maintain a distinct attachment write-mask key component where the broader render-target contract applies.

## 2. Factor/op mapping and fail-closed policy

**Ordinary D3D9 factors:** 1 `ZERO` → `VK_BLEND_FACTOR_ZERO`; 2 `ONE` → `ONE`; 3/4 `SRCCOLOR/INVSRCCOLOR` → `SRC_COLOR/ONE_MINUS_SRC_COLOR`; 5/6 `SRCALPHA/INVSRCALPHA` → `SRC_ALPHA/ONE_MINUS_SRC_ALPHA`; 7/8 `DESTALPHA/INVDESTALPHA` → `DST_ALPHA/ONE_MINUS_DST_ALPHA`; 9/10 `DESTCOLOR/INVDESTCOLOR` → `DST_COLOR/ONE_MINUS_DST_COLOR`; 11 `SRCALPHASAT` → `SRC_ALPHA_SATURATE` (factor RGB = min(src.a, 1-dst.a), alpha = 1). The exact Vulkan factor enum is selected separately for the RGB and alpha components; D3D9 and Vulkan agree on the alpha component of the usual color factors.

**Legacy/special factors:**
- 12 `BOTHSRCALPHA`: D3D9 `SRCBLEND` only, normalize effective RGB pair to `SRC_ALPHA`/`ONE_MINUS_SRC_ALPHA`; the nominal destination setting is overridden.
- 13 `BOTHINVSRCALPHA`: D3D9 `SRCBLEND` only, normalize effective RGB pair to `ONE_MINUS_SRC_ALPHA`/`SRC_ALPHA`; nominal destination overridden.
- 14 `BLENDFACTOR` / 15 `INVBLENDFACTOR`: normalize 193 `0xAARRGGBB` to `(R,G,B,A)/255`; RGB factors `CONSTANT_COLOR` / `ONE_MINUS_CONSTANT_COLOR`; alpha factors `CONSTANT_ALPHA` / `ONE_MINUS_CONSTANT_ALPHA`. The alpha constant comes from the same A byte. This needs an enabled blend-constant path absent from the current bundle translator.
- 16/17 `SRCCOLOR2/INVSRCCOLOR2`: D3D9Ex dual-source modes; not an assumed ordinary D3D9 implementation. Reject as unsupported unless the guest device interface, shader second output, `dualSrcBlend` feature, and actual semantics have been established. Do not map as ordinary `SRC_COLOR`.

**Ops:** `D3DBLENDOP_ADD=1` → `VK_BLEND_OP_ADD`; `SUBTRACT=2` → `SUBTRACT` (source minus destination); `REVSUBTRACT=3` → `REVERSE_SUBTRACT` (destination minus source); `MIN=4` → `MIN`; `MAX=5` → `MAX`. For MIN/MAX the Vulkan equation ignores multiplying source/destination factors; regression expectations should reflect the documented D3D9 semantics/capabilities rather than treating these as ordinary weighted ADD. Device D3D9 caps (factor and blend-op support, separate alpha) and Vulkan color-attachment blend-format capability must be checked for a real backend. Unsupported combinations are blockers, not implicit substitutions.

## 3. Minimum P1 → P2 guest draw packet boundary

Conceptual contract (not a proposed P1 implementation):

~~~text
GuestDrawPacket {
  guest_device_identity,
  ordering_token / draw_sequence,
  draw_reference,                  // opaque draw identity / binding to its own packet
  raw_blend_state_snapshot: {
    27, 19, 20, 171, 206, 207, 208, 209, 193
  },                               // each: {present, raw_dword}, or full raw map
  state_provenance                // known initialized/default/resolved, or unknown
}
~~~

The **smallest semantic boundary** is a per-draw, immutable snapshot of raw DWORDs (a full state map is acceptable; a correctly captured nine-key projection is the minimum for this blend-only study), bound to device identity and guest command ordering. If P1 can only forward updates, P2 instead needs *ordered* updates plus a well-defined draw barrier and initial state; a snapshot avoids ambiguity from further guest `SetRenderState` before renderer execution. Copy or otherwise lifetime-pin the snapshot so queued guest draws cannot all read the most recent state. Preserve whether each value was observed versus synthesized; a draw must not depend on P2's later mutable state.

P1's `SetRenderState` stays a raw cache operation; **no Vulkan enums, default inference, combined-factor expansion, separate-alpha choice, clamping, or pipeline-key construction in P1**. On receipt, P2 resolves documented D3D9 initial/default behavior *only when justified*, validates enums, computes the effective attachment state, chooses the Vulkan pipeline variant and supplies blend constants per draw. Because the first guest draw does not yet exist, packet wire format, state lifecycle and initialization provenance are **proposed contracts**, not observed events. No change to the present replay milestone or its meaning is implied.

## 4. Vulkan 1.1 implementation choice and code constraints

**Guaranteed Vulkan 1.1 core route:** use graphics **pipeline variants** for `blendEnable` plus six factor/op fields; `vkCmdBindPipeline` for each draw's effective variant. For constant-factor blends set `VK_DYNAMIC_STATE_BLEND_CONSTANTS` in each relevant pipeline's `VkPipelineDynamicStateCreateInfo` and call `vkCmdSetBlendConstants` with the draw's four floats before the draw. Merely calling the command without declaring the dynamic state is insufficient. A fixed `VkPipelineColorBlendStateCreateInfo.blendConstants` alternative requires keyed variants per value and is less suitable. Vulkan 1.1 does **not** make blend enable/equations core dynamic states.

**Optional extension route:** `VK_EXT_extended_dynamic_state3` exposes `VK_DYNAMIC_STATE_COLOR_BLEND_ENABLE_EXT` with `vkCmdSetColorBlendEnableEXT` and `VK_DYNAMIC_STATE_COLOR_BLEND_EQUATION_EXT` with `vkCmdSetColorBlendEquationEXT`; these can change enable and RGB/alpha factors/ops per attachment per draw. They require extension availability, enabling the corresponding `VkPhysicalDeviceExtendedDynamicState3FeaturesEXT` flags and declaring relevant dynamic states in the pipeline. `VK_DYNAMIC_STATE_BLEND_CONSTANTS` remains the core mechanism for constants. The extension is an **optional Vulkan 1.1 device capability**, not guaranteed merely by targeting Vulkan 1.1; default to pipeline variants for the project contract. Another optional feature such as dynamic color-write mask is outside the blend-only scope.

**Confirmed snapshot limits:**
- `native_runtime/src/shift_runtime.cpp` has `BundlePipelineState` fields for enable and six blend parameters (`570–582`); `load_bundle_pipeline_state` reads `pipeline_state.json` (`869–977`); pipeline creation fills `VkPipelineColorBlendAttachmentState` and calls `vkCreateGraphicsPipelines` (`3652–3694`). It does not configure dynamic blend constants (`blend.blendConstants` remains zero-initialized; no `pDynamicState` is wired in that creation block).
- `native_vulkan/src/vulkan_bundle_execute.cpp` reads the same bundle state (`1246–1365`) and builds a fixed attachment state (`2045–2092`). This is **bundle/material execution**, not guest-draw packet decoding.
- `src/render/vulkan/vulkan_d3d9_capture_bundle.py` caches raw capture `set_render_state` events at `252–253`; `_pipeline_state` (`648–685`) maps render states 27/19/20/171/206/207/208/209 and emits six Vulkan blend fields, with alpha-op 209 falling back to ADD when separate alpha is enabled. Current `_BLEND_FACTOR` table (`47–59`) covers only 1–11; it cannot reproduce constant or both-alpha factors 12–15. Its contract requires other nonblend states, including write-mask=`0xF`, and rejects incomplete inputs. Its behavior is **not** evidence of live P1 guest-draw forwarding.
- `src/render/material_pipeline_state.py` (`33–106`, `266–420`) holds the *separate* proven static BMT subset: factor rows 1–11, ops ADD/SUBTRACT/REVSUBTRACT/MIN/MAX, and RGB inheritance when separate alpha is disabled. This is not a demonstration that arbitrary guest D3D9 states are implemented.
- In `native_runtime/src/shift_runtime.cpp` `3948–3950` the guest D3D9 frame branch explicitly says guest draw calls are not translated yet. Telemetry sets `guest_draw_translation` false (`5379`). No tested runtime pipeline variant selector keyed to guest render-state snapshots is established.

## 5. Compact target regressions (specification only; not run)

| Case | Raw state setup / transition | Expected renderer-side result |
| --- | --- | --- |
| B0 | 27=0; change 19/20/171 while disabled | no blending, unmodified source output subject to write mask; raw changes retained; later enable sees them |
| B1 | 27=1, 19=2 ONE, 20=1 ZERO, 171=1 ADD, 206=0 | source-overwrite equation for RGB and alpha |
| B2 | 27=1, 19=5 SRCALPHA, 20=6 INVSRCALPHA, 171=1, 206=0 | standard source-alpha weighted RGB and inherited alpha equation |
| B3 | 19=3 SRCCOLOR, 20=10 INVDESTCOLOR; then 19=4 INVSRCCOLOR, 20=9 DESTCOLOR | verify SRC/DST color and inverse factors; distinct pipeline subkeys |
| B4 | exercise 7/8 DESTALPHA/INVDESTALPHA, 11 SRCALPHASAT (legal source position) | expected destination alpha-dependent RGB; saturate uses min(src.a,1-dst.a), alpha factor=1 |
| B5 | 171=2 SUBTRACT vs 171=3 REVSUBTRACT, same factors | source-destination vs destination-source sign and pipeline variant differentiation |
| B6 | 171=4 MIN and 171=5 MAX with nontrivial factors | min/max equations (Vulkan factors ignored for MIN/MAX); correct op ordering |
| B7 | 206=0 with 207/208/209 set differently; toggle 206 to 1 then back | inherited RGB alpha triple → explicit alpha triple → inherited, without erasing cached 207–209 |
| B8 | 206=1; RGB src=5,dst=6,op=1; alpha src=2 ONE,dst=1 ZERO,op=2 SUBTRACT | independent alpha fields; source-alpha output differs from RGB path |
| B9 | 206=1 but 209 never explicitly written | API default alpha operation ADD only with valid default provenance; absent/unknown otherwise blocks |
| B10 | 19=12 BOTHSRCALPHA then 19=13 BOTHINVSRCALPHA; deliberately contradictory 20 | expand source-only combined pair; confirm destination override, don't treat raw 20 as effective |
| B11 | 19=14 BLENDFACTOR then 20=15 INVBLENDFACTOR, 193=`0x80402010`; change only 193 on next draw | constants (R=64,G=32,B=16,A=128)/255; pipeline reuse if dynamic constants; distinct pixel result |
| B12 | factor 16 or 17; unsupported enum / invalid boolean; unsupported feature/caps | deterministic fail-closed diagnostic; no invented fallback |
| B13 | alternating B0→B2→B8→B0 across queued draws | per-draw state snapshot not aliased to latest cached state; correct variant reuse and ordering |

For image-based comparisons eventually specify source RGBA, destination RGBA, target format, write mask, capability gates and numerical tolerance. These are **future** regressions, not run results.

## 6. Provenance and unknowns

**Source facts at named commit:** static BMT and captured-bundle blend translation exists for a subset; two native Vulkan consumers read predefined pipeline state and create fixed blend attachments; current guest runtime explicitly does not translate guest draws. Source links: [runtime](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/53d82df46d6a4fe69ae7e52d2750fa00d5477d7e/native_runtime/src/shift_runtime.cpp), [bundle executor](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/53d82df46d6a4fe69ae7e52d2750fa00d5477d7e/native_vulkan/src/vulkan_bundle_execute.cpp), [captured-D3D9 translator](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/53d82df46d6a4fe69ae7e52d2750fa00d5477d7e/src/render/vulkan/vulkan_d3d9_capture_bundle.py), [BMT translator](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/53d82df46d6a4fe69ae7e52d2750fa00d5477d7e/src/render/material_pipeline_state.py). The upstream `SetRenderState` raw-cache behavior is a **supplied task premise**; the renderer-side source inspection is not a new audit of P1.

**API-derived, not observed retail behavior:** numeric IDs/defaults, combined-factor source override, separate-alpha inheritance, constant blend-factor packing, Vulkan 1.1 static/dynamic division and optional extension capabilities. API sources: [D3D9 render-state enumeration](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3drenderstatetype), [D3D9 factor enum](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dblend), [Vulkan blend factors](https://docs.vulkan.org/refpages/latest/refpages/source/VkBlendFactor.html), [blend constants](https://docs.vulkan.org/refpages/latest/refpages/source/vkCmdSetBlendConstants.html), [`VK_EXT_extended_dynamic_state3`](https://docs.vulkan.org/refpages/latest/refpages/source/VK_EXT_extended_dynamic_state3.html).

**Unknown until at least one translated guest draw:** actual runtime ordering/snapshot provenance and first draw's state vector; frequency of each D3D9 factor/operation and constants; real game use of separate alpha or rare factors; actual guest shader/attachment format compatibility, GPU/driver feature support and visual equivalence. No claim of retail rendering success follows from the clear-only v791 replay.

## Exactly one next evidence-backed target

**Target P2-BLEND-01 (separate bounded task, not undertaken here):** define and validate a renderer-side, fail-closed *pure translation contract* converting one immutable nine-ID raw snapshot + explicit default-provenance metadata into effective Vulkan blend attachment fields and optional four blend constants, using the existing captured-bundle translator's 1–11/ops table as the baseline and documenting blockers for 12–17. Acceptance evidence: an exhaustive input/output fixture matrix corresponding to B0–B13, with no guest-draw success claim. Do not cross the P1 boundary or undertake unrelated graphics work as part of that task.

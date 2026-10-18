# Retail race-window D3D9 capture — 2026-10-18

The isolated PC retail 1.02 executable was launched through PortProton. After
the user confirmed that a race had loaded, the manual capture trigger was
fired. Trigger-mode texture files were deferred before that signal; the
texture output directory contained zero files before the trigger.

## Capture

- Trigger frame: **5867**; configured window: **5865–5869**; completion event:
  frame **5870**.
- The raw JSONL contains **105,047 valid objects**, zero malformed lines, and
  zero duplicate keys. Its frame range is 0–5870 because startup metadata was
  buffered before the trigger.
- The capture records **5,721 indexed draws** and **8,168 VB/IB payload events**.
- **373 draws** match **nine shader hashes** from the 51-hash Silverstone-era
  target inventory: 41 basic-instanced, 222 crowd-instanced, 69 crowd
  billboard, 33 foliage-instanced, and eight skin-test-instanced draws.
- There are **3,031 captured texture-snapshot events** across **508 unique
  paths**. All paths were found: 499 DDS files and nine PPM files. The DDS
  headers and mip payload lengths validate; 387 use DXT1 and 112 use DXT5,
  with one to eleven mip levels.
- Before the trigger, **5,125** `set_texture` events reported
  `deferred-until-trigger`; **1,018** snapshots failed and have no file path.
- The capture bundle totals **212,322,572 bytes** and remains outside Git.

The full raw JSONL and binary payloads are stored under
`/home/pes/nfs-shift-recompilation-artifacts/portproton-retail-capture-20261018/retail-race-after-load-20261018/`.
The machine-readable audit records the raw capture hash, trigger window,
snapshot validation, target shader matches, and blockers in
[`../evidence/retail_frontier_20261018/d3d9_race_window_capture.json`](../evidence/retail_frontier_20261018/d3d9_race_window_capture.json).

## Limits and next step

The race context was user-confirmed; no screenshot or scene label was captured
to independently identify the scene. Shader matches are against the supplied
Silverstone-era inventory and do not prove same-resource or primitive
identity. The audit found no `resource_path`/`resource_sha256` pairs and no
six-face cube snapshot. The evidence is from the original retail executable
under PortProton, not the recompiled Linux runtime.

Next, correlate the matched race-window draws with their captured VB/IB
payloads and textures, then establish exact resource path/SHA identity before
adding any of them to the Vulkan renderer.

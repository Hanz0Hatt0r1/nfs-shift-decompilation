# Retail race-window D3D9 capture — 2026-10-18

The isolated PC retail 1.02 executable was launched through PortProton. After
the user confirmed being in a race, two manual capture triggers recorded short
render windows. New texture snapshots remained deferred until each trigger;
the texture output directory was empty before the first trigger.

## Capture

- First trigger: frame **5867**, window **5865–5869**, completion at frame
  **5870**. Follow-up trigger: frame **6985**, window **6983–6987**, completion
  at frame **6988**.
- The combined raw JSONL contains **202,870 valid objects**, zero malformed
  lines, and zero duplicate keys. Its frame range is 0–6988; the log includes
  startup metadata and the two trigger windows.
- The two windows record **13,069 indexed draws** and **8,252 VB/IB payload
  events**. The follow-up window alone added 7,348 draws and 84 payloads.
- **813 draws** match **10 shader hashes** from the 51-hash Silverstone-era
  target inventory: 131 basic-instanced, 462 crowd-instanced, 134 crowd
  billboard, 78 foliage-instanced, and eight skin-test-instanced draws. The
  follow-up window added 440 matches across nine hashes.
- There are **6,704 captured texture-snapshot records** across **541 unique
  paths**. All paths were found: 531 DDS files and 10 PPM files. DDS headers
  and mip payload lengths validate; 408 use DXT1, 120 DXT5, and three DXT3,
  with one to eleven mip levels. The follow-up trigger added 33 texture files.
- Across the two trigger windows, **12,285** `set_texture` events reported
  `deferred-until-trigger`; **2,125** snapshot attempts failed and have no
  file path.
- The capture bundle totals **253,861,323 bytes** and remains outside Git.

The full raw JSONL and binary payloads are stored under
`/home/pes/nfs-shift-recompilation-artifacts/portproton-retail-capture-20261018/retail-race-after-load-20261018/`.
The machine-readable audit records the raw capture hash, trigger window,
snapshot validation, target shader matches, and blockers in
[`../evidence/retail_frontier_20261018/d3d9_race_window_capture.json`](../evidence/retail_frontier_20261018/d3d9_race_window_capture.json).

## Limits and next step

The race context was user-confirmed for both triggers; no screenshot or scene
label was captured to independently identify the scene. Shader matches are
against the supplied Silverstone-era inventory and do not prove same-resource
or primitive identity. The audit found no `resource_path`/`resource_sha256`
pairs and no six-face cube snapshot. The evidence is from the original retail
executable under PortProton, not the recompiled Linux runtime.

The matched target draws all bind one dynamic 128 KiB stream-1 vertex buffer
(`usage=520`, `pool=0`). Its stride is 64 bytes; the captured declaration has
four stream-1 `FLOAT4` inputs at offsets 0, 16, 32 and 48 (`TEXCOORD8` through
`TEXCOORD11`). All 813 target draws use this buffer, across 231 distinct
64-byte-aligned offsets. The capture contains no payload for this generation,
while stream 0 and index payloads are complete for all 813 draws. These 64-byte
records are required to reproduce the target draws' stream-1 vertex inputs;
their exact meaning still needs shader-level confirmation. The exact
capture-local identity and counts are recorded in
[`stream1_partial_payload_followup.json`](../evidence/retail_frontier_20261019/stream1_partial_payload_followup.json).

No new capture is needed for the current entrypoint and loop analysis. A later
renderer capture should be made only after the race is loaded: arm the existing
resource trigger for `ps:b83e3c4ec719e80f`, use `--partial-buffer-payloads
--partial-buffer-length 131072`, and keep the two-frame pre/post window. The
length filter matches the single 128 KiB VB generation in the current capture
and restricts partial payload files to that size; full-buffer capture behavior
is unchanged. This captures any partial VB lock ranges around the target shader
while leaving texture snapshots and screenshots off. The capture producer
buffers pre-trigger render events and payload ranges in memory, then flushes the
selected window after the trigger; it does not
continuously write the startup render stream to disk. Store the resulting log
and payloads outside Git. No full startup dump needs to be repeated.

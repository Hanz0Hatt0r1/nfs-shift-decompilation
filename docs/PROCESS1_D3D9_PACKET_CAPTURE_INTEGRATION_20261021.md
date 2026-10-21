# Process 1 — optional D3D9 packet capture integration (2026-10-21)

The Linux runtime can opt into Process 2's D3D9 packet capture adapter when it
builds the adapter table for the recompiled PE32 runtime. Set a non-empty
`SHIFT_D3D9_PACKET_CAPTURE_DIR` to the output directory before starting the
runtime. If the variable is unset or empty, the regular runtime callbacks are
used and no packet-capture adapter is installed.

The capture adapter stays owned by `Runtime` for as long as the P-code module
can call its callbacks. It forwards resource callbacks to the existing runtime
backend and records supported `DrawIndexedPrimitive` packets. Its first-draw
limit is one. The capture adapter enables managed DXT5 snapshots so the guest
can provide the raw compressed mip bytes; this flag applies only to the packet
capture path and does not enable DXT5 upload in the live Vulkan backend.

The output is an offline capture input for Process 2's bundle builder. This
integration does not submit the captured guest draw through the runtime's live
Vulkan draw path and does not establish retail frontend, race, or image-parity
success. The guest runtime must first reach a supported indexed draw. The
adapter also fails closed when dynamic buffer history does not prove the bytes
needed for a draw.

The motivating retail evidence is SHIFT.exe SHA-256
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`, frame
14483, event 9694795: a triangle-list draw binds a DXT5 texture, but the prior
capture reports `snapshot_status=capture-failed`. The evidence motivates
managed DXT5 packet support; it does not prove that the Linux P-code runtime
reaches this draw.

## Checks

- A clean Release build of `shift_runtime` and
  `shift_runtime_recompiled_pcode_module_check` succeeded.
- The focused `shift_runtime_recompiled_pcode_module` CTest passed (1/1).
- Process 2's `shift_vulkan_d3d9_packet_capture_adapter` CTest passed (1/1),
  including its assertion that DXT5 is enabled on the capture adapter.
- This integration was not launched against the retail executable, so it does
  not add new frontend, race, or live Vulkan draw evidence.

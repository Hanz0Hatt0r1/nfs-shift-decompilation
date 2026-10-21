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
can provide the raw compressed mip bytes; Process 1 now has a separate DXT3
capability for the same guest-memory path. Process 2 must set that new bit in
its capture adapter before retail DXT3 textures can pass through the integrated
capture path. Neither bit enables compressed-texture upload in live Vulkan.

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

## Managed DXT3 runtime evidence

The original SHIFT.exe capture from the system-Wine run is
`shift_d3d9_capture.jsonl`, SHA-256
`db71d32484c35d97c2aa8645d8f439376d7c1caaaca6041aa565f7549870625b`. It
contains event 2691/frame 20 for a managed DXT3 texture (FOURCC `0x33545844`),
1024×512, one level, usage 0, pool 1. Event 37037/frame 281 records a captured
512×512 managed DXT3 payload, pitch 2048, 262144 bytes, SHA-256
`3148e693a19b0d95a2a021dea80ff78c93b42ec366e4a1b6b31b9e14638e5f96`.

P1 frontier v662 reported `unsupported D3D9 managed texture description` after
42,542,707 dispatches. The producer previously accepted managed A8R8G8B8,
A1R5G5B5, and capability-gated DXT5, but not DXT3. The trace does not yet
identify the exact guest call that produced the v662 error, so the captured
retail DXT3 descriptor is concrete evidence for the same unsupported-format
path, not proof that this single descriptor caused that run's failure.

P1 now represents DXT3 with its own adapter capability, uses the same 4×4,
16-byte block layout as DXT5, and carries those bytes through managed
`CreateTexture`, DDS loading, mip sizing, and block-aligned `LockRect`. DXT1,
DXT2, and DXT4 remain unsupported by the managed runtime path. The new
capability defaults to false; Process 2's capture adapter still needs its
matching change before the packet capture run can exercise this path.

## Checks

- A clean Release build of `shift_runtime` and
  `shift_runtime_recompiled_pcode_module_check` succeeded.
- The focused `shift_runtime_recompiled_pcode_module` CTest passed (1/1).
- New P1 DXT3 checks cover independent capability rejection, the captured
  512×512 pitch of 2048, block-aligned subrect addressing, and DXT3 DDS byte
  preservation; they pass in the focused CTest.
- Process 2's `shift_vulkan_d3d9_packet_capture_adapter` CTest passed (1/1),
  including its existing assertion that DXT5 is enabled on the capture
  adapter. Process 2's matching DXT3 assertion is pending its GitHub patch.
- This integration was not launched against the retail executable, so it does
  not add new frontend, race, or live Vulkan draw evidence.

# Process 2 D3D9 packet adapter — 2026-10-21

## Purpose

`native_vulkan/include/shift_vulkan_d3d9_packet_capture.hpp` and
`native_vulkan/src/d3d9_packet_capture_adapter.cpp` consume Process 1's
`RecompiledGuestD3d9DrawIndexedPrimitivePacket` synchronously. The adapter
wraps and forwards the existing D3D9 callbacks, caches vertex/index buffer
updates by guest resource ID, and writes each selected draw into an isolated
`SHIFT.D3D9RuntimeCaptureSchema/1` JSONL directory. The existing
`vulkan_d3d9_capture_bundle.py` then converts that capture into the native
Vulkan bundle format.

One directory is written per packet as
`draw_<guest-device>_<sequence>/capture.jsonl`. `event_index` is local to that
capture; `guest_draw_sequence` preserves Process 1's per-device sequence.
The packet has no retail frame number, so the isolated capture uses frame 0
instead of inventing one.

## State and payload handling

- Packet vectors and buffer update views are copied while their callbacks are
  active. The adapter never keeps references to borrowed data.
- Every stream frequency is emitted, along with the capture capability that
  makes those values usable by the current Vulkan bundle builder.
- Float constants retain DWORD bits and per-register write masks. The bundle
  builder compares those masks with the emitted constant events and writes the
  exact set-register bits to `constants.svcp`. Shader-referenced float
  registers without a set bit fail closed.
- Boolean constants retain their DWORD values and mask. A shader-used boolean
  without a set bit fails closed; any nonzero DWORD maps to shader `true`.
- Managed A8R8G8B8, A1R5G5B5, DXT1, DXT3, and DXT5 mip data is written as a DDS
  snapshot. DXT blocks are copied without recompression. Backend-owned texture
  bindings keep their resource ID and descriptor but receive no guest pixel
  payload; the existing bundle builder rejects them if an active sampler needs
  pixels.
- Render-target and depth descriptors retain the eight D3DSURFACE_DESC DWORDs.
  No render-target pixels are fabricated.
- The adapter verifies that packet buffer IDs and metadata match resources
  created through the wrapped callbacks. It requires complete buffer bytes for
  a full-buffer capture.

## Required Process 1 glue

Process 1 retains the runtime integration. Its `Runtime` must own one
`D3d9PacketCaptureAdapter` for the lifetime of the wrapped adapter table and
call `install(adapter_info, error)` after constructing the existing callback
table. `install` wraps the callbacks and saves the original context for
forwarding. Process 1 must compile the P2-owned adapter source into the runtime
target; no P1 runtime or P-code files were changed in this branch.

The current packet header is in P1 PR #2140, commit
`476f9a75c9d5ae7107214c5f693bd462a3f3296f`. CMake enables the focused adapter
check when that public packet type is present. A local build against the exact
PR header used:

~~~bash
cmake -S native_vulkan -B /tmp/nfs-shift-d3d9-packet-build \
  -DSHIFT_RECOMPILED_RUNTIME_INCLUDE_DIR=/tmp/p1-d3d9-contract/native_runtime/include
cmake --build /tmp/nfs-shift-d3d9-packet-build \
  --target shift_vulkan_d3d9_packet_capture_check -j2
/usr/bin/ctest --test-dir /tmp/nfs-shift-d3d9-packet-build \
  -R shift_vulkan_d3d9_packet_capture_adapter --output-on-failure
~~~

When installed, this capture adapter sets `supports_dxt5_texture=true` so the
guest can create managed DXT5 textures and include their raw mip blocks in the
packet. In the current P1 runtime, managed DXT5 storage is guest-owned memory;
it does not call the downstream `create_texture` callback. That callback is
used for backend-owned BGRA8 render targets. This capability opt-in is limited
to the capture adapter. It does not enable DXT5 on the live Vulkan texture
upload path, which still has no DXT5 upload implementation.

## Limits

- The update callback contract has no D3DLOCK flags. For a dynamic vertex or
  index buffer, a partial update could be `D3DLOCK_DISCARD` or a preserving
  update. The adapter marks that buffer ambiguous and returns an explicit
  callback error at draw time instead of replaying possibly stale bytes. Full
  buffer updates are accepted. A future packet-interface version can add lock
  flags or a post-unlock full-buffer snapshot.
- Non-finite float constants cannot be represented as JSON numbers under the
  current event schema; their packet capture fails explicitly. Finite values
  include exact `values_bits` alongside the standard numeric fields.
- Capturing a packet creates a replay input. It does not submit that packet to
  the live runtime Vulkan command buffer. Process 1 has to install the adapter,
  and the resulting bundle still needs the existing Vulkan consumer.
- The frame-14483 example draw event 9694795 binds a managed DXT5 texture whose
  current raw capture marked the snapshot failed. Process 1 is addressing that
  capture path. The P2 adapter can serialize DXT5 bytes when a packet provides
  them, but this is not evidence that the example draw is yet replayable.

The C++ test exercises copied resource views, callback forwarding, sequence
and frequency fields, constant masks/bits, backend-owned texture behavior,
A8R8G8B8 and DXT5 DDS output, capture limits, and explicit failure for partial
dynamic-buffer updates. A generated capture was parsed by the existing bundle
reader. `tests/test_vulkan_d3d9_capture_bundle.py`,
`tests/test_shader_backend.py`, and `tests/test_vulkan_d3d9_draw.py` pass (52
tests). These checks do not claim a P1 runtime draw, Vulkan validation of the
new packet adapter path, or retail frame parity.

# Process 1 D3D9 indexed-draw packet — 2026-10-21

## Evidence and scope

The pinned original `SHIFT.exe` capture records this sequence in frame 14483:

- `SetVertexDeclaration` at event 9694765;
- stream 0 VB `0x28433930`, offset 0, stride 24 at event 9694766;
- index buffer `0x284339b0` at event 9694767;
- texture stage 0 `0x2ebecb98` at event 9694786;
- `DrawIndexedPrimitive` at event 9694795: triangle list, base vertex 0, minimum vertex 0, six vertices, start index 0, two primitives.

The executable and raw-capture hashes are recorded in
[`process1_d3d9_guest_state_capture_20261021.json`](../evidence/process1_d3d9_guest_state_capture_20261021.json).
This is original-game API evidence. It does not prove that P-code execution
reached the draw.

## Runtime implementation

The P-code D3D9 device now handles `DrawIndexedPrimitive` (slot 82),
`Set/GetStreamSourceFreq` (slots 102/103), and the float and boolean
shader-constant setters/getters. Indexed draws require an active
`BeginScene`/`EndScene` pair and an index buffer, as described by Microsoft's
[BeginScene](https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-beginscene)
and [DrawIndexedPrimitive](https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-drawindexedprimitive)
documentation. The draw callback receives a version-1, backend-neutral packet.
Resource IDs refer to objects already created or updated through the existing
adapter callbacks. The callback is synchronous;
packet-owned vectors are valid only until it returns.

The packet carries draw arguments, all 16 stream bindings and frequencies, the
index-buffer description, declaration elements, shader token streams, current
float/bool register values, sorted texture/render/sampler state, viewport,
render-target and depth-surface descriptions, and the last clear values.
Float and boolean register data also has per-register set masks. A zero in the
value array without a matching set bit is not claimed as an original device
default. This preserves which values were explicitly written; Direct3D 9's
shader reference says `Get***ShaderConstant*` retrieves values set through the
matching `Set***ShaderConstant*` methods.
Managed texture pixels are copied into tightly packed mip-level vectors.
Surface descriptions use the D3DSURFACE_DESC field order: Format, Type, Usage,
Pool, MultiSampleType, MultiSampleQuality, Width, Height. Backend-owned render
target textures carry their resource ID and description; their pixels are not
guest-readable and are not copied into the packet.

The mip-size calculation now rejects overflow before allocating guest memory or
copying DDS payloads. The regression uses an A1R5G5B5 DDS with width
1,845,248,881, height 3,748,832,529, and 32 levels: its exact byte count exceeds
`uint64_t`, while unchecked wraparound produced only 39,535,162 bytes. The
bounded calculator rejects that chain before any payload read or allocation.

## Verification

Passed on the current Process 1 branch:

~~~bash
cmake --build native_runtime/build --target shift_runtime_recompiled_pcode_module_check -j2
/usr/bin/ctest --test-dir native_runtime/build -R '^shift_runtime_recompiled_pcode_module$' --output-on-failure
cmake --build native_runtime/build --target shift_runtime -j2
git diff --check
~~~

The test covers guest ABI stack cleanup, stream frequencies, constant
round-trips and range failures, packet snapshots, callback errors, invalid
point-list draws, and the overflowing DDS regression.

Latest P-code evidence remains v664: 180 host frames, 3,939 unique guest
functions, no recorded validation errors, and no guest draw translation. The
frontend and race remain unconfirmed. A new retail P-code probe could not be
run in this environment because the retail PE, game-data, and P-code artifact
environment variables are unset.

Process 2's latest mainline evidence is a focused Vulkan submission of one
captured retail draw, with deterministic repeat output and zero validation
errors. Its report explicitly says this capture replay is not connected to
Process 1's runtime. The P1 callback adapter handoff is therefore the next
integration boundary; this change does not alter renderer or Vulkan files.
See [`PROCESS_2_D3D9_VULKAN_CAPTURE_REPLAY_20261021.md`](PROCESS_2_D3D9_VULKAN_CAPTURE_REPLAY_20261021.md)
and [`shift_d3d9_vulkan_first_focused_draw_20261021.json`](../evidence/shift_d3d9_vulkan_first_focused_draw_20261021.json)
on current main.

## Limits

- The draw callback is not wired to a Process 2 consumer yet; absent or failed
  callbacks return `D3DERR_NOTAVAILABLE`.
- This handles indexed draws only. `DrawPrimitive`, `DrawPrimitiveUP`,
  `DrawIndexedPrimitiveUP`, and integer shader-constant methods remain outside
  this packet path.
- Managed texture snapshot support is limited to formats accepted by the
  current guest texture implementation. A8R8G8B8 is four bytes per pixel and
  A1R5G5B5 is two; X8R8G8B8 (format 22) is not currently accepted for this
  managed-memory path. Render-target textures are backend-owned.
- Managed texture levels are restricted by the existing 64 MiB allocation
  ceiling. Shader constant arrays represent the current SM3-sized register
  ranges; this is not a complete D3D9 capability-driven implementation.
- No P-code frontend, retail rendering parity, or race launch is proven by the
  focused native regression or by dispatch counts.

For the constant retrieval rule, see Microsoft's
[Direct3D 9 shader-constant reference](https://learn.microsoft.com/en-us/windows/win32/direct3dhlsl/dx9-graphics-reference-asm#direct3d-9-shader-constants).

# Process 1: guest D3D9 draw state and shaders

## Change

The guest `IDirect3DDevice9` vtable now routes `Set/GetVertexDeclaration`,
`Set/GetStreamSource`, `Set/GetIndices`, and `Set/GetTexture` to the P-code
runtime. These methods store per-device guest state, including stream
offset/stride. `SetTexture` AddRefs a newly bound texture and releases a replaced
binding; setting `NULL` unbinds it. Getters AddRef live objects they return.
Calls reject invalid device-owned objects, streams outside the 16 D3D9 stream
slots, and invalid getter output pointers. Releasing a bound guest object clears
any stale state address.

The guest device also creates vertex and pixel shader COM objects from their
original D3D9 token arrays. It keeps tokens through the END token, including
embedded comments, and exposes `QueryInterface`, `AddRef`, `Release`,
`GetDevice`, and `GetFunction`. `Set/GetVertexShader` and
`Set/GetPixelShader` preserve per-device bindings and COM references. The
bounded reader rejects a wrong-stage/version stream, an invalid guest pointer,
or a stream without END within 262,144 DWORDs. It does not compile shaders,
translate them to SPIR-V, or submit draws; it also does not fully validate D3D9
instruction semantics.

The texture reference behavior follows Microsoft's [`SetTexture`](https://learn.microsoft.com/en-us/windows/win32/direct3d9/texture-resources)
and [`GetTexture`](https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-gettexture) documentation.

Focused regression coverage checks state/shader vtable slots, stream
buffer/offset/stride round-trip, returned-buffer reference count, invalid
stream index, index-buffer round-trip, declaration round-trip, texture
binding/refcount, same-pointer rebind, getter ownership, null unbinding, and
invalid texture stage. Shader checks cover both stages, stage/version
rejection, token and comment preservation, `GetFunction` size/copy behavior,
COM identity and references, parent-device lookup, cross-stage rejection, and
NULL unbinding. The shader fixture is a small synthetic SM3 token stream; it
tests the guest ABI and bounded copy path, not the game's shader compiler or a
retail Vulkan draw.

## Retail evidence

The original retail PE32 capture records `CreatePixelShader` and
`CreateVertexShader` events in frame 14. The captured streams begin with SM3.0
tokens `0xffff0300` (pixel) and `0xfffe0300` (vertex); the first observed
payloads are 144 and 404 bytes respectively. The full capture has 610 pixel
shader and 598 vertex shader creation events, with 261 distinct shader
signatures across those events. Bytecode is not copied into this repository;
the compact event facts and source hash are in the evidence JSON.

The same original retail PE32 capture records `SetVertexDeclaration`,
`SetStreamSource(stream=0, offset=0, stride=24)`, `SetIndices`, and
`SetTexture(stage=0)` in frame 14483 before `DrawIndexedPrimitive` (triangle
list, six vertices, two primitives). The compact event extract, executable
hash, and raw capture hash are in
[`process1_d3d9_guest_state_capture_20261021.json`](../evidence/process1_d3d9_guest_state_capture_20261021.json).

This establishes that these guest state calls are on an observed original-game
draw path. It does not establish that the recompiled P-code runtime reached
that draw. The old v520 scheduler trace showed `ResumeThread` succeed while
the predicate writer was unknown; v527 later observed the worker write
`0x00000006`, and the poll returned `1`. The bounded v662 and fresh v664 P-code
runs reached `host-frame-loop` with no recorded P-code blocker. v664 completed
180 host frames and reported the same 3,939 unique functions as v662, but no
guest draw translation or retail rendering. Its raw dispatch count varied
slightly from v662 and is not launch evidence. The v663 targeted trace timed
out without final frontier metrics. P-code frontend and race readiness remain
unconfirmed.

## Scope and limits

This change is confined to `native_runtime` guest API dispatch and its focused
fixture. It does not add draw submission, capture-file output, or Vulkan
rendering. No Process 2 renderer files were changed. The test proves the
implemented guest ABI and state round-trips; it is not a retail gameplay test,
proof of shader compilation, or proof of complete D3D9 COM lifetime behavior.

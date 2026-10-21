# Process 1: guest D3D9 draw-state calls

## Change

The guest `IDirect3DDevice9` vtable now routes `Set/GetVertexDeclaration`,
`Set/GetStreamSource`, `Set/GetIndices`, and `Set/GetTexture` to the P-code
runtime. These methods store per-device guest state, including stream
offset/stride. `SetTexture` AddRefs a newly bound texture and releases a replaced
binding; setting `NULL` unbinds it. Getters AddRef live objects they return.
Calls reject invalid device-owned objects, streams outside the 16 D3D9 stream
slots, and invalid getter output pointers. Releasing a bound guest object clears
any stale state address.

The texture reference behavior follows Microsoft's [`SetTexture`](https://learn.microsoft.com/en-us/windows/win32/direct3d9/texture-resources)
and [`GetTexture`](https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-gettexture) documentation.

Focused regression coverage checks vtable slots, stream buffer/offset/stride
round-trip, returned-buffer reference count, invalid stream index, index-buffer
round-trip, declaration round-trip, texture binding/refcount, same-pointer
rebind, getter ownership, null unbinding, and invalid texture stage.

## Retail evidence

The original retail PE32 capture records `SetVertexDeclaration`,
`SetStreamSource(stream=0, offset=0, stride=24)`, `SetIndices`, and
`SetTexture(stage=0)` in frame 14483 before `DrawIndexedPrimitive` (triangle
list, six vertices, two primitives). The compact event extract, executable
hash, and raw capture hash are in
[`process1_d3d9_guest_state_capture_20261021.json`](../evidence/process1_d3d9_guest_state_capture_20261021.json).

This establishes that these guest state calls are on an observed original-game
draw path. It does not establish that the recompiled P-code runtime reached
that draw. The old v520 scheduler trace showed `ResumeThread` succeed while
the predicate writer was unknown; v527 later observed the worker write
`0x00000006`, and the poll returned `1`. The latest bounded v662 P-code run
reached `host-frame-loop` with no recorded P-code blocker; the v663 targeted
trace timed out without final frontier metrics. P-code frontend and race
readiness remain unconfirmed.

## Scope and limits

This change is confined to `native_runtime` guest API dispatch and its focused
fixture. It does not add draw submission, shader creation, capture-file output,
or Vulkan rendering. No Process 2 renderer files were changed. The test proves
the implemented guest ABI and state round-trips; it is not a retail gameplay
test or proof of complete D3D9 COM lifetime behavior.

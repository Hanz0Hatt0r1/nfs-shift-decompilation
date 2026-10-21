# Process 1: guest D3D9 draw-state calls

## Change

The guest `IDirect3DDevice9` vtable now routes `Set/GetVertexDeclaration`,
`Set/GetStreamSource`, and `Set/GetIndices` to the P-code runtime. Setters retain
the per-device guest addresses and stream offset/stride. Calls reject invalid
device-owned objects, streams outside the 16 D3D9 stream slots, and invalid
getter output pointers. Getters return the stored state and AddRef live objects
they return. Releasing a bound guest object clears its stale state address.

Focused regression coverage checks vtable slots, stream buffer/offset/stride
round-trip, returned-buffer reference count, null unbinding, invalid stream
index, index-buffer round-trip, and declaration round-trip.

## Retail evidence

The original retail PE32 capture records `SetVertexDeclaration`,
`SetStreamSource(stream=0, offset=0, stride=24)`, and `SetIndices` in frame
14483 before `DrawIndexedPrimitive` (triangle list, six vertices, two
primitives). The compact event extract, executable hash, and raw capture hash
are in [`process1_d3d9_guest_state_capture_20261021.json`](../evidence/process1_d3d9_guest_state_capture_20261021.json).

This establishes that these guest state calls are on an observed original-game
draw path. It does not establish that the recompiled P-code runtime reached
that draw. The latest bounded P-code run reached `host-frame-loop` with no
recorded P-code blocker; the longer targeted trace timed out without final
frontier metrics. P-code frontend and race readiness remain unconfirmed.

## Scope and limits

This change is confined to `native_runtime` guest API dispatch and its focused
fixture. It does not add draw submission, shader creation, capture-file output,
or Vulkan rendering. No Process 2 renderer files were changed. The test proves
the implemented guest ABI and state round-trips; it is not a retail gameplay
test or proof of complete D3D9 COM lifetime behavior.

# Phase 343: BMW D3D9 buffer lifecycle parity

Phase 343 closes the creation-instance side of the BMW M3 geometry runtime proof.

## Runtime buffer objects

The native D3D9 producer now emits successful CreateVertexBuffer and CreateIndexBuffer events. The runtime trace preserves those creation records and attaches them to later SetStreamSource and SetIndices bindings by pointer.

## BMW M3 evidence

The frame-30444 geometry evidence identifies the BMW body vertex buffer as 0x27b39460 with a 76-byte stride and 3,550 vertices, yielding 269,800 bytes.

The six primitive index buffers are INDEX16 and have exact byte lengths derived from their MEB index counts:

- BADGING: 150 indices → 300 bytes;
- PAINT primitive 1: 6,294 indices → 12,588 bytes;
- PAINT primitive 2: 7,386 indices → 14,772 bytes;
- WINDOWS: 612 indices → 1,224 bytes;
- GLOSS BLACK: 576 indices → 1,152 bytes;
- LIGHTSGLASS: 84 indices → 168 bytes.

The supplied shift_resources.txt contains successful creation records for exactly these pointers before the checked frame-30444 DrawIndexedPrimitive calls.

## Gate

`bmw_runtime_buffer_lifecycle_parity.py` emits `SHIFT.BMWM3RuntimeBufferLifecycleParity/1` and fails closed on wrong MEB identity, missing creation instances, wrong byte sizes, wrong INDEX16 format or creation after the target draw boundary.

## Boundary

This proves runtime pointer → D3D9 creation-instance identity and exact creation-size parity. It does not claim that the runtime buffer payload bytes equal the reconstructed MEB bytes.

The next geometry step is raw VertexBuffer9/IndexBuffer9 lock payload capture and byte-for-byte comparison against the reconstructed stride-76 VB and uint16 IB.
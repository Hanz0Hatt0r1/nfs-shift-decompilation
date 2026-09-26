# Phase 344: BMW D3D9 buffer payload parity

Phase 344 extends the BMW M3 geometry lifecycle proof from CreateVertexBuffer/CreateIndexBuffer metadata to optional raw lock payload capture.

## Capture

The native D3D9 producer hooks vertex/index buffer Lock and Unlock methods.
Full-buffer evidence is accepted only when:

- the lock begins at offset 0;
- SizeToLock is 0 (whole buffer) or equals the queried buffer length;
- GetDesc succeeds;
- the lock and unlock calls succeed.

The payload is copied before the original Unlock call. Each binary payload is referenced by a versioned buffer_payload JSONL event.

## BMW target

The exact body MEB is 3,550 vertices with stride 76, giving a 269,800-byte canonical runtime vertex buffer. Its six primitive index ranges require 300, 12,588, 14,772, 1,224, 1,152 and 168 bytes as INDEX16 buffers.

Phase 343 already proved the corresponding runtime buffer pointers and Create* sizes. Phase 344 adds the missing byte-level capture boundary.

## Byte parity

bmw_runtime_buffer_payload_parity.py compares:

- the complete captured BMW vertex buffer against the canonical stride-76 VB bytes;
- each captured runtime index buffer against the exact corresponding slice of the canonical uint16 IB bytes.

For an index buffer, the expected slice is derived from the target draw's start_index and primitive_count. The comparator requires exact byte equality.

## Ordering

A payload is eligible only when its event index lies after the current buffer creation event and at or before the target DrawIndexedPrimitive event. This prevents pointer reuse or future writes from authenticating the wrong draw.

## Current evidence boundary

The supplied historical traces prove the buffer creation instances and exact sizes, but contain no BMW buffer payload events. Therefore Phase 344 tooling is ready while raw runtime VB/IB byte identity remains not-proven until an opt-in capture is produced.

The next proof result will be a complete runtime VB plus six INDEX16 payload matches, after which the geometry byte boundary can be promoted from lifecycle parity to raw-byte parity.
# Phase 341: complete and partial DDS mip-chain parity

Phase 341 расширяет Phase 340 с одного level-0 payload до всей доступной
runtime mip-chain.

## Runtime capture

The native D3D9 producer now captures every write-side `IDirect3DTexture9::LockRect`
level when raw payload capture is enabled. The lock state is keyed by
`texture pointer + level`, so simultaneous locks of different mip levels do not
overwrite one another.

Each `texture_payload` event already carries the level number and event index.
The runtime trace retains these events both in the draw-local snapshot and in an
ordered top-level payload list.

## DDS comparison

`runtime_texture_content_parity.py` splits a DDS into its exact mip-level payloads
for DXT1/DXT3/DXT5 and 32-bit uncompressed textures.

For every captured runtime level:

- byte count must match;
- SHA-256 of the raw payload must match the exact DDS level bytes;
- a mismatch is a hard blocker.

The report distinguishes:

- `coverage_status=complete`: every expected mip level was captured and matched;
- `coverage_status=partial`: one or more levels are missing, but every captured
  level matched;
- `coverage_status=none`: no raw payload was observed.

A partial chain can therefore prove the identity of the captured subset without
pretending that missing mip levels were checked.

## Ordering and lifetime

A raw payload is eligible only when:

`CreateTexture event < payload event <= target DrawIndexedPrimitive event`

This prevents both future payloads and payloads from an earlier reuse of the same
texture pointer from authenticating the current draw.

The runtime trace exports the draw's own `event_index` so the ordering rule remains
machine-checkable.

## Boundary

Complete mip-chain parity is still not the same as a DDS-file byte-for-byte match:
the DDS header itself is not present in the runtime surface payload, and unsupported
resource formats are outside this comparator.

Cube texture raw payloads remain a separate Phase 342 target.

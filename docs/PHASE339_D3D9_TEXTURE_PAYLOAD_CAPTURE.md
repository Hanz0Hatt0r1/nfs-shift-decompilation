# Phase 339: raw D3D9 texture payload capture

Phase 337 established the runtime texture resource-shape gate and Phase 338 made
s1/s2/s4 PPM snapshots part of the normal texture-snapshot path. PPM preserves
RGB content but not the original compressed surface bytes.

## Change

The native D3D9 producer can now optionally hook:

- `IDirect3DTexture9::LockRect`;
- `IDirect3DTexture9::UnlockRect`.

For successful write-side level-0 locks, the producer copies the locked bytes before
the original unlock call and stores them in a standalone binary file. A
`texture_payload` JSONL event records:

- texture object pointer;
- resource type;
- level;
- width/height;
- lock pitch;
- D3D format and pool;
- captured byte count;
- payload file path.

The capture is enabled only with
`SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOADS=1`.

## Why this is stronger

For DXT resources the locked payload is the compressed block data for the selected
level. That gives the later parity stage a direct byte-comparison path:

`runtime LockRect level-0 bytes -> retail DDS base-level compressed bytes`.

This is stronger than comparing only rendered PPM RGB output and avoids treating
matching dimensions as identity.

## Boundary

The producer does not add a DDS header to the captured payload and does not infer
the originating SHIFT resource path. Texture-object identity and archive DDS identity
remain separate evidence joins.

Cube textures continue to use the existing six-face PPM snapshot path; raw cube
payload capture is intentionally outside this phase.

## Regression

Capture-schema and runtime-trace tests cover validation and draw-snapshot retention
of `texture_payload` events.

## Next step

Use the raw payload file from a real BMW paint capture to compare s1/s2/s4 level-0
bytes against the exact BFF DDS entries. In particular, the 1024×1024 s1 runtime
object must be treated as generated/transformed until byte/content evidence proves
its relationship to `common_paint.dds`.

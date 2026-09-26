# Phase 342: D3D9 cube texture payload capture

Phase 342 extends the raw texture capture boundary from 2D textures to cube textures.

## API boundary

IDirect3DCubeTexture9 exposes LockRect and UnlockRect with explicit face and mip-level parameters. The native producer hooks those methods on created cube-texture objects.

Only successful write-side full-surface locks are captured. A sub-rectangle or read-only lock is not promoted to complete surface evidence.

## Unified payload contract

Cube payloads use the existing SHIFT texture_payload event. Additional fields:

- resource_type_name = cube_texture;
- face = numeric D3DCUBEMAP_FACES index 0..5;
- face_name = px, nx, py, ny, pz or nz;
- level = mip level.

The lock state is keyed by texture pointer + face + level. Raw bytes are copied before the original UnlockRect call and stored in a separate binary file.

## Runtime trace

d3d9_runtime_trace.py preserves cube payload records in the same ordered payload lists as 2D records, including draw-local snapshot retention.

## Current BMW boundary

The known BMW paint environmentMap object at s3 is a runtime-global 256x256 A16B16G16R16F render-target cube in D3DPOOL_DEFAULT. No static retail environment DDS has been established in the supplied BMW/RENDER archives, so Phase 342 does not claim content parity for s3.

The existing face-level PPM readback remains the appropriate path for non-lockable render-target cube resources.

## Evidence boundary

Phase 342 proves the instrumentation path:

runtime cube texture pointer -> CreateCubeTexture instance -> face/mip raw payload

when the object is lockable and a matching write-side full-surface LockRect occurs.

It does not infer the originating game resource path or DDS identity.
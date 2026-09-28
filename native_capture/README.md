# SHIFT D3D9 capture producer

Windows-side research capture producer for the retail Direct3D 9 runtime.

## Captured API surface

- CreateVertexDeclaration / SetVertexDeclaration
- SetStreamSource / SetIndices
- CreateVertexBuffer / CreateIndexBuffer
- CreateVertexShader / SetVertexShader
- SetVertexShaderConstantF
- CreatePixelShader / SetPixelShader
- SetPixelShaderConstantF
- SetTexture
- CreateTexture / CreateCubeTexture
- DrawIndexedPrimitive

Present is a frame boundary.

## Extended evidence

Optional capture paths cover:

- texture LockRect/UnlockRect payloads;
- cube face × mip identity;
- VB/IB Lock/Unlock payloads;
- resource creation lifecycle;
- draw-local state snapshots.

Binary payloads are separate artifacts referenced by versioned events.

## Build

```bash
cmake -S native_capture -B native_capture/build -A Win32
cmake --build native_capture/build --config Release
```

Place the resulting d3d9.dll beside the authorized test executable.

## Evidence rules

The producer records runtime observations; it does not invent MEB identity.

Same-instance proof is a later correlation across MEB/resource SHA, declaration, buffers, shader objects, textures and exact draw index.

Runtime authenticity is provenance metadata, not an automatic truth claim.

## Linux alternative

apitrace tooling can extract unique BMW draw/resource instances and payloads without first producing a multi-gigabyte text dump.

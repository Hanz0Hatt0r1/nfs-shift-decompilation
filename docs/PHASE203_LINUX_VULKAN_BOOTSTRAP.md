# Phase 203 — Linux as the primary render lab, Vulkan as the native backend

Phase 203 changes the renderer priority without changing the evidence rules.

## Decision

Android is deferred until the game has been substantially/fully decompiled and the
desktop renderer/runtime contracts are stable.

Linux becomes the primary development and validation platform for the renderer. The
native rendering target is Vulkan.

The existing software reference renderer remains an oracle, not a competing backend.

## Target pipeline

```text
Retail BFF / runtime evidence
            |
            v
        SHIFT IR
            |
            v
     RenderCommand/1
            |
        +---+---+
        |       |
        v       v
 reference    Vulkan
 renderer    submission
 oracle            |
                   v
                SPIR-V
                   |
                   v
             Vulkan device
```

The neutral `RenderCommand/1` boundary is important: it prevents MEB parsing, material
linking and evidence logic from becoming tied to Vulkan APIs.

## Phase sequence

### 203 — Bootstrap

- optional Linux Vulkan CMake target;
- loader/device/queue capability probe;
- repository contract documenting Vulkan as the native desktop backend.

### 204 — Headless Vulkan submission

- create device and graphics queue;
- create a small offscreen image;
- submit a deterministic triangle;
- write the image to a host-visible buffer;
- hash the result.

This phase must not depend on a window system.

### 205 — RenderCommand vertex/index path

- translate verified `VertexLayout` into Vulkan vertex bindings/attributes;
- upload one real BMW MEB mesh;
- upload indices;
- reproduce the geometry-preview checkpoint.

### 206 — Shader path

- translate proven `ShaderProgram/1` operations to SPIR-V;
- preserve D3D9 register semantics through an explicit constant ABI;
- establish VS->PS varying linkage;
- compare Vulkan output against the software reference renderer.

### 207 — Texture/material path

- DDS decode/upload;
- sampler state;
- 2D and cube resources;
- material constant payload;
- real BMW shader permutation.

### 208 — Runtime parity

- feed the same accepted `RenderCommand/1` from the D3D9 capture gate;
- compare runtime-derived constants/resources against Vulkan submission;
- keep same-instance proof separate from renderer readiness.

### 209+ — scene/runtime expansion

SGB, scene composition, camera, animation and gameplay systems stay downstream of the
proven renderer boundary.

Android then becomes another frontend/backend consumer of the stable neutral IR rather
than the platform on which the renderer is first debugged.

## What this phase does not claim

The Vulkan backend is not yet a renderer. Phase 203 only establishes its native build
boundary and a machine-checkable Vulkan capability probe. No retail BMW image is
claimed from Vulkan until the later RenderCommand and shader stages are implemented and
cross-checked against the existing oracle.

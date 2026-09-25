# Phase 219 — SPIR-V descriptor reflection

Phase 219 adds a dependency-free reflection layer for the subset of SPIR-V metadata
needed by the native bundle runner.

The reflected contract includes:
- descriptor set and binding;
- sampler2D vs samplerCube resource type;
- uniform-buffer/storage-buffer classification;
- shader stage;
- optional OpName;
- descriptor-binding collisions.

The implementation is intentionally not a general SPIR-V decompiler. It does not
interpret shader instructions or infer semantics from sampling behavior. Unsupported
descriptor/type/storage combinations remain blockers.

This closes the Phase 218 blocker that prevented a native runner from constructing a
descriptor layout for mixed 2D and cube sampler resources.

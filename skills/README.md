# Project-local skills

These are small, repository-specific operational skills. They adapt public skill
workflows to the evidence policy and data contracts of the SHIFT decompilation.

| Skill | Purpose | Upstream reference |
|---|---|---|
| ghidra | headless/source-correlated binary analysis | mitsuhiko/agent-stuff |
| d3d9-re | D3D9 declaration/binding/runtime evidence | project-specific |
| shader-re | D3D9 shader IR → GLSL/reference parity | GameDev shader workflow |
| bmw-golden-render | real BMW M3 deterministic render slice | project-specific |

The repository intentionally does not vendor third-party skill implementations.
Only the project-specific workflow and the minimum references needed to reproduce it
are kept in-tree.

Android-specific tooling is deferred until the proven desktop render boundary is
stable; the Android CLI/profiling skills remain a later integration stage.
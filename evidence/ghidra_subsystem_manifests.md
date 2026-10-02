# Ghidra subsystem manifests

The headless Ghidra export now supports a second-stage subsystem manifest pass.
The goal is not to rename every `FUN_*` symbol. It is to promote only identities
that are directly supported by exact string xrefs and, where useful, an expected
direct-call shape.

## Source

The input is `SHIFT.GhidraEvidenceDatabase/1` from the analyzed retail
`SHIFT.exe`. The manifest builder consumes only:

- `binary.json` and `manifest.json` for source identity;
- `functions.jsonl` for exact function boundaries and Ghidra names;
- `callgraph.jsonl` for direct call relationships;
- `strings_xrefs.jsonl` for exact code-to-string relationships.

`vtables.json`, `constructors.jsonl` and `factories.jsonl` are deliberately not
used for semantic promotion because they contain heuristic candidates.

## Renderer identities

The export provides exact diagnostic/function-name strings for these routines:

| Address | Promoted alias | Additional call constraint |
|---|---|---|
| `0x00854d30` | `CMeshPrimitiveType::ApplyVertexDeclaration` | direct call to `0x0082e510` |
| `0x00854da0` | `CMeshPrimitiveType::SetVertexBufferAsStreamSource` | direct call to `0x0082e110` |
| `0x00854e10` | `CMeshPrimitiveType::SetIndexBufferAsSource` | direct call to `0x0082e110` |
| `0x00854e70` | `MWL::Renderer::WinRenderer::CMeshPrimitiveType::CreateMeshFromMemoryBuffers` | direct calls to `0x00830f80` and `0x00853c40` |
| `0x00856030` | `CInstancedMeshPrimitiveType::ApplyVertexDeclaration` | direct call to `0x0082e510` |
| `0x00856750` | `CLightweightMeshPrimitiveType::ApplyVertexDeclaration` | direct call to `0x0082e510` |
| `0x008587e0` | `MWL::Renderer::WinRenderer::CMeshPrimitiveType::LoadXMLMeshFromResource` | exact string xref |

This turns the previously recovered D3D9 declaration functions into a more
explicit chain: mesh primitive methods call the already established declaration
wrapper/canonicalization helpers instead of being identified only by proximity.

## Physics and vehicle identities

Exact source diagnostic strings identify:

| Address | Promoted alias |
|---|---|
| `0x0074ddc3` | `MWL::Core::PhysicsParticipant::Restart` |
| `0x00750080` | `MWL::Core::LoadCollisionStream` |
| `0x007506b0` | `MWL::Core::PhysicsInit` |
| `0x00798df0` | `MWL::Core::Vehicle::InitVehicle` |

These names refine existing physics evidence without changing the recovered
contracts. For example, `FUN_00750080` was already established as the CSM
loader and `FUN_007506b0` as the PhysX startup routine; the Ghidra database adds
the retail diagnostic identities that name those routines directly.

## Scene graph identity

`0x0068ba9e` references the exact diagnostic string
`MWL::GraphicsEngine::CSceneGraph::AddUpdate` from
`.\\Source\\SceneGraph\\CSceneGraph.cpp`. The subsystem manifest therefore
promotes that alias directly.

## AI registration stubs

AI registration functions are handled differently. The class string plus the
known registration-call shape establishes that a function is a registration
stub, but does **not** establish a constructor or runtime method name.

The first promoted set includes:

- `0x00a84220` — `AIPolylinePath`;
- `0x00a84460` — `AISpline`;
- `0x00a844f0` — `AISplineInfo`;
- `0x00a84580` — `AISegmentPath`;
- `0x00a84610` — `AIPolyPathNode`;
- `0x00a846a0` — `AIPathNode`;
- `0x00a84730` — `AIPath`;
- `0x00a847b0` — `AIMarker`;
- `0x00a84840` — `AICamera`;
- `0x00a848d0` — `AISmartObjectBase`;
- `0x00a84960` — `AISmartObjectObj`.

Each must contain the exact class string and direct calls to the recovered
registration shape (`0x00631740`, `0x00630fe0`, `0x006310c0`, `_atexit`).

## Tool

Run:

```bash
python3 tools/ghidra/build_subsystem_manifests.py \
  out/shift_ghidra_database \
  out/shift_ghidra_subsystems
```

It writes:

```text
out/shift_ghidra_subsystems/
    index.json
    renderer.json
    physics.json
    vehicle.json
    scene_graph.json
    ai.json
```

`index.json` contains only promoted semantic aliases. Each subsystem file keeps
both successful and failed checks so a future binary or Ghidra analysis change
cannot silently alter the evidence boundary.

## Evidence boundary

The manifests are intentionally conservative:

- exact string xrefs can identify functions when the string is itself a fully
  qualified retail diagnostic/function identity;
- selected renderer identities additionally require the expected direct call;
- AI class-name registrations remain `class-registration-stub` evidence only;
- generic vtable, constructor and factory candidates remain heuristic and are
  not used to assign names.

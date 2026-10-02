# Ghidra program-database cross-check evidence

This note records the first direct join against the machine-readable Ghidra
program-database export produced by `tools/ghidra/ShiftEvidenceExporter.java`.
The purpose is to cross-check existing source/PE conclusions with exact Ghidra
function, call and string-xref observations without promoting the exporter's
heuristic vtable/factory candidates to recovered contracts.

## Export identity

The supplied export reports:

- format: `SHIFT.GhidraEvidenceDatabase/1`;
- program: `SHIFT.exe`;
- PE MD5: `705af8b420e5eb1e3834ac43d5533c6b`;
- language: `x86:LE:32:default`;
- image base: `0x00400000`;
- pointer size: 4 bytes.

The exporter records MD5, not SHA-256, so this note does not claim a new
SHA-256 identity equivalence beyond the existing retail evidence set.

## Corpus size

The supplied Ghidra database contains:

| Direct/candidate layer | Records |
|---|---:|
| functions | 41,538 |
| call edges | 200,598 |
| strings | 48,090 |
| globals | 218,700 |
| static data | 55,066 |
| switch candidates | 1,370 |
| vtable candidates | 2,533 |
| constructor candidates | 1,303 |
| factory candidates | 5,251 |

`functions.jsonl`, `callgraph.jsonl` and `strings_xrefs.jsonl` are used below as
direct observations. The generic vtable/constructor/factory candidate sets are
kept as discovery aids only.

## D3D9 / mesh pipeline

The program database independently strengthens several existing renderer
anchors:

- `FUN_00854d30` references the exact diagnostic/name string
  `CMeshPrimitiveType::ApplyVertexDeclaration` and directly calls
  `FUN_0082e510`. This supports the existing interpretation of
  `FUN_0082e510` as the vertex-declaration application wrapper boundary.
- `FUN_00854e70` references
  `MWL::Renderer::WinRenderer::CMeshPrimitiveType::CreateMeshFromMemoryBuffers`.
  Its direct call graph includes `FUN_00853c40` at instruction `0x008552c3`
  and `FUN_00830f80` at `0x00855c23`, joining Usage conversion and declaration
  canonicalization/creation to the concrete mesh-construction path.
- the same `FUN_00854e70` string set contains source/assertion labels for
  vertex element formats/usages/data, index-buffer metadata and required
  position data. These are direct semantic anchors for the recovered mesh
  specification fields rather than names inferred from table shape alone.

This is an independent program-database cross-check of the D3D9 evidence that
was previously derived mostly from decompiler C and PE bytes.

## Physics subsystem

Two previously unnamed global functions receive strong semantic aliases from
exact source strings:

- `FUN_00750080` -> `MWL::Core::LoadCollisionStream`;
- `FUN_007506b0` -> `MWL::Core::PhysicsInit`.

The latter also references `PhysicsSystem.cpp`, PhysX SDK creation, allocator,
trigger/contact report setup and physics resource-directory strings. These
strings make it a high-confidence subsystem initialization anchor for future
physics call-graph slicing.

The reflection/registration routine at `FUN_00703f10` references the vehicle
component names `Vehicle Chassis`, `Vehicle Gearbox`, `Vehicle Suspension`,
`Vehicle Collision`, `Vehicle Tyres` (plus engine/upgrade/wheel fields) and
calls all three established metadata primitives:

- `FUN_00631740` — registry/class metadata core;
- `FUN_0063a280` — reflected field registration;
- `FUN_006310c0` — metadata/descriptor helper used by the recovered registry.

This gives a compact static root for the vehicle configuration/reflection slice.

## RTTI registration fingerprint

The AI/path registration functions associated with class-name strings include:

| Function | String anchor |
|---|---|
| `0x00a84220` | `AIPolylinePath` |
| `0x00a84460` | `AISpline` |
| `0x00a84580` | `AISegmentPath` |
| `0x00a846a0` | `AIPathNode` |

All four are 86-byte `__stdcall` functions and share mnemonic SHA-256
`5824526536742d9cb874e9ecc084af0d07942498cc64bfa285019984dc11f258`.
Each directly calls `FUN_00631740`, `FUN_00630fe0`, `FUN_006310c0` and
`_atexit`.

Across `functions.jsonl`, **254 functions** share that mnemonic fingerprint.
This is useful as a registration-stub discovery signature, but the fingerprint
hashes mnemonics rather than operands. Therefore 254 is a candidate-cluster
count, not a claim that all 254 functions register classes. The cross-check
analyzer separately tests the required call targets before classifying a row as
matching the registration call shape.

## Automated cross-check

Run:

```bash
python3 tools/ghidra/analyze_shift_export.py \
  out/shift_ghidra_database \
  out/ghidra_crosscheck.json
```

The report format is `SHIFT.GhidraCrosscheckEvidence/1`. It verifies the direct
string/call anchors above and records the full registration-fingerprint cluster
for subsequent subsystem work.

## Scope and limitations

The generic `vtables.json`, `constructors.jsonl`, `switches.jsonl` and
`factories.jsonl` outputs remain heuristic candidate sets. They are valuable for
search-space reduction but are not substitutes for the project-specific RTTI
extractor, constructor disassembly or runtime evidence. In particular, class
renames and layout contracts should continue to require explicit identity joins
rather than proximity to a candidate function-pointer table.

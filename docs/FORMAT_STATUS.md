# SHIFT importer / format status

## Implemented or verified

| Format / subsystem | Current status |
|---|---|
| BFF v3 | archive parsing and metadata |
| Type 0 / 1 | raw + zlib |
| Type 2 | XMem/LZX with persistent state |
| Type 3 | external Oodle runtime path |
| X12d=2 | RC4 protected tables/payload path |
| Reflection XML | class/inheritance/property/Fct boundaries |
| BMLY/BML | structural parser |
| BMT / MTX | material graph + compatibility alias |
| FX / FXH / FXO | source inventory, shader parsing and permutation linking |
| DDS | metadata, DXT decode, cubemap decode |
| MEB | geometry/indices/material refs → MGEO |
| CSM | collision geometry → CMES |
| VHF/CAR | scene/resource graph |
| LOD XML | loose parser for known malformed retail forms |
| CDF | source-backed vehicle property schema |
| EDF | engine property parser and torque interpolation tooling |
| GDF | gear/final-drive parser |
| SDF | BODY/JOINT/HINGE/BAR schema + runtime reconstruction |
| VehiclePhysicsAssetGraph/1 | CDF/EDF/GDF/SDF neutral join |
| BAB/BAS | skeleton parsing, name linkage, animation evidence |
| SGB | container + runtime NODE/PART/SUMM/OCCL/FLAT boundaries |
| Camera runtime | config/state/event/control primitives |
| D3D9 capture | runtime producer and draw-local evidence |
| Vulkan | bootstrap, packets, reflection gates, BMW material/DDS bridge |
| Physics runtime | wheel/contact/body/solver boundaries |

## Major open areas

- complete production D3D9 shader/control-flow/material coverage;
- deeper SGB OBJECT/HIERARCHY/DAMAGE/FLAT semantics;
- complete BAB runtime pose semantics;
- remaining camera behavior;
- SDK/provider construction behind pre-PhysX boundaries;
- exact retail/provider numeric parity without runtime capture;
- full Vulkan RenderCommand/material execution;
- Android runtime, input, audio, streaming and gameplay integration.

The neutral IR remains the portability boundary.

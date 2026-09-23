# SHIFT DrawPacket IR

## New layer

The importer now has a neutral draw-packet builder for the next runtime boundary:

VHF/CAR -> MEB/MGEO -> BMT -> DDS, with optional HLSL/FX metadata.

The output schema is:

`SHIFT.DrawPacket/1`

Each packet preserves:
- scene/node identity and matrix reference;
- resolved MEB path plus vertex/triangle counts;
- primitive index range;
- BMT material reference and material summary;
- shader reference and resolved source path;
- texture references with DDS metadata;
- render-state fields already recovered by the BMT parser.

## Reference resolution

The builder reuses the project's evidence-based path rules:
- slash/case normalization;
- legacy `.mtx <-> .bmt` alias;
- legacy `.fx <-> .fxh` alias;
- path match before basename fallback;
- same-archive preference for basename fallback.

No exact sampler-state claim is made yet. Texture `slot` is explicitly marked `material-order-inferred` until D3D9 sampler bindings and BMT state records are fully reconstructed.

## Usage

First produce `resource_analysis.json` with the existing importer:

```bash
python shift_importer.py analyze-dir /path/to/bffs format_reports/ --ext .vhf .meb .bmt .dds
python draw_packets.py format_reports/resource_analysis.json draw_packets.json
```

An optional `analyze-shader-asm` report can be supplied with `--shader-report`.

## Status

This is a composition/IR layer, not the Android renderer itself. The next reverse-engineering work remains:
- exact D3D9 sampler state -> material texture binding;
- semantic vertex/pixel interface linkage;
- MGEO/VHF transform semantics;
- IMB animation and SGB scenegraph semantics.

# BMW M3 E36 — shader interface status

## Corpus

- 1,707 FXO files;
- 10,756 decoded shader stages;
- 125 unique stage input/output signatures;
- 21,488 VS/PS cross-pairs;
- 13,909 pairs (64.7%) have complete PS-input coverage from VS outputs.

## D3D9 Usage

Important recovered values:

- 0 POSITION;
- 1 BLENDWEIGHT;
- 2 BLENDINDICES;
- 3 NORMAL;
- 5 TEXCOORD;
- 6 TANGENT;
- 7 BINORMAL;
- 10 COLOR;
- 12 DEPTH;
- 13 SAMPLE.

## MEB semantic mappings

- 200 → POSITION0
- 220 → NORMAL0
- 240 → TANGENT0
- 250 → BINORMAL0
- 130..134 → TEXCOORD0..4
- 230..234 → alternate TEXCOORD0..4
- 310 → BLENDWEIGHT0
- 580 → BLENDINDICES0
- 460 → COLOR0
- 461 → COLOR1 where present

## Example bodywork interface

A recovered bodywork pair uses:

- PS TEXCOORD5 → v0, TEXCOORD0 → v1, TEXCOORD1 → v2;
- VS TEXCOORD5 → oT1, TEXCOORD0 → oT2, TEXCOORD1 → oT3.

Linking is semantic by `(usage,index)`, not physical register number.

## Current boundary

COLOR static Type/Usage/Channel evidence is resolved. Runtime same-instance declaration/buffer proof remains separate.

TEXCOORD5 semantic linkage is known at shader level; exact MEB source-property identity remains an evidence task.

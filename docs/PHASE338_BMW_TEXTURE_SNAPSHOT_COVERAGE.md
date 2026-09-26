# Phase 338: full BMW texture snapshot coverage

Phase 337 added the runtime-versus-DDS content comparator, but the native D3D9
producer's default snapshot stage list still omitted material stages s1 and s2.

## Change

When texture snapshot capture is enabled without an explicit stage filter, the
producer now captures all five relevant BMW paint stages:

- s0: shadow object;
- s1: diffuse texture;
- s2: specular texture;
- s3: environment cube;
- s4: scratch-control texture.

The explicit `SHIFT_D3D9_CAPTURE_TEXTURE_STAGES` override remains available for
smaller diagnostic captures.

## Why this matters

The Phase 337 content gate requires s1, s2 and s4 snapshots to compare runtime
texture content against the three material-owned retail DDS resources. With the
old default, the normal capture path could never collect two of those three
inputs.

No resource identity is inferred from the new default. The snapshots remain
draw-local evidence and are matched to retail DDS content only by the separate
Phase 337 comparator.

## Regression

The pipeline tests now verify that native `snapshot_paths` are discovered and
converted by the post-capture inventory.

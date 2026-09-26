# Phase 337: BMW M3 runtime texture resource parity

This phase extends the Phase 335 draw-local material witness with runtime texture
object lifecycle correlation and exact retail DDS metadata comparison.

## Runtime observations from the supplied capture corpus

For the draw-local BMW paint texture pointers observed in frame 30444:

| BMT parameter | D3D9 register | Runtime pointer | Latest CreateTexture before target draw |
|---|---:|---|---|
| `diffuseTexture` | s1 | `0x27a12120` | 1024×1024, 11 levels, DXT1, MANAGED |
| `specularTexture` | s2 | `0x369b59f8` | 8×8, 4 levels, DXT5, MANAGED |
| `scratchControlTexture` | s4 | `0x37ac3450` | 4×4, 3 levels, DXT1, MANAGED |

The pointer `0x27a12120` was also used by an earlier 64×32 DXT5 creation.
The Phase 337 parser deliberately chooses the latest creation strictly before
the target draw, so pointer reuse cannot cause a future/old-object mix-up.

The resource log also records the runtime-global objects used by the same paint
draw: s0 is a D16 depth texture and s3 is a 256×256 A16B16G16R16F render-target
cube. These are not treated as material-owned DDS resources.

## Static-resource comparison

The gate reads the exact DDS entries from `BMW_M3_E36.bff` and parses the DDS
header independently. Runtime creation metadata is compared against the
archive DDS dimensions, mip count and known D3D9 format mapping.

Classification is deliberately descriptive:

- `direct-dds-compatible`: runtime creation shape agrees with the archive DDS;
- `generated-or-transformed-candidate`: runtime creation shape differs, so direct
  identity is rejected and the object requires content-level evidence;
- `unknown`: no prior creation instance was captured before the draw.

This is a narrowing gate, not a claim that matching dimensions imply identical
bytes.

## Current evidence

The supplied `shift_resources.txt` confirms the runtime creation instances
listed above. The Phase 335 frame dump does not include runtime texture pixel
snapshots, so pixel-content identity remains unproven.

The especially important result is the paint diffuse stage: the runtime object
seen at s1 is 1024×1024 DXT1, while the archived `common_paint.dds` is only
184 bytes. The metadata mismatch prevents the project from incorrectly labeling
the runtime s1 object as the raw archive DDS.

The s2 and s4 runtime objects have creation shapes consistent with the known
small archived resources, but exact resource identity still requires content
comparison.

## Gate

`bmw_runtime_texture_resource_parity.py` emits
`SHIFT.BMWM3RuntimeTextureResourceParity/1`.

The gate requires all 12 Phase 335 paint texture bindings to resolve to an
earlier runtime creation event. Shape mismatches remain explicit blockers rather
than being converted into path identity.

## Next boundary

The next step is runtime content identity using the native PPM texture snapshots:
compare s1/s2/s4 captured pixels against the decoded retail DDS payloads, while
keeping generated/transformed objects such as the 1024×1024 s1 surface separate.

# Phase 249 — scene NODE/partition runtime semantics

This phase reconstructs the scene XML object layer around FUN_006a4160 without
claiming that it decodes the still-opaque SGB NODE/FLAT/SUMM binary chunk bodies.

## Recovered object dispatch

The SCENE parser recognizes these object tags in the retail runtime:
TRANSFORM, NODE, TERRAIN, PARTICLES, OCCLUDER and LIGHT.

NODE records are built by FUN_0069ba40 and preserve:
Merged, Animated, Dynamic, VariationIndex, Instances, Resource and
VariationPaletteFile.

TRANSFORM records use Position, Orientation and Scale. A missing scale defaults
to 1.0.

LIGHT records recognize Ambient=1, Directional=2, Spotlight=3 and Point=4.
InnerAngle and OuterAngle are halved and then converted from degrees to radians.
Position, Direction, Colour, Intensity, Range and CastsShadows are read directly.

Partition processing reads PARTITION_ID, AABBOX min/max, CHILD_PARTITIONS and
CHILD_OBJS. The integer-list helper preserves the source's permissive strtol-style
reference parsing.

## Boundary

Parent-child transform composition is not inferred. The existing SGB chunk parser
also remains responsible only for verified container/chunk boundaries and resource
string provenance until real NODE/FLAT/SUMM payload grammar is established.

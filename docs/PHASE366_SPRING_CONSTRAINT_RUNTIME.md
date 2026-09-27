# Phase 366 — spring constraint force runtime

Phase 366 continues the physics track from the spring gap/transition state into
FUN_0075489c, the spring-element force-application loop.

## Evidence source

Retail SHIFT.exe.c:

- FUN_0075489c at recovered source line 750161;
- FUN_00754cc0 at source line 750338 for property registration;
- FUN_007546a0 at source line 750040 for spring-element construction;
- verified recovered-source SHA-256:
  512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9.

## Element layout

FUN_0075489c iterates an element array at object +0x100 with 0x90 byte
stride and count at +0xa8.

The registered spring fields are:

| Field | Offset |
|---|---:|
| Spring Type | +0x10 |
| Spring Direction | +0x18 |
| Spring Head | +0x30 |
| Spring Body | +0x48 |
| Collision Length | +0x60 |
| Spring Params A | +0x68 |
| Spring Params B | +0x70 |

## Recovered force boundary

Upstream transform helpers prepare the world-space vectors. After that boundary,
the function derives a relative vector first. Type 0 uses the transformed configured
Spring Direction as-is; Types 1 and 2 copy and normalize the derived relative vector.
The projection is the dot product between that direction and the same relative vector.

The activation gate is exact:

collision_length <= 0 || collision_length <= abs(projection)

For types 0 and 1:

body_projection = dot(direction_used, body_relative_vector)

response = SpringParamsA * projection + body_projection * SpringParamsB

force = direction_used * response

When collision_length > 0, the source suppresses this force for either sign
crossing:

projection > 0 && response < 0

or

projection < 0 && response > 0

Type 2 uses a vector response instead:

force = body_relative_vector * SpringParamsB + direction_used * (SpringParamsA * projection)

The resulting vector is passed to FUN_007baa70 together with the prepared spring
head anchor.

## Scope boundary

This phase does not infer:

- physical units of either Spring Params field;
- semantic names beyond the property strings registered by the retail executable;
- the exact world-space transform semantics of FUN_007aefb0;
- any downstream suspension/tyre interpretation of the applied force.

The contract is therefore a force-construction boundary, not a complete suspension model.

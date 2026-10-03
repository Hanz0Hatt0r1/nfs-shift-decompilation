# Phase 658 — native BODY point transforms

Phase 658 ports the exact BODY point-transform pair recovered in Phase 375 into `shift_runtime_physics`.

## `FUN_007537b0`

The native helper reads the established BODY triplets:

- angular vector at `+0x18/+0x20/+0x28`;
- translation vector at `+0x78/+0x80/+0x88`.

For input point `p`, it returns the source-backed expression:

```text
angular × p + translation
```

with the exact recovered component ordering.

## `FUN_00753810`

The close variant additionally uses BODY position at `+0x00/+0x08/+0x10` and first computes:

```text
relative = point - body_position
```

It then applies the same cross-product-plus-translation expression to `relative`.

## Regression

`shift_runtime_body_point_transform_check` mirrors the Python oracle for:

- the nontrivial `FUN_007537b0` fixture;
- the relative-point subtraction path in `FUN_00753810`;
- zero angular state reducing to the stored translation vector;
- fail-closed rejection of non-finite BODY state.

## Scope

These functions establish exact read-side relationships among BODY position, angular and translation triplets. They do not identify the writer that advances those triplets between simulation steps and therefore do not by themselves implement vehicle pose integration.

They do remove the remaining opaque transform helper from the Phase 374 auxiliary contact-response chain. Together with Phase 657 `FUN_00755340` and Phase 656 `FUN_007baa70`, only the surrounding frame transforms and record scheduling remain before that auxiliary path can be joined natively.

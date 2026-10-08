# Process 1B — reject the participant `FUN_00481e20` alias for `manager+0x374`

## Blocker

`P1.3.manager374` still had two direct embedded-subobject destinations feeding the large `FUN_00481e20` field-by-field copy. One was the call at `0x004848f5`, where the destination is `parent+0xa00`.

## Reused exact provenance

The merged `SHIFT.OuterVehicleRenderSnapshotAffineBridge/1` contract already fixes the caller domain as the SMS participant path. It proves the selected vehicle slot and snapshot transport into participant-owned storage, and records the render snapshot at `participant+0xa00`.

The relevant destination is therefore:

```text
FUN_004848bc
  -> 0x004848f5 call FUN_00481e20
  -> destination = participant + 0xa00
```

The manager singleton under investigation is the distinct fixed root `0x00bc9fc0`. The participant-owned render snapshot destination is not that singleton root and is not admitted as an affine manager alias by any merged contract.

Therefore the `FUN_00481e20` copy store at:

```text
0x004826a6 fstp dword [ESI+0x374]
```

cannot be a write to `FUN_00489ad0()+0x374` on the `0x004848f5` path.

## Result

The `0x004848f5 (participant+0xa00)` direct destination is rejected from the manager `+0x374` writer frontier.

Only one direct embedded-subobject callsite remains open:

```text
0x0081d335 destination ECX = parent + 0x2d0
```

No control semantics, HDVehicle identity, or provider reduction is promoted. `manager+0x374 == HDVehicle+0x4330` remains unproven and the external provider count remains 7.

## Next step

Root the parent object at `0x0081d335`. If `parent+0x2d0` is proven outside the singleton manager domain, the direct `FUN_00481e20` bulk-copy literal-writer surface can be closed and Process 1B can move on to helper-mediated/indirect manager-root mutations.

# Phase 359 — vehicle physics asset roots

This phase keeps renderer work frozen and reconstructs the next vehicle-physics data
boundary from retail SHIFT.exe.c.

FUN_0074ec30 combines the Physics Manager vehicle and physics path fields and appends
seven runtime roots:

| Key | Relative root |
|---|---|
| chassis | vehicles/Physics/Chassis/ |
| collision | vehicles/Physics/Collision/ |
| engines | vehicles/Physics/Engines/ |
| gearbox | vehicles/Physics/GearBox/ |
| suspension | vehicles/Physics/Suspension/ |
| upgrades | vehicles/Physics/Upgrades/ |
| vehicles | vehicles/Physics/Vehicles/ |

FUN_0074d640 consumes the Chassis root when constructing a participant CDF path and
appends the observed .cdf suffix.

The new SHIFT.VehiclePhysicsAssetRuntime/1 contract records the exact root names,
their manager path components, and the known Chassis-to-CDF linkage.

Unresolved: concrete files/keys below each root and the ownership of each loader.

Four focused tests validate the exact seven roots and the Chassis/CDF linkage.

Renderer and RENDER.bff remain untouched.

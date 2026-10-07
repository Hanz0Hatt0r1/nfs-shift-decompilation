# Phase 737 scope

Included:

- reuse Phase634 source-backed component geometry for `HDVehicle+0x820/+0x12a0`;
- reuse Phase702 selected BMW wheel BODY identities `FL=3`, `FR=4` in the 11-BODY domain;
- reuse the persistent BODY ABI `0x170` stride and f64 origin lanes `+0/+8/+0x10`;
- derive the two pointer-backed Phase728 vec3 inputs from current persistent BODY bytes;
- preserve the exact Phase728 arithmetic and its explicit f64 store boundaries;
- retain only second-source `+0x338/+0x918` as unresolved `FUN_007618f0` input state;
- keep the active top-level provider count at seven.

Excluded:

- assigning a physical name or unit to the second `FUN_007618f0` source object or its fields;
- claiming `source+0x338/+0x918` are owned by a wheel, chassis, suspension or renderer object without direct evidence;
- wiring the incomplete producer into the full production `FUN_00765c40` anchor;
- changing collision-provider ownership or `FUN_007b0710` semantics;
- using Xbox layout as authority for the PC pointer identities;
- reducing the provider count before a complete provider boundary is actually removed.

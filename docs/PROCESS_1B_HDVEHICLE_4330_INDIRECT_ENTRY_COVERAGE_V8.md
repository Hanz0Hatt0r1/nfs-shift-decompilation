# Process 1B — HDVehicle+0x4330 indirect-entry coverage v8

This supersedes `/7` by composing the static-vtable indirect-target recovery subset.

Coverage now includes 12 bounded classes. The new class checks 2,533 pinned static vtable candidates / 22,416 slots and finds zero targets equal to any of the 15 canonical P1B carriers.

The navigation index still contains 19,500 unresolved indirect edges. Therefore global incoming indirect entry remains fail-closed: runtime-written vtables, callbacks, persistent function-pointer stores, runtime-generated/copied targets and opaque memory are still open.

Provider count remains 7. Manager+0x374 identity, `0x004b86cf` and aggregate P1.3 remain fail-closed.

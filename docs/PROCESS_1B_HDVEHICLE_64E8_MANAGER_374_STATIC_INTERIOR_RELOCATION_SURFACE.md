# Process 1B — Participants Manager static interior-pointer and relocation surface

## Scope

This slice closes two alternate ways the exact Participants Manager root `0x00bc9fc0` might otherwise be reconstructed without the already-bounded literal/getter paths: loading a preinitialized pointer to a manager interior subobject and subtracting its offset, or using a shipped PE base-relocation table.

PC retail 1.02 machine/image data is authoritative.

## Result

A 4-byte-aligned scan of `.rdata` and `.data` for values in the bounded manager range `0x00bc9fc0..0x00bca4bf` finds zero cells. Therefore no static data cell exposes the root or a nearby manager interior pointer that can be reduced back to the root by a constant subtraction.

The PE header also reports relocations stripped. The Base Relocation Directory has RVA `0x00000000` and size `0x00000000`, so the shipped image contains no base-relocation table from which an alternate manager-root pointer can be recovered.

## Adjudication

Static interior-pointer reconstruction and shipped base-relocation-derived reconstruction are closed-negative as alternate sources of a Participants Manager root and therefore cannot introduce a new manager `+0x374` value.

Runtime-created pointers, opaque helper returns, indirect/external initialization, or unrecognized runtime transforms remain open. The `0x004b86cf` HDVehicle literal candidate therefore remains fail-closed and provider count remains 7.

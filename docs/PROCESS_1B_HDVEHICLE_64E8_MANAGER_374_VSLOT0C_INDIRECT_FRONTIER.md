# Process 1B — Participants Manager vslot +0x0c indirect frontier

## Scope

This slice bounds the remaining opaque-return candidate `FUN_0045b130`. The function occupies slot `+0x0c` of the exact outer-object vtable `0x00ab5644` and can execute Participants Manager getter calls on some branches.

PC retail 1.02 machine transfer is authoritative. Ghidra SQLite is navigation-only.

## Identity

`FUN_00d36210` allocates `0x46e0` bytes, calls `FUN_0045ef50` at `0x00d362d9`, and stores the constructed object globally at `0x00bc185c`. `FUN_0045ef50` installs vptr `0x00ab5644` at `0x0045ef78`.

Vtable cell `0x00ab5650` (`+0x0c`) contains `FUN_0045b130`. The exact target address appears only once as a raw 32-bit value in the entire PE, at that vtable cell, and the Ghidra direct-call index contains zero direct callers.

## Return shape

`FUN_0045b130` first tests byte `receiver+0x46c1`. If the guard is false it jumps directly to the epilogue and returns without defining `EAX`. Other branches call `FUN_00489ad0` at `0x0045b162` and `0x0045b181` and can therefore leave a manager-root value in `EAX` incidentally.

Because a valid return path does not define `EAX`, the exact Participants Manager root is not a stable function-result contract. This is a useful rejection constraint, but it is not sufficient to rule out an indirect consumer that only invokes/uses a getter-reaching branch.

## Direct dispatch scan

A bounded machine scan for the exact sequence class `load global outer 0x00bc185c -> load [outer] vptr -> load [vptr+0x0c] -> indirect call` finds zero callsites before receiver provenance is lost. Thus there is no direct exact-global-root slot dispatch to classify.

## Adjudication

Direct calls and direct exact-global-root vslot dispatch are closed. The only remaining `FUN_0045b130` risk is generic/interface indirect dispatch where the receiver reaches the same outer object through an alias or subsystem registration. That surface remains fail-closed.

The manager `+0x374` to `HDVehicle+0x4330` join, literal `0x004b86cf`, and P1.3 remain open. Provider count remains 7.

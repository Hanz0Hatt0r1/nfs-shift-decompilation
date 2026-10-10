# Process 1B — HDVehicle+0x4330 indirect-entry coverage v7

Version 7 supersedes `/6` by adding the incoming-entry frontier isolation contract.

## Added bounded class

The direct incoming call surface is now fully adjudicated:

- 25 direct incoming callsites;
- 14 internal carrier-to-carrier callsites;
- 11 external callsites across 7 callers;
- 0 unresolved external direct callers after machine adjudication;
- 0 external direct pre-existing `HDVehicle+0x4330` aliases.

The remaining incoming-entry uncertainty is therefore the unresolved indirect target surface of the shared navigation index:

- 19,500 indirect edges;
- 0 resolved targets;
- 19,500 unresolved targets.

This raises the composed bounded coverage class count from 10 to 11 while preserving zero exact-carrier hits in bounded classes.

## Limits

The navigation index cannot prove absence of incoming indirect carrier entry because it resolves none of those indirect edges. Runtime vtable/callback/function-pointer storage provenance is still required.

Global indirect-entry, runtime-generated/copied pointer, generic store/copy, manager identity, final literal and aggregate P1.3 gates remain fail-closed. Provider count remains 7.

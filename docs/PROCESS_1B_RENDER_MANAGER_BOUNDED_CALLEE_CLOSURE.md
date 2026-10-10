# Process 1B — render-manager bounded callee closure

## Scope

This aggregate composes the complete bounded direct-receiver surface rooted at exact loads of `DAT_00bc185c`.

`SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2` emits 17 direct receiver targets. The merged direct-target closures now account for all 17/17 targets, leaving zero bounded direct targets unresolved.

Two special address-of-stack-local helper handoffs are also already closed-negative: each helper overwrites the pointed local with zero before any read, so the original exact outer root cannot be observed or exported through those paths.

Returned-root persistence and the three derived-subobject transitions are separately closed by `SHIFT.P1B.RenderManagerCopyReturnClosure/1` and `SHIFT.P1B.RenderManagerDerivedSubobjectClosure/1`.

## Adjudication

The bounded direct-callee alias surface is complete and cannot export or recreate the exact render-manager outer root.

This is not a global absence proof. External/unknown-origin memory, opaque runtime-created aliases, helper/non-vtable indirect setters, and other unbounded sources remain fail-closed. Therefore the `manager+0x374 -> HDVehicle+0x4330` identity join, final `0x004b86cf` rejection, P1.3 completion, and provider removal remain open. Provider count remains 7.

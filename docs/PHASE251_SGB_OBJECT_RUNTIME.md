# Phase 251 — embedded SGB object runtime

The NODE object-payload pointer is now followed into the recovered runtime parser FUN_0069bc50 → FUN_0069a6c0. The new sgb_object_runtime.py reconstructs the common 36-byte object header, OBJECT/HIERARCHY/DAMAGE dispatch, string-offset fields, hierarchy count/type bytes at +0x22/+0x23, and the 9-dword HIERARCHY child record layout with the exact runtime copy order.

sgb_runtime.py attaches a bounded embedded-object report to decoded NODE records. Unknown object transform/material fields remain raw. This phase does not touch the renderer or RENDER.bff.

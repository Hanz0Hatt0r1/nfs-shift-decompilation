# Process 1 — `FUN_00765c40` residual ownership frontier

## BLOCKER

P1.2 remains the Process 1 proof gate for Process 2 P2.4. The collision/world lookup boundary is now machine-backed and closed as an explicit typed external provider boundary; only exhaustive residual side-effect classification still blocks complete `FUN_00765c40` removal.

## Closed surface

The following selected-session work is no longer open:

```text
selected per-pass world position       CLOSED
persistent +0x38dc cache lifetime      CLOSED
selected +0x38e8 miss fallback         CLOSED
typed FUN_007b0710 query/output seam   CLOSED
four wheel +0x738 load terms           CLOSED
FUN_0074f560 provider pointer domain   CLOSED: global 0x00c133ac
scene-query virtual dispatch           CLOSED: vtable slot +0x1c0
0x58-byte surface-record provenance    CLOSED
```

The PC-retail machine proof is `SHIFT.Fun0074f560CollisionProviderMachineProof/1`. It establishes the exact lower dispatch without assigning an unproven PhysX/engine class name. The implementation behind the virtual slot remains external and must be preserved as an explicit typed provider callback/interface.

## Remaining P1.2 proof

Only **P1.2b** remains: classify every source-visible `FUN_00765c40` write and side-effecting callee outside the already-closed query input/output, collision-provider boundary, and four `+0x738` load terms.

The source-hash-locked helper `tools/ghidra/inventory_fun_00765c40_write_surface.py` exists specifically for this audit. Lack of a currently typed field is not proof that a write does not exist.

## Consumer

Process 2 P2.4 may consume the typed provider boundary at `0x00c133ac` / vtable slot `+0x1c0`. It must not substitute a guessed track query and must not remove the complete residual `FUN_00765c40` pass until P1.2b closes.

## Gates

- P1.2a: **closed**;
- P1.2b: **open**;
- P1.2 complete: **false**;
- `FUN_00765c40` provider removal authorized: **false**;
- external-provider count: **7**.

## Next step

Run the pinned residual write/call inventory against the authoritative PC-retail `SHIFT.exe.c`, resolve aliases for every assignment and side-effecting call, and publish the smallest positive residual-state contract. Do not reopen P1.2a.

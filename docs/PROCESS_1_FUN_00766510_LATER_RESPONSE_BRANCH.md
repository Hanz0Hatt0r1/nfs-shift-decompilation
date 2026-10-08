# Process 1 — later `FUN_00766510` response branch ownership

## BLOCKER

P1.1b required positive owner/config/source-order proof for the later `FUN_00766510` direct-response block rooted at `HDVehicle+0x3a28/+0x3a40` before Process 2 can internalize the complete `contact_response` boundary.

## INPUT

Authoritative PC retail 1.02 full Ghidra export:

```text
SHIFT.exe.c
sha256 512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9
```

Matching retail executable:

```text
sha256 eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

Xbox recompilation is not required for this proof.

## OUTPUT

Adds `SHIFT.Fun00766510LaterResponseBranchOwnership/1` and a source-hash-locked analyzer.

The setup owner is now closed:

- `+0x3a08` is configured by `FUN_00752f10` from `VehicleLoadData+0xa38/+0xa40/+0xa48`;
- `+0x3a28/+0x3a30/+0x3a38` is the `FUN_00753590` transform of `VehicleLoadData+0xc18`;
- `+0x3a40..+0x3ac8` is populated as six `0x18`-byte triples from six `0x48`-byte setup records beginning at `VehicleLoadData+0xa50`, with per-record components at `+0x00/+0x14/+0x28` and explicit `f32` spill before `f64` storage;
- polynomial coefficient initial values come from evaluated `VehicleLoadData+0x9f4/+0xa08/+0xa1c/+0x9b8/+0x9cc/+0x9e0`.

The important preservation result is that the complete `+0x3a40` table is **not** immutable setup data. The sixth entry occupies `+0x3ab8/+0x3ac0/+0x3ac8`:

- `+0x3ac0` is overwritten in `FUN_00766510` immediately before the table lookup with the current `FUN_00755340(+0x3a08)` result multiplied by persistent `+0x3a00`;
- `+0x3ac8` is a persistent derived value written by `FUN_00756b10`;
- `+0x3a00` is also a persistent derived value written by `FUN_00756b10`.

`FUN_00756b10` preserves the exact formulas:

```text
+0x3a00 = +0x3780*s^2 + +0x3778*s + +0x3770
+0x3ac8 = +0x3798*s^2 + +0x3790*s + +0x3788
selector = +0x3cb0
```

The writer surface is pinned at setup and later mutation/reset refreshes. `+0x3770` and `+0x3788` themselves are mutable bases: `FUN_00758000` changes them, and clamp/reset paths restore them against baselines `+0x3cb8/+0x3cc0` before refreshing `FUN_00756b10`.

## Runtime order

The PC-retail branch order is fixed as:

```text
transform +0x3a28 application
-> derive relative vector against the shared reference vector
-> evaluate +0x3a08 curve
-> multiply by persistent +0x3a00
-> overwrite sixth-table-entry lane +0x3ac0
-> evaluate +0x3a40 table
-> transform table output
-> FUN_007baa70 BODY application
-> FUN_00753650 caller delta
-> accumulate +0x40a0/+0x40a8/+0x40b0
-> optional +0x42d8/+0x42e0/+0x42e8/+0x42f0 diagnostics
```

## CONSUMER

Process 2 may consume this branch as a positive source-backed contract, but it must preserve `+0x3a00`, `+0x3ac0`, and `+0x3ac8` as dynamic/persistent state instead of freezing the six-entry table after setup.

## GATES_CHANGED

- P1.1b later `+0x3a28/+0x3a40` owner/config/order: **closed**;
- whole `+0x3a40` table safe as setup constant: **false**;
- complete P1.1: **still false**;
- `contact_response` provider removal: **still unauthorized**;
- top-level external provider count: **still 7**.

## LIMITS

This proof does not invent physical names or selected BMW numeric constants. It does not close the earlier dynamic inputs feeding `FUN_00713630`, and it does not yet provide the exhaustive final accumulator/tail state-and-diagnostic-write preservation contract required by P1.1c.

## TESTS

`tests/test_process1_fun_00766510_later_response_branch.py` pins the source authority, setup record layout, mutable sixth-table-entry lanes, `FUN_00756b10` refresh surface, and exact runtime ordering landmarks.

## NEXT_OWNER

Process 1 continues P1.1a/P1.1c. Process 2 may consume `SHIFT.Fun00766510LaterResponseBranchOwnership/1` in P2.3.

## NEXT_STEP

Finish the unresolved upstream runtime-global/value provenance around the `FUN_00713630` writer and then publish the exhaustive final `+0x40a0/+0x40a8/+0x40b0` accumulator plus state/diagnostic-write contract.

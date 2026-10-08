# Phase 749 — native later `FUN_00766510` response state

Phase 749 consumes the merged Process 1 contract `SHIFT.Fun00766510LaterResponseBranchOwnership/1` without claiming that the full `contact_response` provider is ready to disappear.

## What becomes native

The native contract now preserves the exact setup and persistent-state geometry already proven by Process 1:

- curve state at `HDVehicle+0x3a08`;
- setup application vector at `+0x3a28/+0x3a30/+0x3a38`;
- six `0x18`-byte table entries rooted at `+0x3a40`;
- mutable polynomial bases at `+0x3770/+0x3788` and their baselines at `+0x3cb8/+0x3cc0`;
- selector state at `+0x3cb0`;
- persistent derived values at `+0x3a00` and `+0x3ac8`.

`refresh_fun_00756b10_later_response_state()` reproduces the source-backed formulas:

```text
+0x3a00 = +0x3780*s^2 + +0x3778*s + +0x3770
+0x3ac8 = +0x3798*s^2 + +0x3790*s + +0x3788
```

The two base terms remain explicit mutable inputs. Phase 749 does not freeze them to setup values. A separate baseline-restore helper models only the already-proven clamp/reset restoration to `+0x3cb8/+0x3cc0`; it does not invent the unresolved `FUN_00758000` mutation rule.

## Runtime table materialization

The complete six-entry table is deliberately not modeled as immutable setup data. Each later-branch evaluation materializes a fresh runtime copy and preserves the retail-owned sixth-entry behavior:

```text
sixth entry = +0x3ab8/+0x3ac0/+0x3ac8
+0x3ac0 = FUN_00755340(+0x3a08) * persistent +0x3a00
+0x3ac8 = persistent FUN_00756b10-derived lane
```

The setup table snapshot remains unchanged. This makes the dynamic/persistent distinction explicit in the native API and prevents the exact failure mode Process 1 ruled out: freezing all of `+0x3a40..+0x3ac8` after setup.

## What remains external

Phase 749 stops before the still-open whole-branch boundary. It does not claim ownership of:

- the full relative-vector derivation and table-response application sequence;
- the final BODY application and `FUN_00753650` caller delta;
- the exhaustive `+0x40a0/+0x40a8/+0x40b0` accumulator contract;
- the optional `+0x42d8..+0x42f0` diagnostic tail;
- the remaining upstream runtime-input provenance around `FUN_00713630`.

Therefore `contact_response` remains an external provider and the active provider count remains **7**.

## Regression

The Phase 749 native check pins:

- all recovered offsets and six-entry table geometry;
- both `FUN_00756b10` polynomial formulas;
- mutable base changes affecting refreshed state;
- baseline restoration affecting refreshed state;
- per-evaluation `+0x3ac0` overwrite;
- persistent `+0x3ac8` injection into the sixth table entry;
- immutability of the setup table snapshot.

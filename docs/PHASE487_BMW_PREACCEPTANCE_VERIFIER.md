# Phase 487 — end-to-end BMW pre-acceptance matrix verifier

## Goal

Phase 487 turns the Phase 486 BODY solver-domain builder into an end-to-end verifier for the real BMW physics archive.

The pipeline is:

`BMW_M3_E36.bff` → exact suspension SDF entry → SDF parser → FUN_007b1b60-compatible solver domain → BODY scalar groups → FUN_007ba2b0 structural matrix → BMW seed comparison.

## Exact archive/resource gates

The verifier requires the previously recorded BMW archive SHA-256 and the exact decoded `vehicles/physics/suspension/aarm_multilink.sdf` SHA-256. This prevents a different BFF/resource from being silently labeled as the BMW regression input.

Expected shape remains:

- 11 BODY records;
- 4 JOINT&HINGE source records;
- 20 BAR records;
- 28 runtime constraint records;
- 40 solver scalar nodes.

## Structural parity gate

The generated matrix is compared against the Phase 406 seed evidence using:

- 700 non-zero cells;
- 900 zero cells;
- 330 strict-upper non-zero cells;
- row non-zero counts `[10 × 10, 25 × 20, 10 × 10]`;
- full 40×40 byte-level 0/1 SHA-256 `6d066aab...`.

The hash is computed with the same flattened 0/1 byte representation already defined by `sdf_constraint_seed_write_runtime.py`.

## Provider interpretation

The verifier also runs provider acceptance predicates on the generated matrix. Their result is diagnostic only. The BMW provider identity remains capture-gated; in particular, a no-match result is not converted into a claim about which backend the retail runtime uses.

## CLI

Run:

    python tools/verify_bmw_preacceptance_matrix.py BMW_M3_E36.bff

Write a full report:

    python tools/verify_bmw_preacceptance_matrix.py BMW_M3_E36.bff -o out/bmw-preacceptance.json

Use `--strict-sdf` to make parser warnings blocking.

## Scope boundary

This phase verifies the pre-acceptance structural matrix only. It does not reconstruct dynamic matrix coefficients, provider solve numerics, packed provider workspace aliasing, or the retail provider class identity.

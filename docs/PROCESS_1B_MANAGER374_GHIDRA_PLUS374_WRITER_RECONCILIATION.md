# Process 1B: Ghidra `+0x374` writer reconciliation

## Blocker

P1.3B still cannot finish the exact `manager+0x374 -> HDVehicle+0x4330` identity join because unrelated/unknown manager-root origins and the global helper/non-vtable setter class remain fail-closed.

The raw PC retail 1.02 writer work already closed the literal destination surface: `SHIFT.HDVehicle64e8Manager374LiteralStoreInventory/1` inventories 25 whole-text instructions whose memory destination carries literal `+0x374`, and downstream contracts classify all 25. Separately, the merged materialized/computed frontier closes address-materialized `+0x374` transports.

The repository also has an analyzed Ghidra database for the same executable. This change adds an independent reconciliation path so Ghidra listing semantics can be checked against the raw-retail objdump inventory before Ghidra-derived instruction evidence is reused for the remaining root-origin/helper work.

## Inputs

`tools/ghidra/analyze_p1b_manager374_ghidra_plus374_writers.py` consumes:

1. JSONL from `run_shift_scalar_uses.sh` for exact scalar `0x374` (the shared generic exporter is preferred; the existing `ShiftScalarUseExporter.java` remains the fallback);
2. `binary.json` from the same Ghidra evidence export;
3. `evidence/hdvehicle_64e8_manager_374_literal_store_inventory.json`.

The Ghidra identity is fail-closed against the established PC retail program:

- program `SHIFT.exe`;
- MD5 `705af8b420e5eb1e3834ac43d5533c6b`;
- language `x86:LE:32:default`;
- image base `0x00400000`;
- pointer size 4;
- executable, non-writable `.text`;
- non-writable `.rdata`;
- writable `.data`.

The raw inventory remains pinned to SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

## Run

Export exact scalar uses from the existing analyzed Ghidra project through the
compatibility runner:

```bash
GHIDRA_HOME="$GHIDRA_HOME" tools/ghidra/run_shift_scalar_uses.sh \
  "$HOME/ghidra-projects" shift SHIFT.exe \
  "$PWD/out/p1b_manager374_scalar_374.jsonl" 0x374
```

Then reconcile them against the Ghidra identity file and authoritative raw-retail literal inventory:

```bash
python3 tools/ghidra/analyze_p1b_manager374_ghidra_plus374_writers.py \
  out/p1b_manager374_scalar_374.jsonl \
  out/shift_ghidra_database/binary.json \
  evidence/hdvehicle_64e8_manager_374_literal_store_inventory.json \
  --fail-on-mismatch \
  --output out/p1b_manager374_ghidra_plus374_reconciliation.json
```

Output format:

```text
SHIFT.P1B.Manager374GhidraPlus374WriterReconciliation/1
```

## Classification

Only scalar rows satisfying all of these are promoted into the Ghidra literal-writer candidate set:

- the matching scalar is exact `0x374`;
- the matching operand is operand 0;
- operand 0 is a memory expression containing an exact positive `+0x374` term and a 32-bit GPR base/index;
- the instruction mnemonic is in the same explicit write/RMW family used by the raw-retail whole-image probe.

The operand parser accepts Ghidra's typed aliases (`float ptr`, `double ptr`, and
`long double ptr`) as well as x86 size names such as `DWORD PTR`. Ghidra emits
`float ptr` for x87 `FSTP` destinations that raw objdump renders as `DWORD PTR`;
excluding that spelling creates a false missing-writer mismatch.

First-memory forms with the same displacement but a mnemonic outside the write allowlist are retained separately. LEA/address arithmetic and other non-destination scalar uses are counted but not promoted.

The reconciliation is complete only when the Ghidra candidate site set equals the raw-retail literal writer site set exactly. Missing and extra sites are emitted separately; `--fail-on-mismatch` returns a non-zero exit status for either condition.

## Gate effect

A successful run may establish only:

```text
ghidra_program_identity_pinned = true
ghidra_literal_plus_0x374_writer_site_reconciliation_complete = true
```

It does **not** change semantic receiver/root gates. These remain fail-closed:

```text
all_plus_374_candidate_receivers_classified = false
unknown_or_unrelated_manager_root_alias_surface_complete = false
global_helper_non_vtable_indirect_setter_surface_complete = false
global_manager_root_origin_surface_complete = false
manager_374_join_to_hdvehicle_4330_complete = false
last_literal_0x004b86cf_rejected = false
p1_3_control_producer_complete = false
external_provider_count = 7
```

A Ghidra/raw site-set match is a decoder/export consistency result, not Participants Manager identity.

## Retail reconciliation result (2026-10-22)

The pinned analyzed Ghidra `SHIFT.exe` export for exact scalar `0x374` produced
170 rows. With the typed-operand parser fix, it yields 25 literal writer
candidates; the raw-retail inventory also contains 25. The intersection is 25,
with no missing or extra sites. In particular, the x87 stores at `0x004826a6`,
`0x00865013`, and `0x00a44ac5` now reconcile as `FSTP float ptr [...]`.

The seven other first-operand memory forms remain non-writes (`CMP`). The output
is preserved as
`evidence/p1b_manager374_ghidra_plus374_reconciliation_20261022.json`.
Input identities for this run:

```text
scalar-use JSONL SHA-256: 204ac152800019db021a1c0c7f584b68c7978d468dc5fbe28df5115d2d877ef1
Ghidra binary.json SHA-256: 709a287ca9eec0599252baefe6abf356f2e4e04652ade140a1f10d381e5865df
raw retail inventory SHA-256: 95ab9638e2925a339a01d2893eed88430a88f136136539ebc06d5711221248b8
reconciliation JSON SHA-256: e07849a60ed41501c767eee6304d25b3b1bc9289710e38e9734b25fc2a18bfe0
```

Regression coverage is in
`tests/test_process1b_manager374_ghidra_plus374_writer_reconciliation.py`.
All semantic receiver/root gates remain false and the external provider count
remains 7; this result only verifies Ghidra/raw instruction-site agreement.

## Limits

This reconciliation covers literal destination `+0x374` stores/RMWs only. Address-materialized stores are owned by the already merged materialized/computed contracts. Helper-returned roots, externally/runtime initialized memory, non-vtable indirect setters, generated/self-modifying code and arbitrary process mutation remain separate surfaces.

No numeric offset equality is used as object identity.

## Next

Use the verified Ghidra listing path for narrowly targeted unknown-root/helper investigations while preserving the existing raw-retail contracts as semantic authority. The final manager/HDVehicle identity and `0x004b86cf` slot2 adjudication remain blocked until those surviving origin/setter classes close.

# Process 1B / P1.3B — orphan caller recovery, batch 3

This batch restores three function bodies in the isolated Ghidra copy
`shift-recovered-mass-20261017`. The original project was read-only throughout.
The plan records each body hash, preceding terminal instruction, `0xcc`
boundary padding, exact entry evidence, and assigned orphan calls.

| Entry | Instructions / P-code | Bytes | Orphan calls assigned |
| --- | ---: | ---: | ---: |
| `0x004b6150` | 163 / 163 | 599 | 2 |
| `0x00a86ca0` | 10 / 10 | 36 | 1 |
| `0x005fccc0` | 349 / 349 | 1,214 | 4 |
| **Total** | **522 / 522** | **1,849** | **7** |

The first body is reached by an exact unconditional jump from `0x004b5c3f`.
The second has a raw 32-bit pointer to its exact instruction entry at read-only
`.rdata` address `0x00aa8660`. The third has a typed data reference from
`0x00ae4b58`. Its conditional exit at `0x005fcd65` enters the shared epilogue
inside existing function `0x005fd180`; its final tail transfer targets the
existing function at `0x004031c4`. Both external CFG edges are recorded and
checked explicitly, and no existing function body was overwritten.

This assigns owners to 7 of the 8 remaining exact orphan calls. The combined
export corpus now has 787 functions, 113,725 instructions, and 113,541
P-code-bearing instructions. The last unresolved call at `0x00d38db6` is in the
executable `.secu` block; its enclosing body boundary remains unverified, so it
is left unassigned in this batch. No semantic names or behavior claims were
added.

The checked-in plan and hash-pinned report are
[`evidence/p1b_orphan_function_recovery_batch3_plan.tsv`](../evidence/p1b_orphan_function_recovery_batch3_plan.tsv)
and
[`evidence/p1b_orphan_function_recovery_batch3.json`](../evidence/p1b_orphan_function_recovery_batch3.json).
Read-only Ghidra exports and the separate recovered project stay outside Git
under `/home/pes/work/nfs-shift-mass-recovery-20261017-artifacts/` and
`/home/pes/ghidra_projects/shift-recovered-mass-20261017/`.

To repeat recovery in the isolated copy:

```bash
GHIDRA_HOME=/opt/ghidra tools/ghidra/run_p1b_orphan_function_recovery_batch3.sh \
  /home/pes/ghidra_projects/shift-recovered-mass-20261017 shift SHIFT.exe \
  evidence/p1b_orphan_function_recovery_batch3_plan.tsv \
  /home/pes/work/nfs-shift-mass-recovery-20261017-artifacts/p1b-manual-followup/batch3-recovered-functions.tsv
```

Then rebuild the report with the retained raw exports:

```bash
python tools/ghidra/build_p1b_orphan_function_recovery_batch3.py \
  --executable /home/pes/ghidra_projects/shift/SHIFT.exe \
  --plan-tsv evidence/p1b_orphan_function_recovery_batch3_plan.tsv \
  --metadata-jsonl /home/pes/work/nfs-shift-mass-recovery-20261017-artifacts/p1b-manual-followup/batch3-address-metadata.jsonl \
  --fourb-slice /home/pes/work/nfs-shift-mass-recovery-20261017-artifacts/p1b-manual-followup/4b-region-broader.jsonl \
  --small-slice /home/pes/work/nfs-shift-mass-recovery-20261017-artifacts/p1b-manual-followup/remaining-candidate-slices.jsonl \
  --pointer-slice /home/pes/work/nfs-shift-mass-recovery-20261017-artifacts/p1b-full-program-index/near-orphan-pointer-candidate-slices.jsonl \
  --boundary-slice /home/pes/work/nfs-shift-mass-recovery-20261017-artifacts/p1b-manual-followup/5fccc-boundary-slice.jsonl \
  --xref-tsv-gz /home/pes/work/nfs-shift-mass-recovery-20261017-artifacts/p1b-full-program-index/shift.xrefs.tsv.gz \
  --wrapper-report evidence/p1b_orphan_wrapper_function_recovery.json \
  --previous-report evidence/p1b_address_taken_orphan_function_recovery_batch2.json \
  --prior-report evidence/p1b_address_taken_orphan_function_recovery.json \
  --recovered-plan-tsv /home/pes/work/nfs-shift-mass-recovery-20261017-artifacts/p1b-manual-followup/batch3-recovered-functions.tsv \
  --recovered-instructions-jsonl /home/pes/work/nfs-shift-mass-recovery-20261017-artifacts/p1b-manual-followup/batch3-recovered-function-instructions.jsonl \
  --recovered-references-tsv /home/pes/work/nfs-shift-mass-recovery-20261017-artifacts/p1b-manual-followup/batch3-recovered-target-references.tsv \
  --copy-project-name shift-recovered-mass-20261017 \
  --output evidence/p1b_orphan_function_recovery_batch3.json
```

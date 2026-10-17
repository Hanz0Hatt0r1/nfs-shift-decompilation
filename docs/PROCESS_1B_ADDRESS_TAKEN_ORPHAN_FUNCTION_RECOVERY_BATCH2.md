# Process 1B / P1.3B — address-taken orphan recovery, batch 2

This batch restores 22 address-taken functions in the isolated Ghidra project
copy `shift-recovered-mass-20261017`. Each entry has exact incoming data
references; every body instruction was unowned in the original project, lies
in executable `.text`, has P-code, and is reachable through the bounded CFG.
The evidence builder compares the original and recovered instruction bytes and
P-code, checks predecessor/gap bytes, and verifies each call reference and its
recovered caller owner.

The batch adds 1,731 instructions/P-code rows across 5,567 bytes. It assigns
owners to 34 of the 60 exact orphan callsites; 52 now have recovered callers
and 8 remain. The combined export corpus has 784 unique functions, 113,203
instructions and 113,019 P-code-bearing instructions. No semantic names or
game-specific behavior claims were added. The original Ghidra project remains
unchanged.

The checked-in plan and hash-pinned report are
[`evidence/p1b_address_taken_orphan_function_recovery_batch2_plan.tsv`](../evidence/p1b_address_taken_orphan_function_recovery_batch2_plan.tsv)
and
[`evidence/p1b_address_taken_orphan_function_recovery_batch2.json`](../evidence/p1b_address_taken_orphan_function_recovery_batch2.json).
Raw Ghidra exports are kept outside Git under
`/home/pes/work/nfs-shift-mass-recovery-20261017-artifacts/`.

To repeat the isolated-copy mutation:

```bash
GHIDRA_HOME=/opt/ghidra tools/ghidra/run_p1b_address_taken_recovery_batch2.sh \
  /home/pes/ghidra_projects/shift-recovered-mass-20261017 shift SHIFT.exe \
  evidence/p1b_address_taken_orphan_function_recovery_batch2_plan.tsv \
  /home/pes/work/nfs-shift-mass-recovery-20261017-artifacts/p1b-full-program-index/batch2-recovered-functions.tsv
```

Then rebuild the checked-in report from the pinned executable and retained
read-only Ghidra exports:

```bash
python tools/ghidra/build_p1b_address_taken_function_recovery_batch2.py \
  --executable /home/pes/ghidra_projects/shift/SHIFT.exe \
  --plan-tsv evidence/p1b_address_taken_orphan_function_recovery_batch2_plan.tsv \
  --raw-dir /home/pes/work/nfs-shift-mass-recovery-20261017-artifacts/p1b-full-program-index \
  --callsite-raw-dir /home/pes/work/nfs-shift-mass-recovery-20261017-artifacts/p1b-unresolved-callsites \
  --wrapper-report evidence/p1b_orphan_wrapper_function_recovery.json \
  --previous-report evidence/p1b_address_taken_orphan_function_recovery.json \
  --copy-project-name shift-recovered-mass-20261017 \
  --output evidence/p1b_address_taken_orphan_function_recovery_batch2.json
```

The runner refuses any project directory other than the isolated recovered
copy. The report builder fails closed if plans, hashes, CFG bodies, references,
or exact caller ownership drift.

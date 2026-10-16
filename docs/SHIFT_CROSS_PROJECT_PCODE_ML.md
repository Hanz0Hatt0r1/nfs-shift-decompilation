# SHIFT cross-project portable P-code probe

This probe applies the generic `revenginstr` portable high-P-code core to the
analyzed PC retail `SHIFT.exe` program.

It is a **triage/OOD tool**, not semantic authority. It does not close P1.3 and it
must not replace exact PC-retail provenance evidence for the control chain.

## Playable-slice blocker

The immediate consumer is P1B / P1.3. The current control frontier still contains
multiple computed forwarding/receiver provenance questions. The probe provides a
mass portable-code view that can prioritize functions/families for exact static
proof while keeping the semantic gate fail-closed.

## Generic core

The project-neutral implementation now lives in:

```text
Hanz0Hatt0r1/revenginstr
```

Clone it next to this repository:

```bash
cd ~
git clone https://github.com/Hanz0Hatt0r1/revenginstr.git
```

or set an explicit path:

```bash
export REVENGINSTR_REPO=/path/to/revenginstr
```

When `REVENGINSTR_REPO` is not set, the runner uses `../revenginstr` when
available. The shared repository is required for the exporter, audit and foreign
guard; the Shift-local exporter fallback has been removed. The historical audit
and guard commands remain thin adapters for callers that need their older
`SHIFT.*` output formats.

The revenginstr exporter emits:

```text
REVENGINSTR.PcodeCorpus/1
```

`model_text` intentionally excludes absolute function/instruction addresses,
function and symbol names, disassembly/bytes, decompiler C, strings/resources,
direct call target identity, branch-target bookkeeping, high-P-code `INDIRECT`
iop bookkeeping and LOAD/STORE address-space IDs.

For 32-bit x86 the normalized header is:

```text
ARCH=X8632
ENDIAN=LE
PTR_SIZE=4
```

The representation caps model input at 256 high-P-code operations with a
deterministic head+tail selection. `source_entry` and `source_name` remain outer
audit/join metadata only.

## One-command probe

The Ghidra project must already contain an analyzed `SHIFT.exe`. No analyzers are
rerun.

Historical foreign-model baseline:

```bash
cd ~/nfs-shift-decompilation

GHIDRA_HOME=/opt/ghidra \
REVENGINSTR_REPO=~/revenginstr \
NEVERGONE_REPO=~/nevergone-recomp \
bash tools/ml/run_shift_cross_project_pcode_probe.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/ml-cross-project
```

The default export is 1000 internal functions. Override with:

```bash
SHIFT_ML_MAX_FUNCTIONS=5000
```

For a focused static frontier:

```bash
SHIFT_ML_NAME_CONTAINS=FUN_0070
```

## Classifier migration

The generic classifier implementation now lives in revenginstr as
`REVENGINSTR.SelectiveClassifier/1`. However the runner does **not** automatically
switch from the retained historical Nevergone v4 model. A generic model is used
only when a validated model directory is explicitly supplied:

```bash
GHIDRA_HOME=/opt/ghidra \
REVENGINSTR_REPO=~/revenginstr \
REVENGINSTR_MODEL_DIR=~/.local/share/nevergone-ml-v2/models/revenginstr-selective-v1 \
bash tools/ml/run_shift_cross_project_pcode_probe.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/ml-cross-project-generic
```

Before using that path for retained comparisons, run the Nevergone migration
suite and require strict v4/v5.2 parity plus the generic accept-router production
gate. Until then, leaving `REVENGINSTR_MODEL_DIR` unset preserves the historical
Nevergone transfer path when `NEVERGONE_REPO` is provided.

The generic-model path emits:

```text
revenginstr-selective-transfer.jsonl
revenginstr-selective-transfer-foreign-guard.jsonl
```

This migration changes implementation ownership, not semantic authority. Even a
parity-validated generic artifact is still trained on Nevergone labels and is a
foreign structural/OOD probe on SHIFT.

## Foreign-project guard

The first real 1000-function x86-32 run established the baseline:

```text
rows                     1000
architecture             X8632 (1000/1000)
portable contract pass   true
leakage findings         0
base accept fraction     0.288
family similarity median 0.669450
contrast margin median   0.000123
```

These predictions are **not SHIFT semantic labels**. The monotone foreign guard
can only demote a foreign-model `accept` to `review`; it never promotes review or
escalate. The default diagnostic floors are:

```text
family_similarity >= 0.70
contrast_margin    >= 0.05
```

They are safety floors, not thresholds fitted to SHIFT labels. Do not tune them
against hand-picked P1.3 answers.

## Outputs

Historical model path:

```text
out/ml-cross-project/
  shift-pcode.jsonl
  nevergone-v4-transfer.jsonl
  nevergone-v4-transfer-foreign-guard.jsonl
  cross-project-audit.json
```

Generic validated model path:

```text
out/ml-cross-project-generic/
  shift-pcode.jsonl
  revenginstr-selective-transfer.jsonl
  revenginstr-selective-transfer-foreign-guard.jsonl
  cross-project-audit.json
```

The runner's audit format is `REVENGINSTR.PcodeAudit/1`. Calling the retained
`audit_shift_cross_project_pcode.py` adapter directly preserves
`SHIFT.CrossProjectPcodeAudit/2`. Both report portable-contract/leakage status
plus prediction/action/similarity/contrast and zero-promotion routing
information.

## Interpretation

There are no SHIFT semantic labels in this probe. A Nevergone-trained prediction
such as `game`, `engine`, `runtime_library` or `media_library` is therefore **not**
a recovered SHIFT semantic fact, regardless of whether inference is executed by
the historical Nevergone CLI or the generic revenginstr classifier implementation.

The useful signal is OOD/selective behavior. Coherent structural neighborhoods can
only prioritize exact P1.3 analysis; they cannot assert receiver/producer
ownership. The retained 1000-function run is the cross-project baseline for later
generic frontend/ABI/model improvements.

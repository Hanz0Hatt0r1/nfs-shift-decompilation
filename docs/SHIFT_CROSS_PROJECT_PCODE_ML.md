# SHIFT cross-project portable P-code probe

This probe ports the architecture-neutral high-P-code representation developed in
the Nevergone ML testbed to the analyzed PC retail `SHIFT.exe` program.

It is a **triage/OOD tool**, not semantic authority. It does not close P1.3 and it
must not replace exact PC-retail provenance evidence for the control chain.

## Playable-slice blocker

The immediate consumer is P1B / P1.3. The current control frontier still contains
multiple computed forwarding/receiver provenance questions. The probe provides a
mass portable-code view that can prioritize functions/families for exact static
proof while keeping the semantic gate fail-closed.

## Portable representation

`tools/ghidra/ShiftMlPcodeCorpusExporter.java` exports format:

```text
SHIFT.MlPcodeCorpus/1
```

`model_text` intentionally excludes:

- absolute function/instruction addresses;
- function and symbol names;
- disassembly and instruction bytes;
- decompiler C;
- strings/resources;
- direct call target identity;
- branch target bookkeeping;
- high-P-code `INDIRECT` iop bookkeeping;
- LOAD/STORE address-space IDs.

The representation retains normalized architecture/ABI scale and structural
P-code evidence. For a normal 32-bit x86 Ghidra language ID such as
`x86:LE:32:default`, the header is expected to be:

```text
ARCH=X8632
ENDIAN=LE
PTR_SIZE=4
```

The representation caps model input at 256 high-P-code operations using a
deterministic head+tail selection. Large constants are bucketed; small constants
remain because field offsets, flags and loop bounds are useful structural evidence.

`source_entry` and `source_name` remain outer audit/join metadata only.

## One-command probe

The Ghidra project must already contain an analyzed `SHIFT.exe`. No analyzers are
rerun.

```bash
cd ~/nfs-shift-decompilation

GHIDRA_HOME=/opt/ghidra \
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

When `NEVERGONE_REPO` is set, the runner uses the P-code-only Nevergone v4 model
by default:

```text
~/.local/share/nevergone-ml-v2/models/production-code-domain-v4
```

Override with `NEVERGONE_MODEL_DIR` when needed.

## Outputs

```text
out/ml-cross-project/
  shift-pcode.jsonl
  nevergone-v4-transfer.jsonl      # when model probe is enabled
  cross-project-audit.json
```

The audit reports:

- exporter/decompile success counts;
- architecture, endian and pointer-size distributions;
- 256-op cap/truncation behavior;
- obvious source-name/source-entry/program leakage checks;
- prediction/action distribution from the foreign Nevergone model;
- confidence, family-similarity and contrast-margin quantiles;
- cross-project `accept` fraction.

## Interpretation

There are no SHIFT semantic labels in this probe. A Nevergone prediction such as
`game`, `engine`, `runtime_library` or `media_library` is therefore **not** a
recovered SHIFT semantic fact.

The useful signal is OOD/selective behavior:

- mostly `review`/`escalate` with low family similarity is healthy foreign-project
  rejection;
- a high `accept` rate with weak similarity indicates an OOD-gate portability
  problem;
- coherent structural neighborhoods can be used only to prioritize exact P1.3
  analysis, not to assert receiver/producer ownership.

The first cross-project run should be frozen and compared against later generic
front-end/ABI improvements instead of repeatedly resampling until the metrics look
better.

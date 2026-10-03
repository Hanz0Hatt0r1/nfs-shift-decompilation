# Attach memory-wrapper forwarding to class evidence

The normal class-evidence pipeline intentionally runs without requiring a
second targeted Ghidra instruction export. It already writes
`memory_wrapper_callsites.json` from recovered `SHIFT.exe.c` plus the structured
whole-program Ghidra callgraph.

When `SHIFT-MEMORY-WRAPPER-FORWARDING/1` is available, use
`tools/shift_live_dump/attach_memory_wrapper_forwarding.py` to add the stronger
source-expression -> wrapper-storage -> backend-storage provenance layer to the
same output directory.

## Run

First build the normal class evidence:

```bash
python3 tools/shift_live_dump/build_class_evidence_pipeline.py \
  /path/to/SHIFT.exe.c \
  --exe /path/to/SHIFT.exe \
  --ghidra-export out/shift_ghidra_database \
  --out out/class_evidence
```

Produce the targeted wrapper forwarding report independently with the existing
one-shot Ghidra runner:

```bash
GHIDRA_HOME=/opt/ghidra \
./tools/ghidra/run_memory_wrapper_forwarding.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/memory_wrapper_forwarding
```

Then attach it:

```bash
python3 tools/shift_live_dump/attach_memory_wrapper_forwarding.py \
  out/class_evidence \
  --forwarding out/memory_wrapper_forwarding/memory_wrapper_forwarding.json
```

The postprocessor writes:

```text
out/class_evidence/memory_wrapper_argument_join.json
```

and atomically updates `pipeline_manifest.json`.

## Manifest additions

The pipeline artifact inventory gains `memory_wrapper_argument_join`. Counts are
added for:

- joined wrapper callsites;
- callsites with a forwarding record;
- join-ready callsites;
- Ghidra-crosschecked joins;
- total modeled backend arguments;
- backend arguments mechanically mapped to source expressions;
- wrapper-internal backend arguments;
- unresolved backend arguments.

The manifest also records that targeted instruction forwarding was used and that
argument provenance was joined.

## Why this is a postprocessor

The whole-program class pipeline and the targeted instruction export have
different collection costs and lifetimes. Keeping the targeted layer optional
means class/RTTI/layout analysis can still run from the existing export even when
the five-function instruction capture has not been refreshed.

Once the targeted report exists, the postprocessor performs a deterministic join
without reopening Ghidra.

## Evidence boundary

Attaching forwarding does not change the semantic promotion boundary. The
manifest explicitly keeps these false:

- `argument_roles_proven`;
- `allocator_abi_proven`;
- `release_abi_proven`;
- `ownership_semantics_proven`.

A mapped source expression proves value provenance only. For example, observing
that `count * 4` reaches a specific backend storage slot is not by itself enough
to name that slot `byte_count`; that requires an additional independent join to
allocation diagnostics, recovered layout geometry or runtime behavior.

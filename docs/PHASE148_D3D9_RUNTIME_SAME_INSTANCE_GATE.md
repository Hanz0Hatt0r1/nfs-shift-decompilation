# Phase 148 — strict D3D9 runtime same-instance gate

`SHIFT.D3D9RuntimeBindingEvidence/1` now exposes `same_instance_gate` as a separate
acceptance layer. Existing `status=observed` semantics remain for backwards compatibility.

## Proof requirements

- the frame binds the same MEB resource identity (SHA-256 or exact normalized path);
- the bound declaration pointer was actually created in the capture;
- that bound declaration decodes with status `match`;
- a MEB usage-ordinal mapping is explicitly supplied;
- at least one MEB property descriptor matches a record in that bound declaration.

A declaration object that matches the descriptor but was never bound by the target frame
does not count.

## Strict CLI mode

```bash
python shift_importer.py d3d9-runtime-trace trace.jsonl runtime.json \
  --meb-resource meb.json \
  --usage-map usage.json \
  --require-same-instance
```

Without `--require-same-instance`, the parser still produces the observational report.
With it, exit code `2` means the strict gate is not proven.

## Boundary

The gate still does not establish runtime authenticity by itself; the capture provenance
and process attribution remain part of the external runtime evidence chain.
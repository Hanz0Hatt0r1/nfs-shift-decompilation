# Phase 135 — RenderCommand constant parity

`SHIFT.RenderCommandConstantParity/1` checks that the final renderer submission preserves
the c-register ranges derived from `SHIFT.MaterialUniformBinding/1` and packed into
`SHIFT.MaterialConstantPayload/1`.

Each expected binding must have the same stage/register start/register count in
`constant_commands`; command byte offsets must equal `register_index * 16`; the packed
payload must contain the same register. Extra command ranges are blockers.

The unified `SHIFT.BMWRuntimeGoldenGate/1` invokes this check for constant-bearing
commands. A command with no material constants is not forced to synthesize an empty
payload.

## CLI

```bash
python shift_importer.py render-command-constant-parity render-command.json parity.json
```

## Next

With the offline constant chain closed, the remaining external dependency is the real
BMW runtime capture. The next golden-path execution is:

`runtime capture -> schema -> trace integrity -> Usage bridge -> shader/resource join
-> constant/declaration/vertex parity -> exact draw -> RenderCommand -> reference render`.
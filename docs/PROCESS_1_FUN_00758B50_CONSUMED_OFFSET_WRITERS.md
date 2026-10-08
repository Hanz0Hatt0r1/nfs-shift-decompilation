# Process 1 — `FUN_00758b50` consumed-offset writer candidates

## BLOCKER

P1.3 needs exact PC-retail input/control producer provenance. The prior `SHIFT.Fun00758b50InputSurfaceInventory/1` probe inventories raw offsets and calls inside `FUN_00758b50`, but it does not answer which upstream functions write the values that the wheel path consumes.

This layer adds a whole-source navigation join without promoting control semantics.

## Tool

```text
tools/ghidra/trace_fun_00758b50_consumed_offset_writers.py
```

Output format:

```text
SHIFT.Fun00758b50ConsumedOffsetWriterCandidates/1
```

The analyzer consumes:

1. the authoritative PC-retail `SHIFT.exe.c` snapshot;
2. a generated `SHIFT.Fun00758b50InputSurfaceInventory/1` report.

It refuses a source whose SHA-256 differs from:

```text
512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9
```

The paired retail executable identity remains:

```text
eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

## Candidate selection

The tool first selects offsets that are referenced inside `FUN_00758b50` but never appear on an assignment LHS inside that same target body. These are navigation candidates for values consumed read-only by the target.

It then scans every recovered `FUN_XXXXXXXX` definition in the same pinned source for direct assignment LHS expressions containing the exact numeric offset.

For every candidate offset the report records:

- target reference count and source lines;
- direct assignment writer sites outside `FUN_00758b50`;
- unique candidate writer functions;
- writer-site count;
- whether any direct source-visible writer was found.

Results are ranked toward the narrowest direct-writer surface first.

## Evidence boundary

A matching numeric offset is **not** proof that two functions operate on the same object. Before a candidate writer can become a P1.3 producer contract, its receiver/base provenance must be joined to the exact `FUN_00758b50` HDVehicle/wheel object.

Likewise, the scan is intentionally not alias-complete. It does not recover:

- stores through local pointer aliases whose LHS no longer contains the literal offset;
- writes hidden inside callees;
- computed offsets not rendered as `+0x...` in the recovered source;
- control semantics for any value.

Therefore a direct writer candidate may guide the next targeted proof, but it cannot by itself identify throttle/brake/steering or any other player-control quantity.

## P1.3 gate

This tool changes navigation quality only:

```text
source-visible direct writer candidates enumerated = true
alias-complete writer ownership proven             = false
retail control semantics proven                    = false
P1.3 control producer complete                     = false
```

The provider count remains **7**. The existing native `VehicleControlIntent` boundary remains host-side only and is not used as retail evidence.

## Run

```bash
python3 tools/ghidra/inventory_fun_00758b50_input_surface.py \
  /path/to/SHIFT.exe.c \
  --output out/fun_00758b50_input_surface.json

python3 tools/ghidra/trace_fun_00758b50_consumed_offset_writers.py \
  /path/to/SHIFT.exe.c \
  out/fun_00758b50_input_surface.json \
  --output out/fun_00758b50_consumed_offset_writers.json
```

## NEXT_STEP

Take the highest-ranked candidate with a small writer set, prove receiver/base provenance from that writer to the exact selected BMW `FUN_00758b50` object, then trace the writer's stored value backward. Only after that value reaches a PC-retail input/control producer may P1.3 promote the corresponding control link.

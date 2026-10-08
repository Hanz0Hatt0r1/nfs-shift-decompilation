# Process 1A — `FUN_00713630` upstream direct surface

## BLOCKER

After P1.1c closure, P1.1a is the only remaining Process 1A blocker before the final `FUN_00766510/contact_response` handoff. Phase 748 reconstructed the arithmetic but deliberately left the earlier inputs fail-closed.

## OUTPUT

`SHIFT.Fun00713630UpstreamDirectSurface/1` bounds the easy/direct surfaces without inventing ownership.

The cadence chain is exact: `FUN_00715380` calls `FUN_007144a0` at `0x0071557d` with the same receiver, `FUN_007144a0` computes signed `receiver+0x158 % 3`, and only on remainder zero calls `FUN_00713630` at `0x007144bd` with that receiver preserved.

Inside `FUN_00713630`, participants are traversed through receiver `+0x140`, count `+0x144`, stride `0x1fa0`, and active byte `+0x4e`. The participant pointer is dereferenced before the writer consumes history `+0x2b10` and f32 `+0x4b0`.

All seven Phase748 config globals have exactly one literal address occurrence in the entire retail image, and every occurrence is the known read in `FUN_00712940` or `FUN_00713630`. No direct literal-address store exists. This closes only the direct-literal surface: computed-address, alias, loader, relocation, or bulk materialization remains open.

`FUN_00727870`, the source-visible history writer, has exactly two direct callers in the exported retail call graph: `FUN_0073e360` at `0x0073f293` and `FUN_007473b0` at `0x0074752c`. The writer shifts the three-lane history from `+0x2b10` to `+0x2b1c` to `+0x2b28` before materializing a qualifying new sample into `+0x2b10`.

A `+0x4b0` f32 store exists at `0x00748956` in `FUN_00748280`, sourced from `DAT_00b078d4`. It is retained only as an identity candidate: matching `+0x4b0` offsets do not prove that this receiver is the participant consumed by `FUN_00713630`.

## GATES_CHANGED

- P1.1c: **closed**.
- P1.1a cadence machine chain: **closed**.
- P1.1a config direct-literal surface: **closed**, alias/materialization ownership still open.
- P1.1a sample writer direct-call surface: **closed**, selected-participant scheduling still open.
- P1.1a participant `+0x4b0` ownership: **open**.
- P1.1a complete: **false**.
- P1.1 complete: **false**.
- provider removal: **unauthorized**.
- external provider count: **7**.

## NEXT_STEP

Root both `FUN_00727870` receiver paths to the selected participant domain, resolve computed/alias materialization of the seven config globals, and join or reject the `FUN_00748280+0x4b0` candidate using exact object provenance.

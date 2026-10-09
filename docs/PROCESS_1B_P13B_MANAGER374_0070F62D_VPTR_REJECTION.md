# Process 1B / P1.3B: `0x0070f62d` computed `manager+0x374` receiver rejection

After the 2026-10-09 P1.3 redistribution, Process 1B owns computed forwarding sites `0x005f6eda` and `0x0070f62d` plus the final manager/HDVehicle identity join and slot2 adjudication.

The `0x0070f62d` path is in `FUN_0070f580`. Machine transfer captures entry ECX in ESI at `0x0070f59b`, then writes exact vptr `0x00b04524` to `[esi]` at `0x0070f5a0`. The target materializer later computes `ECX = ESI + 0x374` before calling `FUN_006310c0`.

Participants Manager uses root vptr `0x00ab9190` and embedded `+0x20` vptr `0x00ab916c`. Because the same receiver is explicitly identified as the `0x00b04524` object before the materializer, `0x0070f62d` cannot be a Participants Manager `+0x374` path.

This proof is intentionally shard-local. It closes only the P1.3B site `0x0070f62d`; it does not claim Process 1D ownership sites `0x0070fb45` or `0x0070fdeb`. The remaining P1.3B computed path is `0x005f6eda`.

The manager `+0x374 -> HDVehicle+0x4330` join, final `0x004b86cf` / slot2 adjudication, P1.3 completion, and provider removal remain fail-closed. Provider count remains 7.

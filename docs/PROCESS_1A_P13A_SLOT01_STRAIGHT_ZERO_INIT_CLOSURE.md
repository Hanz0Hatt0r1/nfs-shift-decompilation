# Process 1A / P1.3A — shallow straight-line zero-init closure

## Scope

After the REP/bare-string, loop-based custom init, nonzero unrolled MOV, and exact-overlap subsets were closed, one separate ordinary-integer class remained: straight-line zero initialization performed with ordinary `MOV` stores rather than a named memory helper or a backward-branch loop.

The analyzer follows direct calls from the four recovered P1.3A wheel/physics roots through depth four, propagates integer zero through registers, excludes stack destinations and stores covered by backward-branch loops, and requires at least eight contiguous zeroed bytes on one non-stack destination base. Callgraph reachability is navigation evidence only; exact receiver provenance adjudicates identity.

## Authoritative result

PC retail 1.02 plus the pinned Drive Ghidra SQLite index produce exactly six candidates. All six are rejected as writers of selected `HDVehicle+0x938` / `HDVehicle+0x13b8`:

- `FUN_00887580` — fixed singleton `0x00c29640`; this receiver was independently pinned by the merged REP closure.
- `FUN_00647a10` — on the bounded depth-four path it is the base constructor of the same `0x00c29640` singleton.
- `FUN_0070fae0` — exact singleton receiver `0x00c104e0`, installing Physics Manager vptr `0x00b04524`.
- `FUN_0087aa00` — the relevant caller enters from `HDVehicle+0x6730`, then invokes the helper on only `HDVehicle+0x6754` and `HDVehicle+0x6814`; its zero stores are local `+0/+0xc/+0x10/+0x14` fields of those high service subobjects.
- `FUN_00886e10` — exact fixed-singleton nested receiver `0x00c29640+0x70c = 0x00c29d4c`, already corroborated by the REP closure.
- `FUN_0088f110` — exact fixed-singleton nested receiver `0x00c29640+0x558 = 0x00c29b98`.

The scan is hash-locked to `SHIFT.exe` SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1` and `shift_ghidra.sqlite` SHA-256 `ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e`.

## Gate

```text
shallow straight-line zero-init depth<=4 complete = true
candidate functions                                = 6
candidates rejected                                = 6
selected-HDVehicle target writer found             = false
SSE/vector copy-init ruled out                     = false
deeper direct aliases ruled out                    = false
indirect/callback aliases ruled out                 = false
slot0 complete                                     = false
slot1 complete                                     = false
P1.3 complete                                      = false
provider count                                     = 7
```

## Limits / next step

This closes only straight-line ordinary `MOV` zero initialization within four direct edges. REP/bare string operations, loop stores, and nonzero ordinary-MOV copies are already covered by earlier P1A contracts. SSE/vector initialization and copy shapes, deeper direct aliases, and indirect/callback carriers remain open.

Next, inventory and adjudicate shallow SSE/vector copy-init sequences. Only after that bounded class is closed should P1A widen to deeper or indirect carriers, and only when an exact selected-HDVehicle-derived destination alias survives.

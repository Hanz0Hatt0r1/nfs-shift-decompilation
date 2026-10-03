# Outer-update callsite static contract

`tools/ghidra/build_outer_update_callsite_contract.py` cross-checks the recovered
`SHIFT.exe.c` snapshot against the structured Ghidra callgraph immediately above
`FUN_00770e80`. Its output format is `SHIFT.OuterUpdateCallsiteStatic/1`.

The checked inputs are:

- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`;
- Ghidra `SHIFT.exe` MD5:
  `705af8b420e5eb1e3834ac43d5533c6b`;
- Ghidra language: `x86:LE:32:default`;
- pointer size: 4 bytes.

No game execution or runtime capture is involved.

## `FUN_00770e80` call ABI

The source definition begins at line 765608 in the pinned recovered source.
Both proven direct callsites pass `&DAT_00c13700` as the receiver.

Inside `FUN_00770e80` the two 64-bit parameters are stored at different points
in the update:

```text
param_2 -> receiver +0xa0   before the two FUN_0076d100 passes
param_1 -> receiver +0x98   after the two FUN_0076d100 passes
param_3 -> forwarded into both FUN_0076d100 calls
```

The established BODY schedule below those calls remains:

```text
FUN_00770e80
  -> FUN_0076d100
  -> FUN_00765470
       -> ... -> FUN_007b4110
       -> FUN_007b2270
            -> FUN_007bab70
  -> FUN_0076d100
  -> FUN_00765470
       -> ... -> FUN_007b4110
       -> FUN_007b2270
            -> FUN_007bab70
```

The source establishes storage and forwarding, not the physical units or final
semantic names of `param_1`, `param_2`, or `param_3`.

## `FUN_00794a30`

The source definition starts at line 791140. Before its conditional outer-update
call it writes two 64-bit channels into its own object:

```text
caller +0x1aa8 <- CONCAT44(param_2, param_1)
caller +0x1ab0 <- CONCAT44(param_4, param_3)
```

The `FUN_00770e80` call is gated by both:

```text
param_5 != 0
caller +0x234 == 0
```

and forwards the two freshly supplied values to `&DAT_00c13700`, with the final
mode byte equal to zero.

Immediately afterwards the source contains the same four-call sequence already
visible in the Ghidra caller frontier:

```text
FUN_0078ef00
FUN_00793ca0
FUN_007aa750
FUN_007851d0
```

This is source + callgraph corroboration of an update call shape, not proof of a
class name.

## `FUN_0079b2d0`

The source definition starts at line 794922. Its case-zero path is gated by:

```text
caller +0x34 != 0
switch(caller +0x234) == case 0
```

That case reads the same two caller-object channels:

```text
caller +0x1aa8
caller +0x1ab0
```

and forwards them to `FUN_00770e80(&DAT_00c13700, ..., ..., 1)`. The same four
post-call helpers then execute in the same order.

The current direct Ghidra callgraph still has no incoming call edge to
`FUN_0079b2d0`. `switches.jsonl` records one internal computed-jump candidate at
`0x0079b2ec`, but that does not identify the function's external dispatcher.
The missing owner therefore remains an explicit blocker.

## Bounded upstream structure through `FUN_00713050`

The source definition of `FUN_00713050` starts at line 705910 and the Ghidra
callgraph contains exactly three direct calls from it to `FUN_00794a30`.

The function exposes a repeatable container/step shape:

```text
this +0x140  record pointer array/base
this +0x144  record count
record stride = 0x1fa0
child object = *record + 0x340
this +0x348  source-visible accumulator
this +0x160  seed for the first 64-bit caller channel
rate source = *(int *)(FUN_0070fe90() + 0x388)
reciprocal expression = 1.0 / rate source
```

One source call also supplies the exact 64-bit constant bits
`0x3fa1111120000000`, which decode as approximately
`0.03333333507180214`. That numerical value is recorded as evidence only; this
contract does **not** promote it to a named time unit or timestep.

The direct upstream edge is:

```text
0x00715434  FUN_00715380 -> FUN_00713050
```

The source definition of `FUN_00715380` begins at line 707679 and independently
contains that call.

## What is now proven

This layer closes several ABI questions above the BODY integrator:

- both direct outer-update caller addresses are source/callgraph corroborated;
- both use the global `DAT_00c13700` receiver;
- caller-object `+0x1aa8/+0x1ab0` are the two 64-bit channels forwarded into
  `FUN_00770e80`;
- `FUN_00794a30` writes those fields from its arguments before its conditional
  call;
- `FUN_0079b2d0` reads the same fields in switch case zero;
- `FUN_00770e80` stores its second 64-bit parameter to `+0xa0` before the two
  physics passes and its first to `+0x98` after them;
- `FUN_00713050` exposes a `0x1fa0`-stride record container and reaches child
  objects through `*record + 0x340`;
- the three `FUN_00713050 -> FUN_00794a30` source callsites match the three
  direct Ghidra call edges.

## Still not proven

The evidence does not justify semantic promotion of:

- either 64-bit channel to a physical unit or final field name;
- `+0x234` to a named state enum;
- `+0x34` to a named enable/active field;
- `FUN_00794a30`, `FUN_0079b2d0`, `FUN_00713050`, or `FUN_00715380` to final
  class/method names;
- the record array at `+0x140` to a specific gameplay class;
- rendered-frame ownership/timing;
- controller/input ownership;
- the indirect owner/dispatcher of `FUN_0079b2d0`.

Those remain separate static frontiers.

## Run

```bash
python3 tools/ghidra/build_outer_update_callsite_contract.py \
  /path/to/SHIFT.exe.c \
  out/shift_ghidra_database \
  --json-out out/outer_update_callsite_static.json
```

The source hash and PE identity are checked fail-closed. If either snapshot or
any required direct-call/source relationship changes, the tool refuses to emit
the contract instead of silently weakening it.

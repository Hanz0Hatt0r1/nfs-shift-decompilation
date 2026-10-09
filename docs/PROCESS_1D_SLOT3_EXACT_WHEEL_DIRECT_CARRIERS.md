# Process 1D — slot3 exact wheel direct-carrier closure

## Scope

This closes only the exact selected-wheel direct paths materialized inside `FUN_00770e80`.

Semantic object identity is inherited from merged `SHIFT.P1A.P13ASlot01X87ReuseTrancheClosure/1`:

- `FUN_00770e80` receiver = `HDVehicle` root;
- `FUN_00755a60` receiver = `HDVehicle+0x400+slot*0xa80`;
- `FUN_00760b50` receiver = the same wheel-runtime object.

Retail machine transfer, not numeric offset equality, adjudicates the new P1D conclusions.

## Exact slot3 paths

### `FUN_00770e80 -> FUN_00755a60 -> FUN_00752fc0`

The four-wheel loop starts from `EDI=HDVehicle+0x740`, advances by `0xa80`, and at `0x007710c9` sets `ECX=EDI-0x340`. Therefore slot 3 is exactly `HDVehicle+0x2380` before `0x007710cf -> FUN_00755a60`.

`FUN_00755a60` writes only wheel-local:

```text
+0x7b0 +0x7b8 +0x7c0 +0x7c8 +0x7f8 +0x800 +0x850
```

It forwards the exact wheel root only once, via `mov ecx,esi` at `0x00755db3` to `FUN_00752fc0`. That leaf writes only:

```text
+0x5b8 +0x7d8
```

and has no direct calls. None overlaps selected `+0x538..+0x53f`.

### `FUN_00770e80 -> FUN_00760b50`

At `0x00771177`, retail code explicitly materializes `ECX=HDVehicle+0x2380`, then calls `FUN_00760b50` at `0x00771180`.

`FUN_00760b50` writes only wheel-local:

```text
+0x368 +0x868 +0x888 +0x8b0
```

Its direct calls receive stack/helper domains, fixed globals, math-wrapper state, or the child pointer `[wheel+0x420]`; no direct callee receives the exact wheel root. No bounded write overlaps selected `+0x538..+0x53f`.

## Reproduction

```bash
python3 tools/ghidra/analyze_p1d_slot3_exact_wheel_direct_carriers_pe.py \
  /path/to/SHIFT.exe \
  evidence/p1a_p13a_slot01_x87_reuse_tranche_closure.json \
  --output out/p1d_slot3_exact_wheel_direct_carrier_closure.json
```

The verifier requires PC retail 1.02 SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1` and exact upstream identity text before checking machine anchors, writes and direct-call inventories.

## Gates

Positive bounded result:

```text
slot3_fun00770e80_exact_wheel_direct_carrier_subset_complete = true
```

Still fail-closed:

```text
deeper_direct_aliases_ruled_out      = false
indirect_callback_aliases_ruled_out  = false
slot3_writer_provenance_proven       = false
P1.3D complete                       = false
aggregate P1.3 complete              = false
external provider count              = 7
```

Next work is stored/escaped selected-wheel aliases plus indirect/callback carriers outside these two `FUN_00770e80` direct paths.

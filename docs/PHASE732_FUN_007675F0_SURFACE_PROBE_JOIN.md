# Phase 732 — native FUN_007675f0 → FUN_00759210 surface-probe join

Phase 732 closes two derived per-pass fields in the selected native `FUN_007675f0` path: `planar_delta` and `surface_scalar`.

## PC retail caller contract

Direct machine-code inspection of PC `SHIFT.exe` at `FUN_007675f0` (`0x007675f0`) proves the caller prepares current chassis BODY position as the query point:

```text
BODY pointer = HDVehicle+0x33a0
BODY0 +0x00/+0x08/+0x10 are loaded as f64
caller spills X/Y/Z to f32 before FUN_00759210
```

The node pointer is loaded separately from the `FUN_007675f0` caller input and is still an unresolved upstream boundary.

The call at `0x00767643` invokes already-native `FUN_00759210` with:

- current BODY0 position, after the source float32 spill;
- the caller-supplied node pointer;
- output point storage;
- output scalar storage.

Immediately afterward `FUN_007675f0` calls helper `0x004a7870`, whose instruction stream is an exact three-lane float32 subtraction. The operands are:

```text
FUN_00759210 returned point - BODY0 query point
```

The X/Z lanes feed the recovered planar distance/direction path. The resulting three-lane value is the existing `planar_delta` native input.

The scalar written by that same `FUN_00759210` call is later read at `0x0076793a` and feeds the already-native gap expression. It is therefore the source owner of the existing `surface_scalar` native input.

## Xbox 360 corroboration

The European Xbox 360 retail build independently mirrors the same join in the counterpart beginning at `0x8259a9f0`:

- BODY f64 lanes are rounded to f32 at `0x8259aa20..0x8259aa40`;
- the probe counterpart is called at `0x8259aa44` (`0x8258ffb8`);
- returned-point X/Z minus BODY-query X/Z follows at `0x8259aa48..0x8259aa64`;
- the same call's scalar output is consumed from stack `+104` at `0x8259ac38`.

Xbox evidence is corroboration only. PC executable instructions remain authoritative for the native PC contract.

## Native execution

`derive_fun_007675f0_body0_probe_query_position()` reads current persistent BODY0 position at each recovered pass and preserves the source f64-to-f32 spill.

`execute_fun_007675f0_surface_probe_join()` then:

1. invokes the already-native Phase 661 `execute_fun_00759210_surface_probe()`;
2. rounds the returned point/scalar through the source-visible float32 boundary;
3. forms the exact lane-wise returned-point minus BODY-query delta;
4. publishes `planar_delta` and `surface_scalar` to the lower `FUN_007675f0` arithmetic contract.

The contact-outer provider chain derives current BODY0 position immediately before the pass anchor, beside the already-owned BODY0 speed read. Therefore pass 1 observes BODY state after pass 0's half-step rather than a stale outer-frame position.

## Provider frontier

Production `ContactOuterSessionInput` no longer accepts already-derived `planar_delta` or `surface_scalar`. It now accepts the earlier source boundary:

```text
surface_probe_node
base_scalar
projected_scalar
alignment_scalar
param_3
```

Historical lower-chain fixtures retain compatibility-only derived outputs when no node pointer is supplied. Those compatibility fields are not retail evidence and are not part of the production frontier.

The top-level external provider count remains seven because this phase narrows the existing `FUN_007675f0` provider payload; it does not remove the provider itself.

## Remaining boundary

The exact source owner/producer and freshness of the node pointer passed into `FUN_007675f0`/`FUN_00759210` are not yet proven. Phase 732 deliberately exposes that earlier boundary rather than assigning a physical name or fabricating a node from unrelated state.

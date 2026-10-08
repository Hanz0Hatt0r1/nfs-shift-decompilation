# Process 1A — close selected participant `+0x4b0` runtime materialization

## BLOCKER

P1.1a was the final open Process 1 proof before the `FUN_00766510/contact_response` handoff. Runtime config ownership and sample-history scheduling were already closed; the remaining gap was the exact selected PhysicsParticipant `+0x4b0` producer consumed by `FUN_00713630`.

## OUTPUT

The exact storage identity is already proven:

```text
actual participant+0x4b0 == (actual participant+0x340)+0x170
```

`FUN_007927c0` is the canonical materializer for the subobject float3 at `+0x16c/+0x170/+0x174`. Retail machine code at `0x007927ee` writes the second f32 input to `[subobject+0x170]`, which is therefore the actual participant `+0x4b0` field.

A selected runtime manager path is explicit in `FUN_00713340`. It walks `manager+0x140` participant records with stride `0x1fa0`, dereferences `record[0]` to the actual participant, forms `actual+0x340`, and calls `FUN_007927c0`. On the conditioned path at `manager+0x15c+index`, the second float3 argument is zero, so that path materializes `actual participant+0x4b0 = +0.0f`.

This must **not** be converted into a setup constant. `FUN_0074ddc3` (`PhysicsParticipant::Restart`) calls the same selected-subobject materializer with dynamic restart data. In case 4, the second float3 comes from restart input `+0x34/+0x38/+0x3c`, so participant `+0x4b0` receives restart input `+0x38`.

Retail ordering is also closed. In `FUN_00715380`:

```text
0x0071556f  FUN_00713340   # selected runtime materialization
0x00715576  FUN_007135b0
0x0071557d  FUN_007144a0   # %3 cadence -> FUN_00713630
```

Thus selected participant materialization runs before the cadence-gated `FUN_00713630` consumer in the outer update.

## ADJUDICATION

- seven config runtime owners/materialization: **closed upstream**;
- sample-history selected scheduling: **closed upstream**;
- participant `+0x4b0` storage identity: **closed**;
- participant `+0x4b0` canonical materializer: **closed**;
- selected runtime materialization path: **closed**;
- pre-consumer ordering: **closed**;
- field is dynamic, not a setup constant: **closed**;
- P1.1a: **complete**;
- P1.1c: **complete**;
- P1.1: **complete**;
- Process 2 `contact_response` provider removal: **authorized**;
- provider count remains **7** until Process 2 actually consumes/removes the provider.

## LIMITS

The zero value is path-specific. Other selected runtime paths, including Restart, write dynamic values. Two residual root-relative `+0x4b0` direct-displacement candidates can remain as diagnostic cleanup items; they no longer block P1.1a because the selected-object producer/materializer has been positively joined.

Process 1 does not change provider count. Process 2 P2.3 owns the actual 7 -> 6 reduction after integrating this handoff in retail order.

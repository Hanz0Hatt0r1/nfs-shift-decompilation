# Process 1A / P1.3A — residual indexed wheel-root lifetimes

## Scope

The known-materializer composition left two same-function indexed candidates outside its normalized exact-root family list: `FUN_00765850` and `FUN_00765aa0`.

Both have selected-HDVehicle direct entry independently visible in retail machine code. `FUN_00765850` is called with literal `ECX=0x00c13700` at `0x0074d988` and `0x00713b0b`; `FUN_00765aa0` has the same literal receiver at `0x00713ac7`.

Each computes:

```text
wheel = HDVehicle + 0x400 + index*0xa80
```

## `FUN_00765850`

The exact wheel root is materialized in EDI at `0x0076588b` and spilled only to stack local `[EBP-0x24]` at `0x0076589a`. It performs scalar wheel-field work at `+0x505/+0x510/+0x518/+0x520`.

At `0x007659b8`, EDI stops being the root and becomes child `[wheel+0x424]`; subsequent calls use child/service/stack-local receivers. The exact root is reloaded from `[EBP-0x24]` only at `0x00765a57`, after which the remaining exact-root operation is the final scalar `+0x520` update.

No exact-root non-stack store, push, new GPR alias, or direct callee receiver handoff exists while root identity is live.

## `FUN_00765aa0`

The exact root is materialized in EDI at `0x00765ac8` and spilled only to `[EBP-0x1c]`. It initializes scalar `+0x505/+0x510/+0x518` state.

At `0x00765b5c`, EDI becomes child `[wheel+0x424]`. The original root is restored at `0x00765bf8` only for final scalar writes to `+0x505/+0x520` before return.

Again there is no exact-root non-stack store, push, new GPR alias, or exact-root ECX callee transfer.

## Gate effect

Promoted only:

- `p13a_residual_indexed_wheel_root_lifetime_subset_complete = true`.

Both exact-root persistent-escape flags are false. This does **not** negate the separate positive `FUN_0076df50 -> FUN_00a62f60` runtime queue store, so global runtime-generated pointer, reconstructed pointer, stored alias, callback/indirect-entry, slot0, slot1 and aggregate P1.3 gates remain fail-closed. Provider count stays 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_residual_indexed_wheel_root_lifetimes.py /path/to/SHIFT.exe \
  --output evidence/p1a_p13a_residual_indexed_wheel_root_lifetimes.json
pytest -q tests/test_process1a_p13a_residual_indexed_wheel_root_lifetimes.py
```

## Next step

Compose these two closed local lifetimes with the positive runtime queue-store evidence, then continue the selected-wheel callback consumer at resolved virtual target `0x0075cfb0`.

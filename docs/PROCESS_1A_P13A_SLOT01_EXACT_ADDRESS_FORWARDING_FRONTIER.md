# Process 1A / P1.3A: slot0/slot1 exact-address forwarding frontier

P1.3A still owns selected-root alias/callee/bulk-copy provenance for `HDVehicle+0x938` (slot0) and `HDVehicle+0x13b8` (slot1), both consumed as f64 values by `FUN_00755950`.

This change closes only the **exact displacement address-materializer/callee** subset. It does not claim that all subobject-relative or bulk-copy paths are exhausted.

## Full-PC-retail scalar surface

Authoritative PC retail 1.02 contains six exact `0x938` scalar uses and 35 exact `0x13b8` scalar uses.

For `0x938`, there are **zero** `LEA` address materializers. The already-audited direct literal stores are f32/object-mismatched candidates, so no new exact-address callee path exists for slot0.

For `0x13b8`, there are exactly three `LEA` materializers:

- `0x007726b3 lea eax,[esi+0x13b8]`
- `0x00772763 lea edx,[esi+0x13b8]`
- `0x007bfaa0 lea ecx,[edi+0x13b8]`

## `FUN_007725f0` pair

The first two occur in `FUN_007725f0`.

At `0x007726b3`, the pointer is passed as the second stack argument to `FUN_00771620`. That callee reads the pointed record but writes only `DWORD [arg2+0x14]`; it never writes the first qword at `arg2+0x0`.

At `0x00772763`, the pointer is passed as the second stack argument to `FUN_00771d30`. That callee likewise mutates only `DWORD [arg2+0x14]`; its floating-point accesses use `arg2+0x8`, not `arg2+0x0`. Therefore neither path can produce the f64 consumed at selected `HDVehicle+0x13b8`.

## `FUN_007bf790 -> FUN_007c5a20`

`0x007bfaa0` is a real base-qword writer path: `FUN_007c5a20` stores qwords at `[ECX]` and `[ECX+0x8]`. Exact destination provenance rejects it.

`FUN_007bf790` has one direct caller, `0x007c50ce` inside `FUN_007c3b00`. Its destination base is `EDI=[EBP+8]`, so the candidate destination is `arg1_to_FUN_007bf790+0x13b8`.

`FUN_007c3b00` has six direct retail callsites. On the three HDVehicle initialization calls (`0x0076e1d0`, `0x0076e1f6`, `0x0076e21a`), its third stack argument is `HDVehicle+0x4330`; `0x0076e1c1` materializes that base once into `EBX`, which is then pushed in each call. `FUN_007c3b00` passes that same third argument as `arg1` to `FUN_007bf790`. Thus the qword written by the `0x007bfaa0` path normalizes to `HDVehicle+0x4330+0x13b8 = HDVehicle+0x56e8`, not `HDVehicle+0x13b8`.

The remaining three `FUN_007c3b00` callsites (`0x00798fce`, `0x00798fff`, `0x00799054`) pass a stack-local object (`EBP-0x238c`) as the same third argument. Those paths therefore write stack-local `+0x13b8`, not selected HDVehicle.

## Adjudication

The exact-displacement address-forwarding subset is exhausted for both P1.3A slots:

- slot0 `+0x938`: no address materializers;
- slot1 `+0x13b8`: all three materializers rejected as target-f64 producers.

This is a frontier reduction only. Normalized wheel-subobject paths (notably `HDVehicle+0x400+slot*0xa80` with local field `+0x538`), base-plus-delta aliases, and overlapping bulk copies remain open. P1.3A slot0/slot1, aggregate P1.3, and provider removal remain fail-closed; provider count remains 7.
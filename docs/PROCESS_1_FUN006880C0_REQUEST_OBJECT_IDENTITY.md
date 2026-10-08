# Process 1 — FUN_006880c0 request-object identity

This slice closes the **source-visible direct call surface** of the remaining generic enqueue wrapper `FUN_006880c0` without broadening the Controller #1 wake claim.

## Authority

Positive claims are backed by the exact PC retail 1.02 `SHIFT.exe.c` export (`SHA-256 512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`) and the already accepted `SHIFT.Process1Fun006880c0QueueProvenance/1` contract. The Xbox 360 recomp is available on Drive but is not required for any promoted claim in this slice.

The upstream contract proves that API `param_2` is stored as `FUN_0066bb50` embedded state `+0x8`, and that `FUN_0066bada` later passes that exact field as the queue pointer to `FUN_006880c0`. The remaining question was therefore the identity of the request objects supplied to `FUN_00634ed0`, `FUN_00634f00`, and `FUN_00634f50`.

## Direct request-object surface

`FUN_00634ed0` has two source-visible direct calls. Both pass `this+0x1820` as `param_2`; this is an embedded request descriptor.

`FUN_00634f00` has three source-visible direct calls. Two use an embedded request descriptor at `this+0x1820`. The third path (`FUN_00896770`) allocates a fresh `0x220`-byte object, constructs it through `FUN_006375c0`, stores it in owner slot `+0x60`, initializes it with `FUN_00636fb0`, and passes that object to `FUN_00634f00`.

`FUN_00634f50` has twenty source-visible calls. Eighteen directly resolve to embedded request descriptors at offsets `+0x100`, `+0x120`, `+0x140`, or `+0x160`. The two forwarding definitions take `param_2`; their complete source-visible direct caller surface consists of four calls to `thunk_FUN_0046ef30`, and all four pass `param_1+0x100`.

Therefore every source-visible direct producer feeding `FUN_006880c0` supplies an operation/request object, not the recovered Controller #1 queue object (`Controller+0x08` / `ThreadState+0x5c`). `FUN_006880c0` can be removed from the source-visible Controller #1 generic queue-pointer frontier.

## Fail-closed boundary

This proof does **not** claim that arbitrary indirect calls or dynamically populated/native APC paths cannot reach the underlying generic enqueue primitive. It also does not prove render/presentation phase locking to Controller #1 or Physics Manager cadence.

The remaining source-visible generic queue-pointer blocker for Process 1 is now `FUN_006333f0`. Its queue-object identity must be classified separately before the generic alias frontier can be considered closed.

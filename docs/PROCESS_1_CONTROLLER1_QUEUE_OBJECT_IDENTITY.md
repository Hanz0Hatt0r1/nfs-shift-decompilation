# Process 1 — Controller #1 queue object identity

This slice stops treating every direct call to the generic queue primitive `FUN_00650350` as though it necessarily targeted Controller #1.

The pinned PC retail 1.02 source contains eight direct caller functions. Only two expose the controller thread-state queue field `+0x5c` directly:

- `FUN_00649b10`: the controller thread-entry self-seed path;
- `FUN_00662ee0`: the explicit controller enqueue wrapper.

The only direct source-visible caller of `FUN_00662ee0` is `FUN_006499e8`, the generic thread teardown/shutdown enumerator, which sends message `0`. That is lifecycle shutdown, not a recovered steady-state render/presentation wake producer.

Six direct callers of `FUN_00650350` still operate through generic queue pointers and cannot be attributed to Controller #1 by API name alone: `FUN_0057e5b0`, `FUN_0057e820`, `FUN_006333f0`, `FUN_006503d0`, `FUN_00655220`, and `FUN_006880c0`.

The companion BManager queue-wake proof resolves `FUN_00655220` further by joining its target object through the BManager controller registry. The remaining generic pointer aliases stay fail-closed until their queue-object ownership is proved.

This evidence does not establish an APC wake source or render/presentation phase locking.

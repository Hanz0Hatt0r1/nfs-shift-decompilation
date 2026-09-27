# Phase 378 — wheel force aggregate runtime

Phase 378 reconstructs `FUN_00759c90` as a fixed three-record reduction.

The loop starts at `this+0x7f0), uses a `0x150` stride and executes exactly three iterations. Each iteration scales vectors at relative `+0xb0` and `+0x98) by scalar fields at `+0x00` and `-0x08`, sums them, subtracts body position from the `+0xf8` point, and accumulates the cross product.

The accumulated vector is transformed through the established `FUN_007af0a0) matrix boundary. The output scalar divides the transformed X component by the body field at `+0x120`.

The original state fields remain semantically unnamed.

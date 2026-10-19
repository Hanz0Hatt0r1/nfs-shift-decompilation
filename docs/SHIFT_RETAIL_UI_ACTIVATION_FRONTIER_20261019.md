# Retail UI activation frontier

Updated 2026-10-19. These bounded probes refine the UI activation blocker
without changing guest state or forcing the gate.

## Probe boundary

The v223, v225, v226 and v228 probes use the pinned PC retail 1.02 executable
(SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`),
the cumulative startup module set recorded in the v215 replay evidence, 120
host frames and Vulkan validation. Each reaches the same `host-frame-loop`
checkpoint: 96,082 dispatches, 1,559 unique functions, 120 clear submissions,
120 present submissions and zero validation errors. The reports retain the
no-guest-draw result. Raw retail files and full probe logs remain outside Git;
their hashes and summaries are in the [machine record](../evidence/retail_frontier_20261019/entrypoint_probe_v223_ui_activation_branch.json).

## Branch that prevents activation

The v223 call trace records 968 child calls from `0x0054bb20`, eight targets
121 times each. The selected caller's entry ECX is `0x27e315e8`; its helper
object is at `+4` (`0x27e315ec`). `0x00508ea0` and `0x00508e90` both return
`0x00000000` on all 121 calls. The short-circuit therefore never calls
`0x00508ec0`. Ghidra maps `0x00508e90` to a byte read at helper-object offset
`+0x2d`; the parent-object slot at `+0x31` is zero in the bounded probe.

The v225 trace shows `0x005093a0` entering with state `+0x28 == 1` and its
active flag at `+0x2c == 1`; it leaves readiness byte `+0x2d` at zero. Its child
at `0x27e31d68` moves to state 7. In v226, the child's `0x00508af0` readiness
method returns `0x2827bd00` (low byte zero) on all 120 calls, with child fields
`+0x218 == 2` and `+0x340 == 1`.

## Pending request provenance

The v228 exact-address trace identifies the last P-code store to child
`+0x218` (`0x27e31f80`): function `0x0066bb50` wrote the four-byte value 2 at
dispatch 64,488. It was called by `0x0066cc00` (return `0x0066cc3a`), whose
caller return address is `0x0065fafe`. Static decompilation places that call
in `0x0065fa60`, along the request path that later calls `0x00653480`.

## Request active state and cleanup guard

Caller traces v229–v239 show the synchronous setup path. In separate bounded
runs, `0x0065fa60` calls `0x00653140`, `0x00652190`, `0x0066cc00`, then
`0x00653480`; `0x0066cc00` returns `0x00010000` and `0x00653480` returns zero.
The latter calls `0x00635e40`, `0x0065f490` and `0x0066bab0`; that path returns
one and continues through `0x0048c777`, `0x0066bada`, `0x006880c0` and
`0x00650350`. These are completed direct-call observations, not proof that an
asynchronous worker completed the request.

The v237 target-wide call trace records one call to `0x0066bb50` from
`0x0066cc00` and no call to `0x0066b8d0` anywhere in the bounded guest call
stream. Static PE disassembly shows why these addresses must be interpreted
carefully: `0x0066cc00` calls `0x0066cb60` only if its owner byte `+0xb8` is
already nonzero; `0x0066cb60` checks that byte again before calling
`0x0066b8d0`. The latter clears bit 1 at request-object `+0xf8` (the observed
child `+0x218`) and is also reached from a separate cleanup wrapper. The
disassembly does not establish `0x0066b8d0` as the request's completion
callback.

The v238 caller trace observes owner `+0xb8 == 0` at entry to
`0x0066cc00`, last written by `0x0065fd90` through `0x0065ee60`. In v239,
`0x0066cc00` has set the byte to one by the time its parent makes the following
`0x00653480` call; exact-byte provenance names `0x0066cc00` as the writer. The
request is active after setup. The owner's initial zero explains why the
old-request cleanup branch is skipped on first setup, but it does not explain
the missing readiness transition. The pending child bit has no observed later
clear, and the worker/consumer path remains unresolved.

Across v229–v239, the probes remain at the same bounded host-frame-loop
checkpoint (v229 and v238 are two dispatches lower; the others report the
stable count), with 120 clear and present submissions, four waiting workers,
zero Vulkan validation errors, and no guest draw translation. The [machine
record](../evidence/retail_frontier_20261019/entrypoint_probe_v229_v239_async_request_calls.json)
contains per-run call events and hashes. Raw logs remain outside Git.

## Consumer check (v240)

The v240 target-receiver-slot trace confirms the exact readiness receiver and
the synchronous consumer branch without forcing UI state. `0x00653480` calls
`0x0066bab0` once; that method returns one after selected checks at
`0x006550f0`, `0x00655110` and `0x00655130` return `1`, `0` and `0`. The path
then calls `0x006880c0` and `0x00650350`. No call to `0x0066b8d0` occurs, so its
cleanup role remains the best-supported interpretation, not a completion
callback.

The readiness method `0x00508af0` is called 120 times from `0x00508970` on
receiver `0x27e31d68`; every sample has `+0x218 == 2`, `+0x340 == 1`, and a
return value with low byte zero. The bounded run still ends at 96,082
dispatches/1,559 unique functions with four waiting workers, no guest draw, and
zero Vulkan validation errors. The consumer branch runs, but it does not
produce the pending readiness transition. The [v240 machine record](../evidence/retail_frontier_20261019/entrypoint_probe_v240_consumer_target_slots.json)
contains the selected target calls, receiver-slot values, runtime/PE hashes,
and raw-log hash; full logs and retail files remain outside Git.

## Next step

Trace the downstream calls from `0x00650350` (`0x0064fef0`, `0x00650290`, and
`0x0064f530`) and identify which worker/consumer write is expected to clear the
pending child state. Keep the UI gate and readiness byte untouched; treat
`0x0066b8d0` as cleanup unless a call path establishes its completion role.
After the activation route is reached, continue toward the first guest draw
with its stream/index data, shader bindings and render target. The current
evidence proves neither retail frontend readiness nor a guest draw, race or
playable session.

# Retail UI activation frontier

Updated 2026-10-19. These bounded probes refine the UI activation blocker by
tracing original retail state transitions; they do not inject state or force
the gate.

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

## Worker queue and async-file guard (v249–v252)

The v249 downstream trace resolves the signal source. `0x00650350`, called by
`0x006880c0`, enters `0x0064fef0` and `0x00650290`, then calls
`0x0064f530`. That function successfully calls `SetEvent(0x60004)`. The
async-file worker thread `0x00010000` returns from its wait at dispatch 64640;
the event was consumed by the intended waiter.

The v250 worker-loop trace follows the wake into `0x006671b0`, the indirect
operation callback dispatcher. It returns status 4. The v251 callback trace
identifies operation 3 and target `0x00655ab0`, invoked on the same request
receiver `0x27ed9284` seen in the main-thread setup. Its `0x00655440` guard
returns a value whose low byte is zero, so the callback takes its status-4
defer/error path instead of updating readiness.

The v252 guard trace shows the failed operation: `0x00655440` calls
`KERNEL32.dll!CreateFileA` with desired access `0x80000000`, share mode 1 and
OPEN_EXISTING disposition 3. The path argument points at `0x28249b16`, but
`CreateFileA` returns `0xffffffff`; the following `0x006553b0` helper returns
4. The path bytes were not part of the v252 trace, so the evidence does not yet
distinguish a missing asset from a path-resolution or access problem. The
readiness samples remain `0x00508af0`: `+0x218 == 2`, `+0x340 == 1`, low-byte
return zero.

The v249–v252 probes use the same pinned retail PE and cumulative module set,
120 host frames, Vulkan validation, and synthetic mesh fixture. They remain at
the host-frame-loop checkpoint (96,080–96,082 dispatches, 1,559 unique
functions, zero validation errors, no guest draw translation). Raw logs remain
outside Git; hashes and selected events are in the [worker machine record](../evidence/retail_frontier_20261019/entrypoint_probe_v249_v252_async_file_frontier.json).

## Case-insensitive retail path and next blocker (v253–v254)

The v253 string-slot trace captures the worker's path argument exactly:
`C:\\pakfiles\\bootpersistent.bff`. The file exists in the installed PortProton
tree as `Pakfiles/BOOTPERSISTENT.bff`; the differing component case explains
the v252 `CreateFileA` failure on the case-sensitive host filesystem.

The generic guest path resolver now matches existing ASCII path components
without case sensitivity. It still canonicalizes resolved components and
rejects paths outside the configured game-data root. A native regression
fixture creates `CaseSensitiveFileFixture-*/Pakfiles/BOOTPERSISTENT.bff` and
opens it with lower-case guest components. The existing symlink deletion test
also passes, confirming `DeleteFileA` still operates on the final symlink.

The v254 retail run reaches `CreateFileA` successfully: the next `GetFileSize`
call uses handle `0x0005000c`, and the caller then consumes size
`0x00156c72`. Execution stops at dispatch 71,631 / 1,510 unique functions
because P-code function `0x005f1830` returns `-1`. No ReadFile call for this
resource is observed before the failure. This is a new frontier beyond the
case-sensitive path bug, not evidence of UI readiness or rendering. Raw logs
and the exact probe boundary are recorded in the [v253–v254 machine record](../evidence/retail_frontier_20261019/entrypoint_probe_v253_v254_casefold_file_lookup.json).

## Indirect tail-dispatch override and next blocker (v256–v257)

The v256 trace confirms that the third vtable slot at `0x00af01c0` contains
`0x0066cd60`, but the generated `0x005f1830` export rejects every external
branch target after checking its two internal PCs. It returns `-1` without
calling the runtime dispatcher. The NFS runtime frontier module now supplies
an address-specific override for the statically confirmed sequence
`mov eax,[ecx]; jmp [eax+8]`. A fixture verifies the EAX update, target call,
and original guest return address.

The v257 retail trace reaches `0x0066cd60`; its calls to `0x0066bbf0` and
`0x0066ccc0` complete, and the callback chain returns through `0x00652540` and
`0x00652d60` (`0x20110001`). The run advances to 71,640 dispatches and 1,517
unique functions, then stops because export `0x00652b13` is missing from
`0x00652af0`. The host-frame loop is not reached. The [machine record](../evidence/retail_frontier_20261019/entrypoint_probe_v256_v257_indirect_tail_frontier.json)
contains the probe hashes and selected return values.

## Async-file and P-code continuation (v258–v274)

The v258–v261 cumulative probes advance the startup request past the previously
missing virtual tail and request-handler exports. The runtime now handles the
observed `ReadFileEx` call using the supplied `OVERLAPPED` offset and dispatches
the queued completion routine on an alertable wait by the initiating worker.
Focused fixture coverage verifies callback arguments and the alertable-wait
result. The exact three-instruction dispatcher `0x005b0d50` selects the virtual
slot at `+0x48`, and Ghidra P-code for `0x0066cc70` preserves the request
arguments and its success/error state update.

The next request operation reaches the CRC32 worker loop at `0x0066caf0`.
Its byte lookup and stdcall epilogue are preserved from the Ghidra export; the
contiguous jump chain through `0x0041a946` is kept in one P-code body to avoid
deep nested dispatch on each byte. v261 completes that path and stops at
missing export `0x00509689`, called from `0x005095d4`, after 457,430 dispatches
and 1,727 unique functions. Its Ghidra-lowered body restores the saved frame
and conditionally updates the receiver byte. v262 executes that block and
advances to missing export `0x00509e60` called from `0x00637530`, at 463,504
dispatches and 1,735 unique functions. The one-instruction tail alias
`0x00509e60` now dispatches to the existing `0x00509e40` export without
changing guest state. v263 advances to missing export `0x0050967d` called from
`0x005093a0`, at 515,847 dispatches and 1,747 unique functions. Its exact
three-instruction block preserves `ECX`, calls `0x005089c0`, then dispatches to
the `0x0050958c` continuation. v264 reaches indirect target `0x27f30a50` from
`0x0040ba50`; v266's unresolved-call trace gives return address `0x0040bb04`,
placing the failing `CALL EAX` at `0x0040bb02`. v267 identifies slot
`0x27f30a90` as holding `0x27f30a50`, written by allocator `0x00427330`; the
target's first word is `0x0b`, so it is pool data and not executable code. The
earlier v265 writer at `0x27f30a8c` was the unrelated doubly linked-list `prev`
field.

The register trace shows `0x0054bb20` returning with `EDI` changed on the final
iteration. v269 isolates the nested `0x005093a0` call, and v270 shows
`0x005089c0` preserves `EDI` while continuation `0x0050958c` returns with
`EDI=0x27f30a98` and `EAX=3`. Ghidra's static flow shows that this continuation
belongs to `0x005093a0` and reaches a shared epilogue that restores the saved
registers. The separate P-code continuation returned before that epilogue.
The `0x0050967d` adapter now restores the active parent frame only when its
stack matches `ESP == EBP - 0x18`; the fixture verifies register, return-value,
and stack restoration. v271 then advances to missing export `0x005095f0` from
`0x00509551` at 516,250 dispatches / 1,751 unique functions.

The guarded `0x005095f0` state-3 adapter advances v272 to the initializer
`0x0054b560`, called from `0x005088e0`, at 516,254 dispatches / 1,752 unique
functions. Its Ghidra-lowered 20-instruction body completes the observed
helper sequence, preserves ESI, returns 7, and models the two `RET 4` helpers;
fixtures check the call order and stack cleanup.

v273 completes `0x0054b560` and stops at missing export `0x0085b0b0` from
`0x0040e630`, after 518,457 dispatches / 1,789 unique functions. Byte-level
disassembly of the pinned PE shows `MOV AL,[ECX+0x32f]; RET`. The narrow adapter
preserves the upper EAX bytes, reads that receiver field, and applies the guest
return. The v274 trace confirms EAX changes from `0x0085b0b0` to
`0x0085b000`, EDI remains unchanged, and the sampled byte is zero. The probe
advances to missing stateful export `0x0082f600` from `0x0040d910`, at 524,846
dispatches / 2,006 unique functions; its body and helper contracts are the
next recovery target.

Do not force the UI gate or readiness byte; preserve the retail state updates.
The [machine record](../evidence/retail_frontier_20261019/entrypoint_probe_v258_v274_pcode_worker_frontier.json)
stores run hashes, object provenance, register traces, and lowering evidence.

The run remains a bounded startup probe with the synthetic mesh fixture; it
does not reach the host-frame loop and proves neither frontend readiness, a
guest draw, a race nor a playable session.

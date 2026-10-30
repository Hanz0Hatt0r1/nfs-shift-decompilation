# Original-PE worker queue head/tail trace, v808

## Run identity

v808 ran the original Need for Speed SHIFT PC retail 1.02 PE32 x86 executable
in the Linux P-code guest runtime. It was not a recompiled-game or native
Windows/Wine run.

- Retail PE SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- Runtime SHA-256:
  `135c2452d882da91a249fb01acd9e5a3deedab42bde826097e43d9eb6aaff54e`
- Module manifest: `module-manifest-v659-005a0ef0.json`; SHA-256:
  `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`
- 120 host frames; `host-frame-loop`; 814,082 P-code dispatches; 3,934
  unique functions; zero Vulkan validation errors; two guest workers waiting
  at the final snapshot. Main-thread function snapshot: `0x00832160`.
- `guest_draw_translation=false`; `retail_rendering_proven=false`.
- Probe-log SHA-256:
  `bdc82a1b32e20b933e6b052bb7d22fd408b4837f2bdac82eb2f1323198b82b7e`
- Summary JSON SHA-256:
  `885a88e030674d159aa18c5c56478244f5a34362327a0cee6447ca82f5155637`

## Queue field meaning in the retail PE

Ghidra decompilation and the original PE bytes agree on these queue operations:

- `0x00650230` resets owner fields `+0xb4` and `+0xb8` to zero.
- `0x00650290` appends a task node. It stores the previous tail from `+0xb8`
  in the node, sets `+0xb4` to the new node if the queue had no tail, and then
  sets `+0xb8` to the new tail.
- `0x00650350` enters the append path only when owner flag bit 0 is set. After
  enqueueing, it calls the event wrapper for `owner+0x40` only when flag bit 3
  (`0x8`) is set.
- `0x0064fe50` checks flag bit 3 and routes through the wait wrapper using
  `owner+0x40`.

Thus `+0xb4/+0xb8` are the queue head and tail, rather than unclassified
auxiliary fields.

## Runtime observation

At dispatch 412,840, worker `0x00010002` entered `0x0064fe50` with owner
`0x27f7cd00`. The trace sampled event `+0x40=0x60018`, head `+0xb4=0`, tail
`+0xb8=0`, and flags `+0xc0=0xf`. The worker then entered its
`WaitForSingleObjectEx(0x60018, INFINITE, TRUE)` path. At that point the queue
was empty, while the event-wait flag was enabled.

During the 120-frame run, the selected `0x00650350` calls enqueued work only
for owners `0x27f7c290` and `0x27f7c780` (events `0x6000c` and `0x60010`). No
selected enqueue used owner `0x27f7cd00`. The earlier v807 600-frame trace
likewise retained no enqueue for that owner and no `SetEvent(0x60018)`.

## Conclusion and limits

The evidence supports an ordinary idle wait: the queue had no task at the
observed wait entry, so the absence of a matching event signal is not evidence
that the runtime lost a wake. No runtime behavior or guest state was changed.
The selected traces do not rule out a different producer path outside the
selected function set, and they do not prove why this worker was created or
whether another lifecycle phase should later enqueue work. They establish no
visible frontend, guest draw translation, or race entry.

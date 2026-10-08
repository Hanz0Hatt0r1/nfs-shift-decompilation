# Process 1 — FUN_006333f0 Controller #1 layout exclusion

This slice closes the final **source-visible generic queue-pointer alias** remaining after the `FUN_006880c0` request-object proof.

## PC retail object layout

Controller #1 owns the queue previously joined as `ThreadState+0x5c` and `Controller+0x08`. In the exact PC retail 1.02 source, `FUN_00649cb0` allocates that queue with `FUN_008868c0(0xe0)`, constructs it through `FUN_0064fe70`, stores the exact returned pointer at `ThreadState+0x5c`, then passes the same pointer to `FUN_00655000`. `FUN_00655000` stores its queue argument at `Controller+0x08`.

Therefore the recovered Controller #1 queue object is a standalone allocation of `0xE0` bytes.

## FUN_006333f0 required layout

`FUN_006333f0` begins its dispatch decision by reading `*(byte *)(param_1 + 0x250)`. Its fallback path then calls the common enqueue primitive `FUN_00650350(param_1, ...)`.

A field at `+0x250` cannot belong to the standalone `0xE0` Controller #1 queue allocation. Consequently the `param_1` object accepted by `FUN_006333f0` is structurally not the recovered Controller #1 queue object.

This removes `FUN_006333f0` from the Controller #1 alias frontier and, together with the already merged `FUN_006880c0` request-object proof, closes the source-visible generic `FUN_00650350` queue-pointer alias surface.

## Fail-closed boundary

This does **not** prove that Controller #1 has no indirect or native APC wake path. Dynamically populated function pointers, OS/native APC injection, and any render/presentation phase-lock relationship remain separate unresolved questions.

Xbox 360 recomp files are available on Drive but are not required for this positive claim; the promoted layout exclusion is PC-backed.

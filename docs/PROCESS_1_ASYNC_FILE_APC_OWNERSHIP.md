# Process 1 — async-file APC ownership is separate from Controller #1

This slice continues from:

```text
SHIFT.Process1Controller1MessageQueueWake/1
```

That contract left one concrete alertable-completion question open: the PC retail
binary contains `ReadFileEx` and `WriteFileEx` with completion routines, but their
thread ownership had not been joined to or separated from `Controller #1`.

The PC retail 1.02 executable now closes that specific boundary. The known
`ReadFileEx` / `WriteFileEx` completion surface belongs to a separate worker
named **`Base File: Async Thread`**, not to the Controller #1 worker
`FUN_00662880`.

This is deliberately narrower than claiming that Controller #1 can never receive
an APC from any source.

## 1. The async-file object has its own named worker thread

The PC executable contains the exact string:

```text
Base File: Async Thread
```

at `0x00aeff74`.

The start wrapper at `0x0065f0a0` passes that name and the async-file object to
the generic thread creator `0x00649cb0`.

The object vtable begins at `0x00af386c`. Its virtual slot `+0x4` is
`0x00667240`. The generic thread trampoline reaches that slot through a virtual
call, so the object worker is:

```text
Base File: Async Thread
  -> generic thread trampoline
  -> vtable +0x4
  -> 0x00667240
```

The absolute pointer to `0x00667240` occurs in the vtable at `0x00af3870`; there
is no direct call occurrence that would collapse this ownership into the
Controller #1 loop.

Controller #1 remains the independently proven worker `FUN_00662880`.

## 2. The async-file worker owns the operation dispatch table

Worker `0x00667240` reads operation codes and selects handlers from the table at
`0x00b890f0`.

The five recovered entries are:

```text
operation 2 -> 0x00655ab0
operation 3 -> 0x00655ab0
operation 4 -> 0x00655c80
operation 6 -> 0x00655c80
operation 5 -> 0x00655c80
```

The selected function pointer is passed to helper `0x006671b0`, which performs
the indirect method call.

A raw PC-image pointer scan finds `0x00655ab0` only in two table slots and
`0x00655c80` only in three table slots. No direct `call`/`jmp` occurrences to
those handlers were found.

Therefore the recovered static path is:

```text
0x00667240 async-file worker
  -> 0x00b890f0 operation table
  -> 0x006671b0 indirect dispatch helper
  -> 0x00655ab0 / 0x00655c80
```

## 3. All direct PC ReadFileEx / WriteFileEx callsites are in that surface

The PC retail IAT entries are:

```text
ReadFileEx  -> 0x00aa6240
WriteFileEx -> 0x00aa6234
```

A direct `FF 15 <IAT>` scan of the executable finds exactly:

```text
ReadFileEx:
  0x006558d5
  0x00655c15

WriteFileEx:
  0x006559df
  0x00655dca
```

Those callsites pass the completion routines:

```text
read completion  -> 0x006553e0
write completion -> 0x00655410
```

and sit inside the async-file operation handlers reached by the operation table
above.

For this identified PC surface, there is no recovered path through
`FUN_00662880`.

## 4. The async-file worker has its own alertable SleepEx venue

The async-file worker calls the wrapper at `0x00649780` with the alertable flag
set to true. The wrapper reaches the PC `SleepEx` IAT entry at `0x00aa6274`.

So the same subsystem that issues the asynchronous file operations also has its
own recovered alertable wait path:

```text
Base File: Async Thread
  -> async operation dispatch
  -> ReadFileEx / WriteFileEx
  -> ...
  -> SleepEx(..., TRUE)
```

This is the correct static ownership venue for the known file completion
routines. It is distinct from Controller #1's independently recovered
`SleepEx(10, TRUE)` loop.

## 5. Process 1 adjudication

This slice proves:

- all direct PC-retail `ReadFileEx` callsites are accounted for;
- all direct PC-retail `WriteFileEx` callsites are accounted for;
- those callsites are reached through the async-file operation-dispatch surface;
- that surface is owned by the named `Base File: Async Thread`;
- the async-file worker is distinct from Controller #1;
- therefore the identified file-completion APC surface is **not** promoted as a
  Controller #1 wake source.

This slice does **not** prove:

- that no other indirect or library-owned APC mechanism can reach Controller #1;
- that Controller #1 can never return early from `SleepEx(10, TRUE)`;
- that rendering or presentation is phase-locked to Controller #1.

The message-queue conclusion is unchanged: Controller #1 polls its queue and
does not wait on the queue Event.

## Machine-locked PC spans

`evidence/process1_async_file_apc_ownership.json` pins SHA-256 for:

- the named async-thread start wrapper;
- the generic virtual worker dispatch;
- the thread-name bytes;
- the async-file vtable head;
- the operation-dispatch table;
- the indirect dispatch helper;
- worker dispatch plus alertable sleep;
- all four direct `ReadFileEx`/`WriteFileEx` callsite spans;
- both completion routines;
- the `SleepEx` wrapper.

The evidence is based on the exact PC retail 1.02 `SHIFT.exe` already used by
the project. The Xbox recomp was available for navigation, but is not required
for any promotion in this contract.

## Next Process 1 blocker

The known async-file completion surface is now separated from Controller #1.

The next useful search is narrower:

1. enumerate remaining APC-capable or alertable-completion mechanisms outside
   the Base File async worker and test whether any are owned by Controller #1;
2. trace D3D9/render/presentation producers toward `FUN_00662ee0` or another
   Controller #1-owned wake source;
3. keep render-frame phase-lock fail-closed until one such producer join is
   machine-backed.

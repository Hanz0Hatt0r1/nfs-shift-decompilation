# Process 1B — HDVehicle+0x4330 `_bsearch` callback closure

## Result

PC retail 1.02 contains exactly two direct `CALL rel32` sites whose target is `_bsearch` thunk `0x0090421d`:

```text
0x0053c2da
0x00a5df75
```

Both comparator entrypoints are fixed by retail machine code, and neither is one of the 15 canonical Process 1B `HDVehicle+0x4330` carriers.

## Weird decompiler site — `0x0053c2da`

The Ghidra C export renders the comparator as `unaff_retaddr`. The retail bytes show why that is misleading.

`FUN_0053c2c0` establishes EBP, then tail-jumps into a tiny thunk:

```text
0x0053c2c0  push ebp
0x0053c2c1  mov  ebp,esp
...
0x0053c2cd  jmp  0x00429e86
```

The thunk explicitly pre-pushes the comparator:

```text
0x00429e86  push 0x0053c280
0x00429e8b  jmp  0x00429e98
0x00429e98  jmp  0x0053c2d2
```

The shared body then pushes the other four cdecl arguments and calls `_bsearch`:

```text
0x0053c2d2  push 4
0x0053c2d4  push eax
0x0053c2d5  push ecx
0x0053c2d6  lea  eax,[ebp+8]
0x0053c2d9  push eax
0x0053c2da  call 0x0090421d
```

Thus the fifth argument is exactly comparator `0x0053c280`. `unaff_retaddr` is a decompiler/calling-convention artifact, not runtime comparator provenance.

## Fixed comparator site — `0x00a5df75`

The second site is conventional:

```text
0x00a5df62  push 0x00a5df20
...
0x00a5df75  call 0x0090421d
```

Comparator `0x00a5df20` loads one unsigned 16-bit value from each argument and returns their subtraction.

## Carrier intersection

```text
comparators = {0x0053c280, 0x00a5df20}
canonical P1B HDVehicle+0x4330 carriers = 15
intersection = empty
```

Therefore the bounded `_bsearch` callback surface has zero exact P1B carrier hits.

## Scope

This closes `_bsearch` only. Other callback families, generic function-pointer stores/copies, runtime-generated/copied/encoded pointers, noncanonical code-address synthesis and opaque indirect dispatch remain fail-closed.

The manager `+0x374 -> HDVehicle+0x4330` join, `0x004b86cf`, P1.3 completion and provider removal are unchanged. Provider count remains 7.

# Process 1 — reject the `FUN_00469ab0` manager+0x2a0 candidate

## Result

The previously interesting mutation edge

```text
0x00469b17  lea ECX,[ESI+0x2a0]
0x00469b1d  call FUN_0057f620
```

does **not** mutate `FUN_00489ad0()` singleton `manager+0x2a0` on the proven caller path.

The exact PC-retail receiver at the call into `FUN_00469ab0` is the distinct global singleton at `0x00bbdbe0`.

No class/physical/control semantic name is assigned to that object.

## Why the new Ghidra index mattered

The SQLite index resolves `0x00469ab0` to `FUN_00469ab0` (`__thiscall`, 85 bytes) and shows no direct callgraph caller. The vtable candidate export also contains no slot targeting it.

That does **not** prove the function is unreachable: the retail binary reaches it through a jump thunk. The index therefore narrowed the search, and exact machine code closed the receiver identity.

## Exact chain

The enclosing retail path first reads the real manager collection:

```text
0x004b6229  call FUN_00489ad0
0x004b622e  cmp ESI,[EAX+0x2c4]
0x004b623a  lea ECX,[EAX+0x2a0]
0x004b6242  call FUN_0054ed00
```

Here `EAX` is the proven `0x00bc9fc0` manager singleton.

Later in the same path, however, the mutator receiver is obtained from a different getter:

```text
0x004b62f2  push 1
0x004b62f4  call 0x004042b0
0x004b62f9  mov ECX,EAX
0x004b62fb  call 0x004b5dc0
```

The getter thunk resolves to:

```text
0x004042b0  jmp 0x0043b920
0x0043b920  jmp 0x0043b932
...
0x0043b945  mov ECX,0x00bbdbe0
0x0043b94b  call FUN_005801e0
...
0x0043b97b  mov EAX,0x00bbdbe0
0x0043b980  ret
```

So `0x004b62f9` loads `ECX=0x00bbdbe0`.

The second thunk then reaches the candidate body:

```text
0x004b5dc0  jmp FUN_00469ab0
```

and `FUN_00469ab0` preserves that receiver in `ESI`:

```text
0x00469abc  mov ESI,ECX
...
0x00469b17  lea ECX,[ESI+0x2a0]
0x00469b1d  call FUN_0057f620
```

Therefore the mutated collection is:

```text
0x00bbdbe0 + 0x2a0
```

not:

```text
0x00bc9fc0 + 0x2a0   # FUN_00489ad0 manager singleton
```

The identical `+0x2a0` offset is not object identity.

## Adjudication

Closed:

- `0x00469b1d -> FUN_0057f620` is rejected as a `manager+0x2a0` mutator;
- the exact candidate receiver is `0x00bbdbe0` on the proven path;
- the enclosing function's earlier access to real `manager+0x2a0` does not transfer that identity to the later receiver.

Still open:

- insertion/registration provenance for the real `FUN_00489ad0()+0x2a0` collection;
- `manager+0x374 == HDVehicle+0x4330`;
- selected non-sentinel `HDVehicle+0x64e8` provenance;
- retail input/control producer closure.

Provider count remains **7**.

## Next target

Do not spend more Process 1 time expanding `FUN_0057f620` for manager ownership. Instead, trace the exact path around `0x0045daa3` where an entry from the real `manager+0x2a0` collection is selected and stored to `manager+0x378`. That sibling-slot join may expose the registration/selection ownership needed to understand `manager+0x374` and the remaining `HDVehicle+0x64e8` branch.

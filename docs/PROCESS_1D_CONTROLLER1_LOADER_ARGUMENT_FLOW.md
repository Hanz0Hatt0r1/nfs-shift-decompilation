# Process 1D — Controller #1 loader argument flow

## Result

The merged loader-reachability frontier identified exactly seven direct `GetModuleHandleA` / `LoadLibraryA` calls reachable through the recovered Controller #1 direct callgraph. This stage proves their actual loader arguments from authoritative PC retail 1.02 machine bytes.

```text
0x00907490  GetModuleHandleA("mscoree.dll")
0x0090a9e3  GetModuleHandleA(NULL)
0x0090aa60  GetModuleHandleA("KERNEL32.DLL")
0x0090aad7  GetModuleHandleA("KERNEL32.DLL")
0x0090abc9  GetModuleHandleA("KERNEL32.DLL")
0x00918a16  GetModuleHandleA("kernel32.dll")
0x0091c0a0  LoadLibraryA("USER32.DLL")
```

All literal strings and callsite setup instructions are hash-locked against retail `SHIFT.exe` SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

## Current-module PE walk

`FUN_0090a9bb` is the one direct loader caller without a literal module name:

```text
0x0090a9c8  xor ebx,ebx
...
0x0090a9e2  push ebx
0x0090a9e3  GetModuleHandleA(NULL)
```

It then parses the current module's PE headers:

```text
0x0090a9e9  read e_lfanew at +0x3c
0x0090a9ee  read section count at +0x6
0x0090a9f2  read optional-header size at +0x14
0x0090a9f6  materialize first section header
0x0090a9fd  compare against ".mixcrt"
0x0090aa12  advance section cursor by 0x28
```

There is no export-directory `+0x78` access in this function. Its recovered role is a current-module section-table lookup, not PE export-directory API resolution.

## Relation to direct GetProcAddress proof

The separate merged Controller #1 GetProcAddress argument-flow proof already pins all eleven worker-reachable direct resolver target names as non-APC. The loader proof now removes the remaining contextual ambiguity on which direct modules those resolver/runtime paths load or query.

## Gate

```text
all worker-reachable direct loader arguments proven = true
direct literal/NULL loader surface complete          = true
current-module .mixcrt walk is export resolver       = false
direct loader argument surface supports APC path     = false

indirect loader calls ruled out                      = false
generated/nonliteral module names ruled out          = false
manual export walking overall ruled out              = false
native/syscall APC injection ruled out               = false
Controller #1 target-thread join complete            = false
Controller #1 timing exhaustive                      = false
P1.3D complete                                       = false
provider count                                       = 7
```

## Reproduction

```bash
python3 tools/ghidra/verify_p1d_controller1_loader_argument_flow.py \
  /path/to/SHIFT.exe \
  --output out/p1d_controller1_loader_argument_flow.json
```

The verifier reads only the retail PE, validates the executable hash, exact machine byte windows and literal strings.

## Next step

Continue indirect/manual/native resolution paths and Controller #1 target-thread identity. The direct loader plus direct named `GetProcAddress` route is now exact and negative for APC injection.

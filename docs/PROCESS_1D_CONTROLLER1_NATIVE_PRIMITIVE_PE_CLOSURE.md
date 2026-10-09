# Process 1D — Controller #1 native/manual primitive PE closure

## Scope

PR #1699 introduced two narrow APC-adjacent machine primitive families:

- manual export-walk candidates requiring exact x86 `FS:[0x30]` PEB access plus PE `e_lfanew` (`+0x3c`) and export-directory (`+0x78`) hints;
- direct native transitions using `SYSENTER` or `INT 0x2e`.

This stage executes that surface directly on authoritative PC retail 1.02 `SHIFT.exe`.

## Authority and function-body correction

```text
SHIFT.exe SHA-256
  eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1

shift_ghidra.sqlite SHA-256
  ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e
```

Machine disassembly is semantic authority. Ghidra function entries are navigation only.

The SQLite `functions.raw_json.size` is **not** treated as a contiguous `[entry, entry+size)` body. Retail machine flow proves that `FUN_00420770` branches from `0x0042081f` / `0x0042084a` into the later chunk at `0x004209bc`, so a contiguous-size ownership assumption would be invalid.

## Whole-PE result

```text
Ghidra function entries                    41538
raw FS-segment instruction decodes          3458
exact FS:[0x30] / fs:0x30 decodes              0
exact #1699 PEB heuristic candidates            0

raw SYSENTER decodes                            1
raw INT 0x2e decodes                            0
```

Because the whole disassembly contains zero exact `FS:[0x30]` instructions, the exact #1699 `FS:[0x30] + 0x3c + 0x78` heuristic closes negative without needing any function-body ownership assumption.

## The lone SYSENTER decode

The only raw site is:

```text
0x004209bf  ret 0x4
0x004209c2  int3
0x004209c3  int3
0x004209c4  int3
0x004209c5  int3
0x004209c6  int3
0x004209c7  int3
0x004209c8  sysenter
```

Static whole-PE checks find:

```text
direct branch/call references to 0x004209c8  0
absolute 32-bit pointer occurrences             0
Ghidra function entry at 0x004209c8             no
nearest prior function entry                    FUN_00420770 @ 0x00420770
nearest next function entry                     FUN_004209d0 @ 0x004209d0
```

Therefore the **direct statically addressed** SYSENTER/INT 0x2e surface closes negative. This does not prove that computed or indirect control flow can never enter `0x004209c8`.

## Fail-closed boundary

Closed negative:

```text
exact FS:[0x30] + PE-export-offset heuristic = true
direct statically addressed SYSENTER/INT2e   = true
```

Still open:

```text
computed/indirect entry to 0x004209c8           = open
alternate PEB/module discovery                  = open
indirect native stubs/function pointers         = open
generated/WOW64 transitions                     = open
manual export walking overall                   = open
native/syscall APC injection overall            = open
Controller #1 target-thread join                = open
Controller #1 timing exhaustive                 = false
P1.3D complete                                  = false
provider count                                  = 7
```

An absence from this exact primitive surface is not a universal no-APC theorem.

## Reproduction

```bash
python3 tools/ghidra/analyze_p1d_controller1_native_primitive_pe.py \
  /path/to/SHIFT.exe \
  /path/to/shift_ghidra.sqlite \
  --output out/p1d_controller1_native_primitive_pe_closure.json
```

The tool verifies the retail PE hash, streams GNU `objdump` twice (primitive inventory, then direct incoming flow references), checks literal pointer occurrences in the PE, and never infers a contiguous Ghidra function body from the SQLite size summary.

## Next step

Bound computed/indirect reachability to `0x004209c8`, then continue indirect/native-stub and Controller #1 target-thread provenance. No timing gate may advance until an exact APC-capable API/service identity is joined to the Controller #1 worker/thread handle.

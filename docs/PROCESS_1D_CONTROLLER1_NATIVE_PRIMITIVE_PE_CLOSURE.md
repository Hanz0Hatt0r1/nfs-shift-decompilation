# Process 1D — Controller #1 native/manual primitive PE closure

## Scope

PR #1699 introduced a Ghidra inventory for two narrow APC-adjacent machine primitive families:

- manual export-walk candidates requiring exact x86 `FS:[0x30]` PEB access plus PE `e_lfanew` (`+0x3c`) and export-directory (`+0x78`) hints in the same function;
- direct native transitions using `SYSENTER` or `INT 0x2e`.

This stage reproduces that bounded surface directly from the authoritative PC retail 1.02 `SHIFT.exe` and joins instruction ownership to the current Drive Ghidra SQLite function intervals.

## Authoritative inputs

```text
SHIFT.exe SHA-256
  eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1

shift_ghidra.sqlite SHA-256
  ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e

SQLite format
  SHIFT.GhidraSQLiteIndex/1
```

Machine disassembly is semantic authority. The SQLite function index is used only to decide whether a decoded instruction belongs to an indexed retail function.

## Result

Across 41,538 indexed functions:

```text
raw FS-segment instruction decodes         3458
FS decodes owned by indexed functions      3395
exact FS:[0x30] / fs:0x30 decodes             0
manual-export heuristic candidates             0

raw SYSENTER decodes                           1
SYSENTER inside indexed functions              0
raw INT 0x2e decodes                           0
INT 0x2e inside indexed functions              0
```

The owned FS forms are only the expected TIB/SEH-family offsets:

```text
fs:0x0       and register-write variants
fs:0x10
fs:0x18
```

No exact `FS:[0x30]` PEB access exists in the disassembled retail surface, therefore the exact #1699 `FS:[0x30] + 0x3c + 0x78` manual-export heuristic has zero candidates.

## The lone raw SYSENTER decode

The only raw `SYSENTER` decode is:

```text
0x004209c8  sysenter
```

It is not owned by any indexed Ghidra function. The nearest function boundaries are:

```text
previous: FUN_00420770  start 0x00420770  end 0x0042089e
next:     FUN_004209d0  start 0x004209d0
```

Therefore this byte sequence is **not promoted** to an executable Controller #1 APC path. It remains an explicit unowned-byte frontier until exact control-flow ownership proves or rejects execution.

## Fail-closed boundary

This closes only two narrow sub-surfaces:

```text
exact FS:[0x30] + PE-export-offset heuristic = closed negative
defined-function SYSENTER / INT 0x2e          = closed negative
```

The following remain open:

```text
unowned 0x004209c8 control-flow ownership      = open
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

An absence from the exact primitive heuristic is not a universal no-APC theorem.

## Reproduction

```bash
python3 tools/ghidra/analyze_p1d_controller1_native_primitive_pe.py \
  /path/to/SHIFT.exe \
  /path/to/shift_ghidra.sqlite \
  --output out/p1d_controller1_native_primitive_pe_closure.json
```

The tool requires GNU `objdump`, verifies the retail executable hash, streams disassembly, and maps only relevant primitive instructions back to indexed function intervals.

## Next step

Adjudicate control-flow ownership of raw `0x004209c8`. Then continue indirect/native-stub and Controller #1 target-thread provenance. No timing gate may advance until an exact APC-capable API/service identity is joined to the Controller #1 worker/thread handle.

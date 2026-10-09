# Process 1D — Controller #1 direct resolver reachability

## Result

Using the pinned Ghidra SQLite callgraph, the recovered Controller #1 worker `FUN_00662880` reaches only **6** of the **18** functions that directly call `GetProcAddress`.

Those six functions account for **11** of the binary's **100** direct `GetProcAddress` calls:

```text
0x0090748b  distance 9  calls 1
0x0090aa27  distance 6  calls 1
0x0090aa9e  distance 6  calls 1
0x0090abb8  distance 7  calls 2
0x009189cd  distance 8  calls 1
0x0091c073  distance 9  calls 5
```

Their local string context is CLR/CRT/KERNEL32/USER32 oriented: `CorExitProcess`, `EncodePointer`, `DecodePointer`, `InitializeCriticalSectionAndSpinCount`, `GetUserObjectInformationA`, `GetLastActivePopup`, `GetActiveWindow`, and `MessageBoxA`. No plain APC target name appears in this worker-reachable resolver subset.

## Boundary

This is a **direct-callgraph** closure only. It does not prove that the contained strings are exact `GetProcAddress` arguments, nor can it rule out:

- indirect calls or function pointers;
- callbacks or virtual dispatch;
- hashed/generated API names;
- manual export walking;
- native/syscall APC injection.

Therefore the Controller #1 timing gate remains fail-closed.

```text
direct worker-reachable resolver callers = 6 / 18
direct worker-reachable GPA calls         = 11 / 100
plain APC name evidence in that subset    = false
Controller #1 timing exhaustive           = false
P1.3D complete                            = false
provider count                            = 7
```

## Next step

Join the native/manual primitive inventory to exact local machine flow and Controller #1 target-thread identity. Only then can the remaining indirect/native APC timing surface be closed.

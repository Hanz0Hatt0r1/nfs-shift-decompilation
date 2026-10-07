# Phase 738 scope

In scope:

- discover every direct PC-retail caller/callsite of `FUN_007618f0` from the standard Ghidra callgraph export;
- generate a finite targeted instruction-export worklist;
- recover the physical explicit stack argument at each direct callsite;
- reuse the existing all-path IA-32 register provenance engine for register PUSH operands;
- fail closed when the argument is not an immediate pre-call PUSH or its physical origin is ambiguous;
- preserve the distinction between physical argument provenance and semantic object ownership.

Out of scope:

- assigning a class, resource, suspension, wheel, or configuration semantic name to the second source object from offsets `+0x338/+0x918` alone;
- claiming a positive retail owner before the generated retail report exists;
- wiring incomplete second-source ownership into the selected runtime session;
- changing Phase737/728/727 arithmetic or reducing the seven-provider frontier without a positive owner join.

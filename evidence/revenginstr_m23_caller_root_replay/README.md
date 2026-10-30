# M2.3 caller argument root replay

This replay pins a writable Ghidra `Decompiler Parameter ID` preparation copy
and then exports caller argument subtrees read-only. Three exact call edges
were examined; all three caller decompilations completed.

| Plan | Caller → callee | Result |
| --- | --- | --- |
| `direct-intermediate` | `008868c0` → `006382b0`, site `008868c9` | Exact parameter 0 root, byte offset `0x0`; present in both `ParameterRoot/1` and `/2`. |
| `looped-offset` | `006382b0` → `00638020`, site `006382e9` | No exact formal root. The argument is a `MULTIEQUAL` of two cast call results (`006382b8` and `006382db`). |
| `stack-derived-outer` | `00806ef0` → `008868c0`, site `00806f1a` | No exact formal root; the bounded subtree remains stack-derived. |

The `looped-offset` plan name was retained from the requested probe. This
consumer result is a call-result PHI abstention; it does not demonstrate a
loop-carried PHI whose inputs have different offsets. The RevEngInstr synthetic
regression separately guards against publishing one exact root when
`MULTIEQUAL` alternatives change offsets. `00638020` also contains a `PTRADD`
with `+0x12c`, but this replay does not establish a value-flow connection from
that use to the call argument or prove a `0x13a * 4` update.

## Writable preparation and project pin

`Parameter ID` ran twice in callee-before-caller order on a controlled writable
copy. Pass one changed only `00806ef0`'s return type from `undefined4 *` to
`void *`; pass two made no further change. Both passes completed for the five
selected functions. Subsequent subtree and flow extraction used that copy
read-only with analysis disabled.

The manifest pins the source project snapshot and the resulting writable-copy
tree. The tree digest covers `shift.gpr` and every entry beneath `shift.rep`,
sorted by relative path; it hashes a `D`/`F` entry marker, relative path, file
size, and file bytes. Ghidra was `12.1.2-DEV`; the Parameter ID runs used Java
`26.0.2.1`. No binary or Ghidra project database is committed here.

## Evidence and limits

The raw bounded plan, both caller flows, subtree rows, and `/1` and `/2` root
sidecars are included and hash-pinned in `manifest.json`. There is one exact
positive root and two explicit abstentions. The replay reports static P-code
provenance only; it does not establish runtime behavior or object semantics.

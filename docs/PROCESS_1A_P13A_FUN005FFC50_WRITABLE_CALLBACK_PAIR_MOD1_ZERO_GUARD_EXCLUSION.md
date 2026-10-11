# Process 1A / P1.3A — modulus-1 zero-guard exclusion

This subset follows the local induction passes and closes one more target-compatible site by combining the already-proven secondary singleton with exact retail branch feasibility.

PC retail 1.02 proves:

- upstream classifies `0x005d5621` as `cmp BYTE PTR [esi+ebp*1],0x0` with secondary singleton `EBP=0x00aa9b60`;
- `0x005d5603` materializes that same singleton on the local null-argument path;
- `0x005d560c` checks `BYTE PTR [ebp+0x0]` and `0x005d5614` jumps to `0x005d562b` when it is zero;
- the retail `.rdata` byte at `0x00aa9b60` is exactly `0x00`;
- therefore the singleton path necessarily takes the guard and skips `0x005d5621`.

The target-compatible frontier is reduced from seven to six sites: `0x00503328`, `0x0050334b`, `0x007a6e9e`, `0x007a6ea5`, `0x007f25a0`, and `0x0080b696`.

This is an exact branch-feasibility proof for one retail site. It does not infer a general string bound, does not close runtime/missing-secondary aliases, and does not promote aggregate callback, slot0/slot1, or P1.3 gates.

Next: trace the runtime count provenance feeding `ESI` at `0x00503328/0x0050334b`, then classify the four remaining modulo-4/8 sites.

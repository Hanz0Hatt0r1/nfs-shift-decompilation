# Process 3 — independent P1 iterator frontier audit (2026-10-21)

**Question:** What is actually established about retail `FUN_007f1eb0` and its apparent consumer `FUN_00675a90`, and what is the minimum non-invasive runtime evidence needed to identify the guest branch before any D3D9 `Draw*` call?

**Scope/provenance:** independent read-only static assessment using only the exact Ghidra decompilation and metadata supplied in the request and read-only GitHub source/evidence. No original PE, local Ghidra project, local v668 log, or filesystem accessed. The cited Ghidra export `process1-ui-worker-path-30000-20261021.jsonl` reportedly completed with exit 0, contains 30,000 functions and both named functions; this is **user-supplied export provenance, not a file independently inspected on GitHub**. No game class name, purpose or memory allocation is inferred from raw addresses.

**Target:** original PC retail 1.02 `SHIFT.exe`, PE32 x86, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

## 1. Determination: `FUN_007f1eb0` is iterator-like, not a named iterator contract

The provided full Ghidra C has the following control skeleton (comments are analytical, not reconstructed source):

```c
uVar2 = (*param_2 == 0) ? 0 : param_2[2] + 1;
if (uVar2 < *(uint *)(param_1 + 0x20)) {
    base = *(int *)(param_1 + 0xe0);
    // scan entries at base + 16*index, flag at entry+12
    do {
        if ((*(byte *)(base + uVar2*16 + 0xc) & 1) != 0) {
            param_2[1] = *(int *)(base + uVar2*16 + 4);
            param_2[0] = base + uVar2*16 + 8; // address, not the pointed-to value
            param_2[2] = uVar2;
            iVar1 = *(int *)(base + uVar2*16);
            param_2[3] = iVar1;
            return (iVar1 & 0xffffff00u) | 1u;
        }
        ++uVar2;
    } while (uVar2 < *(uint *)(param_1 + 0x20));
}
return uVar2 & 0xffffff00u;
```

**Confirmed by the supplied decompilation, conditional on ordinary valid pointers/metadata:**
- `param_1+0x20`: a `uint32_t` comparison bound for candidate indices (not proof of allocation capacity or an object's total element count).
- `param_1+0xe0`: a 32-bit value used as base for a sequence of **16-byte-spaced** entries, not proof of a particular class or ownership.
- The entry at `base+16*i` is tested at byte offset `+0x0c`, mask `0x01`. The code skips entries without the bit and chooses the next matching entry.
- With `param_2[0]==0`, starts from index 0; otherwise resumes from `param_2[2]+1`. The four DWORD output slots written on success are `[0]=base+16*i+8` (address within entry), `[1]=DWORD(entry+4)`, `[2]=i`, `[3]=DWORD(entry+0)`. The referenced C does not write these output slots on exhaustion.
- **Success return:** `(DWORD(entry+0)&0xffffff00)|1`. **Exhausted/no match:** `i&0xffffff00`. Therefore **AL** is guaranteed `1` on success, `0` on exhaustion, but **full `EAX` is not an ordinary boolean**; nonzero `EAX` may also denote exhaustion. A caller using `AL` or a converted `char` is compatible with the observed control contract. Upper 24 bits are not proven to be semantically useful to these callers.
- `FUN_007f2030` resets a count and repeatedly calls `FUN_007f1eb0` until its **char** result is zero, incrementing once per successful call. This independently supports an enumeration/scanning interpretation.

**Limits:** source `__fastcall`/parameter names are Ghidra inferences; confirm actual x86 calling convention, registers and stack slots using instruction-level caller evidence. No established record type, field names, container name, menu/vehicle/world affiliation, lifetime, lock/synchronization, or allocation bounds. For extreme/corrupt metadata the shown C does not itself prove overflow-proof index increment, `index*16`, pointer arithmetic or memory accesses. The reported end boundary (next named function `0x007f2030`) is **not proof** that every byte in `0x007f1eb0..0x007f202f` is contiguous or owned exclusively by this entry.

**Corroborating GitHub evidence:** an earlier v621–v659 P-code evidence JSON contains **one completed return** for target `0x007f1eb0` at dispatch/completion `39431691` with `EAX=0x00000000`. This demonstrates only one run-specific result, not a complete distribution or a v668 call path. [v621–v659 evidence](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/evidence/retail_frontier_20261021/process1_pcode_frontier_v621_v659.json).

## 2. `FUN_00675a90`: partial branch behavior, no class semantics

The supplied decompilation begins from **unresolved incoming `in_AL`, `in_ZF` and `unaff_EBP`**, not validated formal arguments:

```c
if (in_ZF) {
    while (in_AL != 0) {
        FUN_00671670(*(undefined4 *)(unaff_EBP + 8));
        in_AL = FUN_007f1eb0();
    }
} else if (in_AL != 0) {
    do {
        if ((*(byte *)(**(int **)(unaff_EBP - 0x10) + 0x28) & 4) == 0)
            FUN_00671580();
        else
            FUN_00671670(*(undefined4 *)(unaff_EBP + 8));
        cVar1 = FUN_007f1eb0();
    } while (cVar1 != 0);
    return;
}
```

**Exactly established in this decompiler representation:** there is a conditional split based on incoming ZF; both paths require a nonzero incoming AL to enter iteration; on the ZF path it calls `0x00671670` with a value from `[EBP+8]` before each next `0x007f1eb0` scan. On the non-ZF path a **bit-2 test** (mask `4`) of a byte reached through the `[EBP-0x10]` pointer-dereference chain chooses `0x00671580` when clear or `0x00671670([EBP+8])` when set, then scans again. The exact dereference sequence and branch instruction must be checked at the original x86 level before treating this as a stable memory contract.

**Not established:** that `0x00675a90` is an independent ordinary callable entry, that Ghidra has reconstructed entry flags correctly, what sets `ZF/AL`, that `[EBP+8]` is an object rather than a passed value, what the `+0x28` flag means, or that the two callees render anything. It could be a mid-function entry/shared loop or fallthrough from `0x00675a70`; **this is a hypothesis, not an established fact**. The reported decompilation boundary to next named `0x00675b20` does not settle x86 control-flow ownership. `FUN_00476196` *references* `0x00675a90` in the supplied export; without exact reference type/instruction it is **not proof of a direct CALL**, let alone proof of reaching that site in v668.

The submitted list of 27 function texts referencing `FUN_007f1eb0` is a **textual decompilation search**, not typed XREF, not a dynamic coverage map and not a proof that all entries are valid independent callers:
`0041bab0, 0041bfc0, 0041c490, 0041c510, 0049e9d0, 004d67e0, 004d6960, 00572ce0, 0063fc40, 00640b30, 0065da20, 0065dea1, 00675a70, 00675a90, 00675c20, 00675d70, 006dc7d0, 006dd3c0, 006dede0, 006e47c0, 006e4ef0, 007f1eb0, 007f2030, 007f2070, 007f2190, 00837df0, 008b7510`. Inclusion of `007f1eb0` itself underscores that textual matches cannot automatically be treated as typed direct-call edges.

## 3. Draw* gap: no causal link proven

**User-supplied v668** (same retail PE under a **recompiled guest P-code runtime, not native Windows SHIFT.exe**): 360 requested/rendered **host** frames; `host-frame-loop`, `blocker=null`, 1,734,402 dispatches, 4,728 unique functions, main guest function `0x00835590`, five waiting workers, validation errors 0. Repeated Clear/SetRenderTarget/BeginScene/EndScene/Present; 17 CreateVertexBuffer, 16 CreateIndexBuffer, 1 CreateTexture, 1 CreateDevice, 1 SetPixelShader and 1 SetVertexShader; **zero selected** `DrawPrimitive`, `DrawIndexedPrimitive`, `DrawPrimitiveUP`, `DrawIndexedPrimitiveUP` entries, `guest_draw_translation=false`. Supplied log SHA-256 `9630914c79a0816f453580f0bc884480df3f2f144cf158e4e735a7887a41cf37`; raw log not examined.

This establishes **absence in the selected trace**, not proof that `FUN_00675a90` was or was not executed, nor proof that its chosen branch prevents any Draw*. The draw API trace selection, execution coverage and frontend/race state must be checked separately. Creating buffers and executing scene/present API calls are not evidence of a translated retail draw. Neither 360 host frames nor dispatch/unique counts classify UI versus world. No provided typed XREF or original x86 path connects the iterator's two calls to a specific `IDirect3DDevice9::Draw*` callsite. The **closest testable frontier** is thus **which incoming flags and object/data actually choose the `0x00675a90` branch, whether that path executes in v668, and where the selected callee returns/continues**, not a proven missing iterator feature or guest-state defect.

## 4. One minimal, semantics-preserving verification

**Static prerequisite (read-only exact instruction/XREF export):** for the pinned retail PE, collect `0x00476196` containing exact reference instruction and type; exact instruction/CFG slices spanning `0x00675a70..0x00675b20` (including `0x00675a90`, incoming edges, writes of AL/ZF, EBP frame setup, `0x00671580/0x00671670` calls and returns); and `0x007f1eb0..0x007f2030` (with argument/register origins). Get **typed CALL/JUMP/FALLTHROUGH references** and source instruction addresses to `0x00675a90` and `0x007f1eb0`, plus direct xrefs from either branch's callees toward a *real* D3D9 Draw* callsite if present. Do not infer class/domain from function address neighborhoods. This distinguishes a genuine separate entry from a shared tail before interpreting incoming `ZF`.

**One bounded read-only replay:** same pinned PE/module/game data, first observed `0x00476196/0x00675a70/0x00675a90` path (if reached) through **the first attempted D3D9 Draw* dispatch or the 360-host-frame bound**. Capture an ordered, low-volume trace at:

- **T0 — caller edge:** exact caller and instruction site into `0x00675a90` (or proof of fallthrough/jump), guest thread ID, `EIP/ESP/EBP/EAX(AL)/EFLAGS.ZF/ECX/EDX` and `[EBP+8]`. Check register/flag provenance at predecessor instruction, not the decompiler's synthetic arguments.
- **T1 — decision at `0x00675a90`:** incoming AL/ZF, whether loop is entered, actual branch target. Only on the non-ZF path read the checked pointer chain through `[EBP-0x10]` and the byte at the computed `+0x28`, recording mask `0x4` with guest-pointer validity; do not assign it a class-field meaning.
- **T2 — each observed `0x007f1eb0` step (cap to a small sample plus final step):** actual x86 argument registers/stack, `param_1`, `param_2`, `[param_1+0x20]`, `[param_1+0xe0]`, pre `param_2[0..3]`; selected `index`, `entry=base+16*index`, `entry[0/+4/+8/+0xc]` only after bounded validated guest reads; post `param_2[0..3]`, `EAX`, **AL**, and subsequent chosen callee `0x00671580` or `0x00671670`. Keep thread ID and callsite/return address to tie all samples to the same traversal.
- **T3 — draw-boundary/correlation:** trace actual dispatch/import name, caller instruction, thread and active guest call stack for the **four Draw* methods**, or explicitly record **no such trace within the bounded window** and report trace truncation/coverage status. Compare the sampled iterator branch's caller ancestry to each Draw* event; mere temporal adjacency is not causality. If trace never reaches `0x00675a90`, record that negative observation and instrument the last verified ancestor, not fabricate branch outcomes.

**Existing trace facilities, verified in GitHub code:** `SHIFT_TRACE_GUEST_CALL_TARGETS`, `SHIFT_TRACE_GUEST_CALLER` (one caller), `SHIFT_TRACE_GUEST_CALL_IMPORTS`, `SHIFT_TRACE_GUEST_CALL_LIVE_LOG`, target/stack-slot filters, plus event thread ID, caller, return address, entry EAX/ECX/EDX/EBP/ESP and completion EAX in [`native_runtime/src/recompiled_pcode_module.cpp`, approximately lines 865–899 and 1319–1495](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/src/recompiled_pcode_module.cpp). [The event ABI](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/include/shift_recompiled_pcode_module.hpp#L102-L136) exposes those call fields. **Current call-trace events do not by themselves record EFLAGS.ZF, exact mid-block predecessor EIP, computed iterator memory layout or resolved branch target inside a P-code function**; obtain those read-only at instruction/dispatch boundaries. A target filter catches dispatched entries, not an ordinary intra-function fallthrough. The four Draw* entry names should be mapped to the actual runtime-traced import names/addresses; do not claim coverage merely by setting a filter. Existing GitHub code explicitly dispatches `d3d9.dll!IDirect3DDevice9::DrawIndexedPrimitive` in the import table, but that fact does not establish its use in v668.

**Classification from the probe, not speculation:** a confirmed Draw* descendant of the branch and object provenance tied to confirmed world/vehicle paths establishes that route; an observed iterator pass with no Draw* or a branch into unrelated calls establishes only the captured bounded behavior. Without typed callers/object provenance, do **not** label any path `menu/UI` versus `vehicle/world`. No force-setting flags, rewriting iterator outputs, bypassing polling or substituting Draw* is justified.

## Final adjudication

**`FUN_007f1eb0`: iterator/enumerator-like sequential scan — supported. Exact class/element semantics — unproven. `FUN_00675a90`: conditional consumer of its AL status — supported at Ghidra representation level, entry/control-flow ABI unresolved. Absence of selected Draw* in v668 — supported; causal relation to either function — **not established**.** Next action is a narrow typed-xref/instruction slice plus one ordered read-only runtime branch/caller trace. No runtime/renderer edit recommended.

**Related GitHub corroboration:** [earlier frontier evidence including a single `0x007f1eb0` return](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/evidence/retail_frontier_20261021/process1_pcode_frontier_v621_v659.json); [runtime dispatch/trace implementation](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/src/recompiled_pcode_module.cpp); [report-only branch policy](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process-reports/process-reports/README.md).

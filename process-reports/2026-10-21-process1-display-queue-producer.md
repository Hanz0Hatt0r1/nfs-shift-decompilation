# P1 — display/iterator helper 0x00831380: candidate item producers and bounded v674/v676 provenance

**Date:** 2026-10-21  
**Repository / branch:** `Hanz0Hatt0r1/nfs-shift-decompilation` / `work/process-reports`  
**Original:** retail PC 1.02 `SHIFT.exe` PE32 x86, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.  
**Method / scope:** independent static+runtime inference only from the complete user-provided decompilation/probe evidence and named GitHub reports. Original Ghidra project, local log files and executable bytes were **not opened**. All source-type labels are untrusted until separately resolved. No runtime/renderer code or guest memory changes.

## Executive verdict

**Bounded classification: producer candidates and two concrete last-writer sites identified; the source of the *actual 4-byte output item* is not yet proven.** The strongest new v676 correlation is that the exact receiver `0x2002d518` has both `[receiver+0x1c]=0x27cc0908` (last writer `0x0062f53d`) and `[receiver+0x24]=3` (last writer `0x004cb900`). The observed call of `0x00831380` returned **`AL=1`**. Its source shows an output store through `param_2` on its successful path, but no **post-call** output-memory sample or nested `[0x27cc0908+0x14]` was provided. Do **not** equate the raw `EAX=0x27cc0901` upper 24 bits with an item pointer or independent return value.

A nonzero `+0x24` and reported successful helper call **disfavor the narrow claim of a never-initialized/always-empty receiver in this v676 invocation**. They do **not** prove that the producer supplied meaningful display commands, that the caller consumed them successfully, or that a missing producer cannot affect another receiver, branch or replay. No guest D3D9 Draw* was recorded in the bounded v674 selected import trace; rendering/gameplay is not established.

## Supplied exact function evidence

~~~c
bool __fastcall FUN_0082f3c0(int param_1) {
  return *(int *)(param_1 + 0x24) == 0;
}

undefined4 __fastcall FUN_00831380(int *param_1, undefined4 *param_2) {
  int iVar1;
  if ((param_1[9] != 0) && (iVar1 = param_1[7], *(int *)(iVar1 + 0x14) != 0)) {
    *param_2 = *(undefined4 *)((*(int *)(iVar1 + 0x14) + -1) * *param_1 + *(int *)(iVar1 + 4));
    thunk_FUN_00d699b0();
    return 1;
  }
  return 0;
}

void __fastcall FUN_007ee360(int param_1) {
  char cVar1;
  cVar1 = FUN_00831380();
  while (cVar1 != '\0') {
    if (param_1 != 0) {
      FUN_007f10a0();
      FUN_00886930(param_1);
    }
    cVar1 = FUN_00831380();
  }
  if (*(int *)(param_1 + 4) != 0) {
    FUN_007f10a0();
  }
  FUN_004f0050();
  return;
}
~~~

`0x00835590`: user-provided Ghidra decompilation has **21 apparent calls** of `0x00831380`, **43** of `0x0082f3c0`, repeated loops conditional on `!FUN_0082f3c0()`, helper calls followed by `_GetFirstItem_AptDisplayListState__QAEPAVAptCIH__XZ()`, and one branch consuming an iterator value and calling vtable methods. **Counts are decompiler call expressions, not per-frame dynamic invocations; exact instruction xrefs and caller argument setup were not supplied.** The symbolic `GetFirstItem` label is a call label, not proof of receiver class identity.

**Exact computable successful-path reads of `0x00831380`:** assuming its Ghidra body correctly models this selected call: `*(uint32_t*)(receiver+0x24) != 0`, `nested = *(uint32_t*)(receiver+0x1c)`, `count = *(uint32_t*)(nested+0x14) != 0`; `stride = *(uint32_t*)receiver`, `base = *(uint32_t*)(nested+4)`; `payload_slot = base + (count-1)*stride` (32-bit arithmetic); `*(uint32_t*)out = *(uint32_t*)payload_slot`; followed by a call to `thunk_FUN_00d699b0` and successful Boolean result **`AL=1`**. “Count”, “stride” and “base” here are **arithmetic roles inferred from the expression**, not verified field names or class layout. The thunk may change the state and needs an independent instruction/body check. A success return does **not** reveal the stored payload absent a memory snapshot.

## Bounded runtime observations (do not cross-correlate separate replays)

| Probe | Observation | Limits |
| --- | --- | --- |
| **v674**, DXT3-integrated runtime SHA-256 `230a92c641305c1f7c84938a4c52d3def17f59914f40886616bd5e5942866b1b`, 54 overrides | 360 **host frames**, `host-frame-loop`/exit 0, 1,744,308 P-code dispatches, 4,729 unique functions, four waiting workers, zero validation errors, no blocker. `0x00835590` had **987** entry calls from `0x00835d80`, all returned `EAX=1`. `0x00831380` had **288** calls from `0x00835590` plus one from `0x007ee360`. The 288 call returns have varying upper EAX bytes but **AL=1**. Representative `0x00831380` from `0x00835590`: `ECX=0x2002d518`, `EDX=0x7ffdeefc`, `ESP=0x7ffdeeec`, return `0x00835b50`. | `guest_draw_translation=false`, `retail_rendering_proven=false`. No selected D3D9 Draw-import **entry** recorded on this bounded/traced path. Log SHA-256 `14b0335a1ace45e37a491df5e1c9547bd6058500cc490d7e3a6d2869d809429c`, 8,470,105 bytes locally; only the user report is accessible here. Host frames are **not** proof of menus/race/retail draw. |
| **v673** | `0x0082f3c0` target `+0x24` sampled **0** in all **8,192** captured calls, Boolean `AL=1` (zero-test satisfied). | Trace capped at 8,192; separate run, possibly distinct receivers/subobjects. Must **not** join these 8,192 reads with v674/v676 receiver `0x2002d518`, or assume all uses of this shared helper are the display queue. |
| **v676**, deliberately without P2 commit `1fef18a8` | Expected `unsupported D3D9 managed texture description` at P-code dispatch **1,303,056**. Before that: no reserved-low-memory fault; four `0x00831380` calls **without trace truncation** — three from `0x00835590` and one from `0x007ee360`. Raw log SHA-256 `c511d0156dbb7d8c71090e733bb2f75d09685dbe9a1873c68acab87b8925ff2b`. | Expected earlier graphics compatibility stop due to omitted adapter; **not evidence of a new queue-related failure** and not comparable to v674's full 360-frame host loop. Raw log hash was provided; raw bytes not accessed. |

### v676 exact writer/return correlation (single selected invocation)

**At entry to `FUN_00831380`:** dispatch **1,303,004**, caller `0x00835590`, return address `0x00835b50`, `ECX=0x2002d518`, `EDX=0x7ffdeefc`, `ESP=0x7ffdeeec`.

| Address / expression | Sampled entry value | Last-write provenance in v676 |
| --- | --- | --- |
| `receiver+0x1c = 0x2002d534` | `0x27cc0908` | writer PC/function `0x0062f53d`, write size **4**, value `0x27cc0908`, dispatch **434,489** |
| `receiver+0x24 = 0x2002d53c` | **3** | writer `0x004cb900`, size **4**, value **3**, dispatch **1,302,886** |
| `ESP+0x10 = 0x7ffdeefc` (**same address as EDX**) | **0** at entry | **No return-time output snapshot given.** The zero was sampled *before* this call and does not prove a zero result. |
| return `EAX` | `0x27cc0901` at dispatch **1,303,006** | **Only `AL=1`** should be construed as the helper Boolean result. Upper 24 bits are not an item identity. |

Both v676 entry predicates are either **directly true** (`+0x24=3`) or, for `[nested+0x14]`, **conditionally supported** by `AL=1` *provided that* the supplied decompilation models this exact runtime call path and no return/ABI distortion occurred. `nested+0x14 = 0x27cc091c` was **not sampled**, and `[0x7ffdeefc]` after return was **not sampled**. In particular the precise output item and any subsequent mutation by `thunk_FUN_00d699b0` remain unknown.

## New writer bodies and static producer candidates (same retail Ghidra export, supplied verbatim)

~~~c
undefined4 * __fastcall FUN_004cb900(uint param_1, undefined4 *param_2)
{
  undefined4 uVar1;
  undefined4 *puVar2;
  undefined4 uStack_8;
  if ((*(byte *)(param_1 + 0x2c) & 8) == 0) {
    uStack_8 = param_1 & 0xffffff00;
    FUN_0062ff90(0,4,4,0x1f,1,0,uStack_8);
  }
  if (*(int *)(param_1 + 0x18) == 0) {
    uVar1 = FUN_0062f2d0(*(undefined4 *)(param_1 + 4),param_1);
    *(undefined4 *)(param_1 + 0x18) = uVar1;
    *(undefined4 *)(param_1 + 0x1c) = uVar1;
  }
  puVar2 = (undefined4 *)FUN_004cb6d0();
  FUN_00457cc0(0,0);
  if (puVar2 == (undefined4 *)0x0) puVar2 = (undefined4 *)0x0;
  else *puVar2 = *param_2;
  if (*(int *)(param_1 + 0x24) == 0) {
    *(undefined4 *)(param_1 + 0x30) = *(undefined4 *)(*(int *)(param_1 + 0x18) + 4);
  }
  *(int *)(param_1 + 0x24) = *(int *)(param_1 + 0x24) + 1;
  return puVar2;
}

void __fastcall FUN_0062f53d(undefined4 param_1, uint param_2)
{
  int in_EAX;
  uint uVar1;
  undefined4 *puVar2;
  uint uVar3;
  int unaff_EBP;
  uint *unaff_ESI;
  int iVar4;
  bool in_ZF;
  if (in_ZF) {
    uVar3 = *(uint *)(unaff_EBP + 8);
    *unaff_ESI = uVar3;
    if ((param_2 & 0x100) != 0) {
      unaff_ESI[5] = 8;
      uVar3 = uVar3 + 8;
      goto LAB_0062f5f0;
    }
  } else {
    if (in_EAX == 0) in_EAX = 3;
    if ((param_2 & 0x100) == 0) {
      if (in_EAX == 0x1f) uVar3 = *(uint *)(unaff_EBP + 8);
      else {
        if (in_EAX == 0) in_EAX = 3;
        uVar3 = (1 << ((byte)in_EAX & 0x1f)) - 1;
        uVar3 = *(int *)(unaff_EBP + 8) + uVar3 & ~uVar3;
      }
    } else {
      if (in_EAX == 0x1f) uVar1 = 8;
      else {
        iVar4 = 3;
        if (in_EAX != 0) iVar4 = in_EAX;
        iVar4 = 1 << ((byte)iVar4 & 0x1f);
        uVar1 = iVar4 + 7U & ~(iVar4 - 1U);
      }
      uVar3 = uVar1 + *(int *)(unaff_EBP + 8);
      unaff_ESI[5] = uVar1;
      *unaff_ESI = uVar3;
      if (in_EAX != 0x1f) {
        if (in_EAX == 0) in_EAX = 3;
        uVar1 = (1 << ((byte)in_EAX & 0x1f)) - 1;
        uVar3 = uVar1 + uVar3 & ~uVar1;
      }
    }
LAB_0062f5f0:
    *unaff_ESI = uVar3;
  }
  uVar3 = *(uint *)(unaff_EBP + -4);
  unaff_ESI[2] = *(uint *)(unaff_EBP + 0xc);
  uVar1 = *(uint *)(unaff_EBP + 0x10);
  unaff_ESI[1] = uVar3;
  unaff_ESI[4] = param_2;
  if (uVar1 == 0) {
    if (unaff_ESI[3] != 0) goto LAB_0062f617;
    uVar1 = FUN_0062e1a0();
  }
  unaff_ESI[3] = uVar1;
LAB_0062f617:
  if ((unaff_ESI[4] >> 7 & 1) != 0) {
    puVar2 = (undefined4 *)FUN_00886900(0x20,unaff_ESI[3],5);
    if (puVar2 == (undefined4 *)0x0) puVar2 = (undefined4 *)0x0;
    else *puVar2 = 0;
    unaff_ESI[8] = (uint)puVar2;
    _GetHashSize_AptFrameStack__QAEXXZ();
  }
  uVar3 = FUN_0062f2d0(unaff_ESI[1],unaff_ESI);
  unaff_ESI[4] = unaff_ESI[4] | 0x200;
  unaff_ESI[6] = uVar3;
  unaff_ESI[7] = uVar3;
  return;
}
~~~

### Confirmed writer versus producer-of-item: two distinct levels

- **`+0x24` state:** `FUN_004cb900` increments `*(int*)(param_1+0x24)`; in v676 the last write of **3** to receiver `0x2002d518+0x24` is attributed to this writer. **High confidence for this observed writer**, conditional on the runtime's provenance machinery. The decomp also shows `FUN_004cb900` may assign a pointer to `+0x1c` when `+0x18==0` and obtains an insertion location from `FUN_004cb6d0`; if non-null it copies **`*param_2`** to **`*puVar2`**. This is the **strongest static candidate for item-content insertion**. It does not prove that this particular stored item was subsequently returned by `0x00831380`, or that all three count increments represent three successful payload copies (the copy is conditional).
- **`+0x1c` pointer:** `FUN_0062f53d` stores `unaff_ESI[7] = uVar3` = `[unaff_ESI+0x1c]`, where `uVar3` is produced by `FUN_0062f2d0`. Runtime v676 attributes the **exact store at `0x2002d534`** of pointer `0x27cc0908` to `0x0062f53d` at dispatch 434,489. **High confidence for this last writer on this instance**, but this is pointer/container setup, **not proof of inserted item content**.
- **Nested `[param_1[7]+0x14]`:** at v676 address `0x27cc091c`; neither its value nor writer was sampled. The success-path check suggests nonzero for the returned invocation, but **its producer is unidentified**. Static candidates `FUN_0062f2d0`, `FUN_004cb6d0`, the `thunk_FUN_00d699b0` update path and other alias writers require exact def-use / runtime last-writer evidence. Do not assert `FUN_004cb900` is the direct writer of nested `+0x14`.

**Special function-boundary caution:** the Ghidra body labelled `FUN_0062f53d` contains `unaff_ESI`, `unaff_EBP`, `in_ZF` and an internal `LAB_0062f5f0` transfer. This suggests nonlocal live-in register/flag state or cross-boundary control flow: its function-entry/independent-call status **cannot be inferred from its label alone**. A GitHub static note [`PROCESS_1A_P13A_FUN005FFC50_WRITABLE_CALLBACK_PAIR_D94_HELPER_INITIALIZER.md`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process-reports/docs/PROCESS_1A_P13A_FUN005FFC50_WRITABLE_CALLBACK_PAIR_D94_HELPER_INITIALIZER.md) explicitly describes a **different** helper path involving a trampoline into `0x0062f53d`, confirming that this address can serve as a continuation block. That report concerns **another receiver/object `+0xd94`**; it does **not** identify the v676 `0x2002d518` object. Reconstruct bytes, `getFunctionAt/getFunctionContaining`, CFG and xrefs before treating `0x0062f53d` as a normal isolated callable function.

A second GitHub note [`PROCESS_1A_P13A_FUN005FFC50_WRITABLE_CALLBACK_PAIR_D94_ENTRY_PAYLOAD_ADDRESS.md`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process-reports/docs/PROCESS_1A_P13A_FUN005FFC50_WRITABLE_CALLBACK_PAIR_D94_ENTRY_PAYLOAD_ADDRESS.md) describes `0x0062f2d0` as a block/payload allocator in a different container instance. It is **supporting context only**, not proof that v676 `0x27cc0908` has the same layout or that its returned slot points to the same logical item type.

## 0x007ee360: shared iterator helper, not yet proven shared receiver/queue

The provided `FUN_007ee360` decomp **calls `0x00831380` in a loop** and continues while the Boolean is nonzero; optional calls to `0x007f10a0` and `0x00886930` occur for nonzero `param_1`. This establishes **shared callable helper / control pattern**, not object identity. v674 and v676 each recorded **one call** from `0x007ee360`, but **no `ECX`, `EDX`, output destination, nested pointer or caller stack snapshot for that call** was included. Without comparing the live `ECX` and `[ECX+0x1c]` against the `0x00835590` calls, one cannot conclude both routines consume the same **instance** or even the same semantic queue. The decompiler displays calls without explicit arguments; the actual x86 fastcall receiver/out parameter setup should be validated in instruction-level disassembly.

## Narrowest read-only next probe

**One caller-scoped paired entry/return capture for `target=0x00831380`, callers `0x00835590` / `0x007ee360`; add only the two known last writers and the unknown nested field.** Keep ordered event IDs, guest thread ID, current guest PC/return address, guest ESP/ECX/EDX, and resolved object addresses.

1. **Entry slot snapshot**, target `0x00831380` (v676 representative `ECX=0x2002d518`): read `+0x00` (arithmetic multiplier), `+0x18` (if correlating producer), `+0x1c` (nested pointer), `+0x24` (counter), `+0x30` (producer-side cached word); optional `+0x2c` flag. For the **nested pointer** `N=RAM[ECX+0x1c]` sample `RAM[N+0x04]` (arithmetic base) and **`RAM[N+0x14]` (critical missing predicate)** with their last writers and guest pointer validity.
2. **Output slot at entry and return:** compute `out=EDX` from actual guest regs; in the cited v676 event `EDX=ESP+0x10=0x7ffdeefc`. Capture `RAM[out]` before and **after** the helper; if success, capture source `item_address = RAM[N+4] + (RAM[N+0x14]-1)*RAM[ECX]` and `RAM[item_address]` before the copy. Correlate with `AL` **only**, not full EAX, and optionally identify the `thunk_FUN_00d699b0` callsite/side effects. Trace guest writes to `out` and to the calculated payload slot, not just last-writer of the container header.
3. **Producer entries + writes:** capture `0x004cb900` entry receiver `param_1`, pointer/input `param_2`, return `puVar2` and **before/after `*puVar2`**, `+0x24` old/new, plus `+0x1c` if initialized; capture `0x0062f53d` **original instruction PC** (not assumed function entry), `ESI`/`EBP`/`EFLAGS` and actual `[ESI+0x1c]` old/new; record returned pointer from `0x0062f2d0`. Last-writer provenance for **`RAM[N+0x14]`** and for the **selected payload slot** is the decisive missing data; use address-specific byte/DWORD traces with bounded ring buffer rather than unbounded all-memory logging.
4. **Caller comparison:** for `0x007ee360` and `0x00835590` record caller guest function + exact guest CALL PC (when available), return PC, `ECX`, `EDX`, `N`, `out` and `AL`. Same helper call without equal or causally linked receiver/N **does not prove same queue**. For `0x0082f3c0` log its actual ECX/argument base and compare **only if its receiver is proven to correspond**; its use elsewhere is documented in [`REVENGINSTR_UI_STATE_GATE_EVIDENCE_20261019.md`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process-reports/docs/REVENGINSTR_UI_STATE_GATE_EVIDENCE_20261019.md), so its `+0x24` is not globally this object's counter.

**Decision criteria:** if a recorded producer `FUN_004cb900` writes `X` at the exact `item_address` later dereferenced by `0x00831380` and after-return `RAM[out]==X`, that establishes an **instance-specific producer→item→consumer join**. If `[N+0x14]` remains zero until the critical read and never gets written after valid initialization, a missing producer becomes plausible—but only after proving the call uses the **same** N and seeing the gate/branch. If `AL=1` and a valid item is written, the simple “no element ever produced” explanation is false **for that invocation**; downstream draw failure may still have a different cause. Do not write guest memory, force queue counters, or infer shader/rendering completion from host frames.

## Source provenance and limits

- **Primary sources:** user-provided exact Ghidra decompilation of `0x0082f3c0`, `0x00831380`, `0x007ee360`, `0x004cb900`, `0x0062f53d`; description of `0x00835590`; v673/v674/v676 bounded runtime observations and log SHA-256 values.
- **GitHub crosschecks:** two bounded Process 1A `+0xd94` helper/payload notes and the historical UI-state gate note cited above. They help identify reused helpers, continuation CFG and shared-offset pitfalls, but **do not establish** v676 receiver identity, full xref inventories, source machine bytes or the actual output item.
- **Not available/claimed:** original retail Ghidra project full xrefs, exhaustive producer list, exact CALL instruction addresses for `0x00831380`, authoritative function boundaries around `0x0062f53d`, byte-level disassembly for writer bodies, original runtime log bytes beyond supplied hashes, actual `[N+0x14]` value, `RAM[EDX]` after return, `item_address` and its writer, or any retail gameplay / guest Draw* proof.
- **Conclusion:** `v676_receiver_state_nonempty_on_success_path` supported; `last_writer_receiver_plus_1c=0x0062f53d` and `last_writer_receiver_plus_24=0x004cb900` supported by trace; **`item_content_producer_join_unresolved`**, **`shared_queue_with_0x007ee360_unresolved`**, **`guest_draw_translation_unproven`**. No semantic changes recommended.

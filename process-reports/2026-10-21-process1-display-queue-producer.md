# P1 — display/iterator helper 0x00831380: producer provenance through bounded v692

**Date:** 2026-10-21  
**Repository / branch:** `Hanz0Hatt0r1/nfs-shift-decompilation` / `work/process-reports`  
**Original:** retail PC 1.02 `SHIFT.exe` PE32 x86, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.  
**Method / scope:** independent static+runtime inference only from the complete user-provided decompilation/probe evidence and named GitHub reports. Original Ghidra project, local log files and executable bytes were **not opened**. All source-type labels are untrusted until separately resolved. No runtime/renderer code or guest memory changes.

## Executive verdict

**Актуальный bounded verdict (v692, с producer context v679–v691):** путь передачи DWORD §0x3f800000§ из indexed storage через retail setter/callback → вставку в контейнер → §FUN_00831380§ output доказан для отдельных трасс v691/v683; v692 непосредственно подтверждает, что §FUN_00831380§ выдаёт этот DWORD в stack-out §*EDX§ и следующий оригинальный retail consumer делает §ECX=item+4§, §FUN_005e1d50§ (§mov eax,[ecx]; ret§), получает §EAX=0§ и уходит по ветке §jne 0x008355e7§. **Это не доказывает**, что DWORD является invalid pointer в native Win32, типом float/1.0, tagged variant, или что ошибка P-code породила это значение. Отсутствует проверка реальной guest page commitment/protection по §0x3f800004§ и независимый сопоставимый original-retail execution. **Семантический fix не обоснован.**

**Предыдущие разделы v673/v674/v676 и их выводы о «неизвестном output» ниже сохранены как исторические:** для тех прогонов выход не снимался. Их **позже уточняют** v683/v692, которые измеряют результат stack-out и источник; не применять исторические неопределённости к v692 и не объединять счётчики из независимых запусков. v692 — bounded P-code host loop, не native retail rendering, не доказательство отсутствия любого Draw в будущем.

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

## v679–v692 producer/consumer provenance update (2026-10-21)

**Source separation:** New runtime counts and Ghidra/retail-machine-instruction descriptions in this section are supplied local P1 evidence; their raw logs, compiled runtime binaries, exact PE disassembly slices, and full local Ghidra xref lists were **not accessible** in this GitHub-only analysis. The original PE image is pinned to SHA-256 §eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1§. The GitHub repository search did not surface a complete indexed disassembly/xref report of §0x0082b150§ / §0x0082b840§ / §0x0082be30§ / §0x008353e0§ / §0x008355b5§; therefore these addresses and bytes are **source-supplied exact Ghidra/PE observations**, not independently re-read from a local PE here.

### Bounded chronology — do not equate host frames with retail draws

| Replay | Observation | Specific limit |
| --- | --- | --- |
| v679, integrated P1+P2 DXT3, SHA-256 §8a86d6cc80206b6abf9540349ee23bfb2cde3c624a310740913b25a4581cf85b§ | 360 host frames, exit 0, §host-frame-loop§, 1,741,455 dispatches, 4,729 functions, five waiting workers, no blocker or validation errors; 1,114 Clear requests/360 submissions, 1,112 Present requests/360 submissions, 752 pending Presents. Trace §4059e60c1c6be0eda3318ef7a6fa873218fe244d853617107a4e6fb79d0e0615§ not truncated: **664** §0x00831380§ paired calls, 663 from §0x00835590§ with §AL=1§, one from §0x007ee360§ with §AL=0§. §+0x24§ values **1/2/3 each 221**; illustrative cycle at dispatch 1,302,592/597/602 has **3→2→1**, subsequent 2/1 writes by §0x00d699b0§. Initial 3 last writer §0x004cb900§ at 1,302,474. | Output §*EDX§ **was not captured on return** in v679. §guest_draw_translation=false§, §retail_rendering_proven=false§; four selected Draw* imports zero. |
| v683, integrated DXT3 SHA-256 §69e50ef445f0f79a2563e6006e62821d28bfae0abe29677ee44b20d537adfeb2§ | 360 host frames, 1,741,723 dispatches, 4,729 functions, five waiting workers, no blocker/validation errors; same Clear/Present bridge counts as v679. Raw trace §408e0b29620ba38e9ef0fc7320ca491f7dd757c452b3909beb21a542fb75d0b2§ (4,930,536 bytes, 4,245 lines), no truncation. **663** §0x00831380§ calls from §0x00835590§, all §AL=1§ and **§*EDX=0x3f800000§ after return**, writer §0x00831380§ at stack-out §0x7ffdeefc§. §FUN_005e1d50§ exact §mov eax,[ecx]; ret§: 663 main-caller invocations from §0x00835590§ at return §0x00835b5b§ all §ECX=0x3f800004§ → §EAX=0§; no corresponding §0x00835590→0x008352f0§ (two total calls to §0x008352f0§ were from §0x008353e0§). | An output DWORD was observed, **not a validated C++ pointer/type**. Memory at §0x3f800004§ was zero/unreadable by diagnostics; mapping validity unknown. No selected Draw* imports; no native gameplay proof. |
| v687, integrated SHA-256 §d46ea64435ed73d9e799d37e7ce219238d780bde7b251d6f2e9666962bd88cb8§ | 360 host frames, 1,741,305 dispatches, 4,729 functions, three waiting workers, no blocker/validation errors. 2,008 §0x008353e0§ entries / 2,007 returns (caller-scoped trace, **no truncation**); **664 calls to §0x004cb900§**. Incoming §EDX§ points to a stack local containing §0x3f800000§. §0x008353e0§ saves input §EDX§ through §ESI§ into §[EBP-4]§; after successful vtable §+0x134§ predicate, calls §FUN_004cb900§ with §ECX=EBX+0x1e80§, §EDX=&[EBP-4]§. | 2,008/2,007 is an observed count mismatch, not proof of loss. The underlying source-array producer wasn't traced in v687. No selected Draw* imports. |
| v691, integrated, same SHA-256 §d46ea64435ed73d9e799d37e7ce219238d780bde7b251d6f2e9666962bd88cb8§ | 360 host frames, 1,741,414 dispatches, 4,729 functions, three waiting workers, no blocker/validation errors; full trace §b49d2124d59bd50f019b9681604d93f15398881d0df35b64bdb52fec7d1dd2cf§ (21,675,068 bytes) **no truncation**. **663** calls to §0x0082be30§ from §0x007e3e20§: §ECX=0x27f867c0§, §EDX/index=0§, §[ECX+0x14]=0x27f869a0§, §[ECX+0x18]=0x27f86a00§, §[0x27f869a0+index*4]=0§, so old DWORD source is §0x27f86a00§. Always §[0x27f86a00]=0x3f800000§. Third argument (§stack+4§) values: §0x27bda660§ on 442 entries, zero on 221. Every old-nonzero callback §vtable+0x238§ resolved to §0x008353e0§ with §EDX=0x3f800000§. | **Byte provenance** at source: byte 0 last writer §0x0082b150§ (size **1**), bytes 1–3 last writer §0x0082b840§ (write size **4**, DWORD value §0x3f800000§). §0x0082b150§ had 1,326 entries from §0x007e3e20§, indices 13/14 equally, param3 values 0 (663), §0x3f800001§ (442), §0x3f800000§ (221). This **does not** mean §0x0082b150§ generated the complete DWORD. Source of §0x0082b840§'s incoming value vector remains untraced. |
| **v692**, integrated same SHA-256 §d46ea64435ed73d9e799d37e7ce219238d780bde7b251d6f2e9666962bd88cb8§ | 360 host frames, **1,738,845** dispatches, 4,729 functions, three waiting workers, validation 0, blocker null; bridge **1,112 Clear / 1,111 Present** requests, **360 host submissions each**. Trace §a2bdcdd676ed083ee76697ba34e4bb287b282d73201ec705b44503937f7ee51d§ (4,069,724 bytes), filters §0x00831380§ / §0x005e1d50§ / §0x00835590§, four Draw* imports selected. Exactly **660** paired §0x00835590→0x00831380§ calls with **§*EDX=0x3f800000§ after** (pre: zero 220, §0x3f800000§ 440); exactly **660** paired §0x00835590→0x005e1d50§ calls with §ECX=0x3f800004§, diagnostic target DWORD zero, §EAX=0§; **665** paired §0x008353e0→0x005e1d50§ calls including 660 same-receiver/value plus five others; §0x00835d80→0x00835590§ 1,111 paired calls all §EAX=1§. | §guest_draw_translation=false§, §retail_rendering_proven=false§. All four selected Draw* imports **zero events** in this bounded trace; **no claim outside window**. Different numbers v691 663 vs v692 660 **are not longitudinal state change** (separate bounded runs). |

**What can be said causally from counts:** v679 shows §0x004cb900§ produces nonzero receiver count and §0x00d699b0§ subsequently decrements it, so the selected **iterator/container is not simply an untouched permanently empty queue** in that replay. v683/v691/v692 show that a specific bit-pattern travels across producer and consumer instructions, not a full type interpretation. v692 §0x00835d80→0x00835590§ §EAX=1§ confirms frame-service return for this caller, **not** successful retail UI, gameplay or Draw. A lack of selected Draw-import records is a bounded observation, not proof the local §jne§ caused global renderer inactivity.

### Static retail setter/callback/consumer chain and ABI evidence

**Indexed storage writers (Ghidra export supplied by user; exact PE bytes cited only for selected instructions):**

1. §FUN_0082b150(p1,index,byte_value)§ checks count via a vtable §+0x34§ method, then performs a **one-byte** store to the indexed storage derived from §[p1+0x14]§ and §[p1+0x18]§. v691 confirms it as **last writer of only byte 0** at §0x27f86a00§. Its caller-provided values §0§ / §0x3f800001§ / §0x3f800000§ are not evidence of a whole-word write, regardless of higher argument bits.
2. §FUN_0082b840(p1,index,values)§ checks count and vtable §+0x3c§; for return §7§ copies four consecutive DWORDs from §values§ into indexed storage, for return §0xb§ calls §FUN_0064fda0§ on four values then copies two DWORDs. **No semantic type name** is justified for §7§/§0xb§. v691's last-writer source bytes 1–3 confirm at least one four-byte store with value §0x3f800000§ from §0x0082b840§, but its **§values§ pointer/content producer and selected type return** remain unknown.
3. §FUN_0082be30(p1,index,new_dword)§ checks count; the old §uint32§ is read from §[[p1+0x14]+index*4]+[p1+0x18]§ (retail formula, value-based). If **old !=0**, machine code §0x0082be7d..0x0082be91§ loads global §DAT_00c26058§, reads vtable slot §+0x238§ and §call eax§, passing **old DWORD in §EDX§** to the callback, with callback return site §0x0082be91§. If new DWORD !=0, §FUN_00839e20§ is called; finally writes the new DWORD into indexed storage. v691 establishes that old DWORD equals §0x3f800000§ at the exact 663 observed invocations and §vtable+0x238§ resolves to §0x008353e0§. The distinction **old value callback before new value write** matters: a null new value is **not** the callback payload.
4. §FUN_008353e0§ saves incoming §EDX§ through §ESI§/§[EBP-4]§, tests a distinct vtable §+0x134§ predicate, and when true calls §FUN_004cb900§ (§0x0083539d..0x008353a6§) with receiver **§ECX=EDI+0x1ad8§** and **§EDX=&[EBP-4]§** (source-supplied exact local PE instruction evidence). The helper copies §*param_2§ into a selected item slot when nonnull and updates §+0x24§; v687/v691 support this producer route. **Do not silently reconcile** older v687 notation §EBX+0x1e80§ with later exact §EDI+0x1ad8§: both must be recorded as run/context-dependent reported receiver expressions until live registers and/or instruction bytes at the exact callsite prove equivalence. Their numerical offsets differ; treat the later §EDI+0x1ad8§ as **latest supplied exact PC observation**, not as a license to assign a layout. The shared item value and target alone do not prove receiver-base equality across reports.
5. §FUN_00831380§: if §p[9]!=0§ and §[p[7]+0x14]!=0§, writes **one DWORD** via §out§ by dereferencing §[p[7]+4]+([p[7]+0x14]-1)*p[0]§, then calls §thunk_FUN_00d699b0§ and returns Boolean §AL=1§. In v683/v692, **§*out=0x3f800000§** is observed. Earlier provenance (v686 supplied) reports 477 source values with last item writer §FUN_004cb900§, called from §FUN_008353e0§; list pointer writer §0x0062f53d§, list base writer §0x0063ac20§, count writer §0x004cb6d0§. These **are separate observations**: an exact per-event v691 writer→consumer match for all 663 calls still requires correlated source-slot address and write event on the same invocation. v685 saw 657/663 sampled source values matching §0x3f800000§, not an invariant from all runs.
6. **Original retail consumer exact instruction sequence**, SHA-pinned PE (source-supplied exact bytes/instruction decoding):

   ~~~asm
   0x008355b5: call 0x00831380
   0x008355ba: mov esi, [ebp-8]
   0x008355bd: lea ecx, [esi+4]
   0x008355c0: call 0x005e1d50
   0x008355c5: cmp eax, 1
   0x008355c8: jne 0x008355e7
   0x008355d0: call 0x008352f0  ; reachable on EAX == 1
   ~~~

   §FUN_005e1d50§ is §mov eax,[ecx]; ret§ (exact reported bytes). When §*out=0x3f800000§, §ESI=0x3f800000§ and getter's guest address §ECX=0x3f800004§. The v692 P-code diagnostic returned §EAX=0§ (660/660), which selects §jne 0x008355e7§ at the local retail comparison; the §0x008355d0§ call is **skipped for those invocations**. v683 only saw two §0x008352f0§ calls from §0x008353e0§ and zero from the §0x00835590§ main path. This is **a bounded local control-flow exclusion**, not a proven causal explanation of zero Draw* imports.

**ABI/type confidence:** (i) §0082be30§ callback passes a **raw 32-bit old slot value in EDX**; (ii) §008353e0§ saves that raw DWORD and §004cb900§ consumes the **address of the local copy** (§EDX=&local§), not necessarily a C++ object pointer; (iii) §00831380§ passes a raw DWORD via output pointer §EDX§; (iv) §00835590§ **uses** that DWORD as a base address for a dereference at §item+4§. This demonstrates **pointer-like consumption by this branch**, not that upstream setter's slot is exclusively pointer-typed, nor that a tagged/value discriminator is absent, nor that §0x3f800000§ is a legitimate object pointer. Its IEEE-754 bit pattern matching 1.0f does **not** type the value. To confirm a tag/union case requires actual type discriminator refs/branches, object construction/ownership or contrasting native-retail path, not analogy from symbol names and offsets.

### Guest page validity: why the zero diagnostic is not yet an original Win32 read

The v692 diagnostic reported §RAM[0x3f800004]=0§ and §FUN_005e1d50§ returned §EAX=0§. **The replay uses a flat / sparse 4-GiB address reservation:** diagnostic addressability or zero bytes in its backing storage are not an original Win32 §MEM_COMMIT§/page-protection observation. Such a read does **not** prove that §0x3f800004§ would be mapped/readable in native Windows or under Wine, and therefore cannot establish that this is a valid guest object, that a type byte is zero, or that the original retail binary would return zero rather than fault in an equivalent state. The [repository runtime overview](../native_runtime/README.md) describes sparse 4-GiB §ram§. The [native capture code](../native_capture/shift_d3d9_capture.cpp) shows an existing read-only pattern using §VirtualQuery§ and §MEM_COMMIT§ + access-protection checks; **that implementation was not changed**.

**Smallest decisive next read-only differential probe (single matched-event recipe):**

- **Trigger:** take the **first matching** original retail §0x008355b5 → 0x008355c0§ iteration (same PE/hash and controlled input/state), and one matching P-code iteration, bounded to **one** output event per environment. At §0x008355ba§/§0x008355bd§ log §[EBP-8]§, §ESI§, §ECX=ESI+4§, §EAX§ after §0x005e1d50§ and the actual branch decision at §0x008355c8§; also log thread ID, caller return and queue-item source address (if provenance is available). At the P-code side, **consult loader/virtual-memory allocation/protection metadata**, not merely host §ram[]§ contents. At original retail under Windows/Wine, **query §VirtualQuery(ESI+4)§** for a 4-byte range (region bounds, §MEM_COMMIT§, readable protect excluding §PAGE_NOACCESS§/§PAGE_GUARD§); **only then** use read-only bytes at §ESI+4§. If it is not committed/readable, record the failure **without dereferencing** it.
- **Outcome discriminator:** original retail same item §0x3f800000§ + **uncommitted/unreadable §0x3f800004§** supports an **invalid dereference for that original execution** (the fact that P-code read returns zero would then be a *compatibility/mapping difference*, not automatically an incorrect producer). Original retail **committed/readable §0x3f800004§** with an actual §1§ and accepted branch would distinguish state/memory-image differences; inspect object/variant tag and caller guard before declaring a type. Original retail has a **different item/tag/branch** → trace just one upstream §0x0082be7d§ old DWORD/callback resolution and the §0x0082b840§ §values§ input for that same event to locate the divergence. Failure to reach the matched event cannot be used as positive evidence for either theory.
- **No mutations:** no guest write, forced tag, counter reset, type cast substitution, or P-code semantic fix. Do not rely on allocating/touching §0x3f800004§ to make a read succeed; that would destroy the mapping evidence.

**What blocks a definitive answer:** no native-original page-commit/protection/read observation at §0x3f800004§ in the same setter/consumer sequence; no verified discriminator/value-case xrefs for the specific indexed slot; no §FUN_0082b840§ incoming §values§ provenance or demonstrated intentional construction of §0x3f800000§ as a valid dereferenceable object; no full local Ghidra xref dump covering this receiver. The observed raw DWORD path is source-backed, but **producer-callback ABI correctness, logical type, original Win32 page validity, and P-code equivalence remain separate questions**.

### Historical 0x0057da20 note (not a present producer blocker)

The §rvi_0057da20§ missing export was **historical v527** evidence from caller §0x00590d60§ (see [process1_scheduler_return_quantum.json](../evidence/retail_frontier_20261021/process1_scheduler_return_quantum.json)). The supplied exact PE 12-instruction body is an **allocator callback**: lazily initializes global §0x00be6ca8§ through §0x0062e1a0§ (argument §0x00aaa828§) and invokes §0x00638300§ using callback argument §[ESP+4]§ and size §0x80§/zero. The cited §0x0057e380§ / §0x00590d60§ caller context handles §Online_PlasmaLogEnabled§ / §Online_GameProtocolVersion§; these names do **not** establish an audio path or a current frontend cause. The user reports that the v659 module manifest includes §rvi_0057da20§, and the [repository v621–v659 frontier summary](../evidence/retail_frontier_20261021/process1_pcode_frontier_v621_v659.json) records a later bounded host-frame-loop with no missing-export blocker. Do **not** report §0x0057da20§ as a present blocker. Full v659 manifest is external to currently indexed GitHub files, so the export entry itself was not independently revalidated here.

### Current result

**Established (bounded):** §0082b840§ full-DWORD write/§0082b150§ low-byte overwrite → old DWORD §0x3f800000§ in indexed source §0x27f86a00§ → §0082be30§ vtable §+0x238§ call with raw §EDX=0x3f800000§ (resolved to §008353e0§ in v691) → §004cb900§ candidate/observed item-copy path → §00831380§ §*EDX=0x3f800000§ → §00835590§ calls §005e1d50§ at §0x3f800004§ → §EAX=0§ in P-code → **retail local §jne§ skips §008352f0§** for sampled v692 iterations. The per-event link between v691 writer and v692 consumer is **a cross-run reconstruction**, supported by consistent bit patterns and static ABI, not one atomic joined trace.

**Not established:** invalid-pointer origin, native page mapping/AV, legitimate tagged union, P-code translation bug, cause of no selected Draw*, or retail frontend/race completion. Minimal next evidence is **one page-validity-aware original-vs-P-code consumer boundary capture**, followed by upstream setter capture only if the two executions diverge.


## Source provenance and limits

- **Historical primary sources (v673–v676; superseded where indicated above):** user-provided exact Ghidra decompilation of `0x0082f3c0`, `0x00831380`, `0x007ee360`, `0x004cb900`, `0x0062f53d`; description of `0x00835590`; v673/v674/v676 bounded runtime observations and log SHA-256 values.
- **GitHub crosschecks:** two bounded Process 1A `+0xd94` helper/payload notes and the historical UI-state gate note cited above. They help identify reused helpers, continuation CFG and shared-offset pitfalls, but **do not establish** v676 receiver identity, full xref inventories, source machine bytes or the actual output item.
- **Not available/claimed:** original retail Ghidra project full xrefs, exhaustive producer list, exact CALL instruction addresses for `0x00831380`, authoritative function boundaries around `0x0062f53d`, byte-level disassembly for writer bodies, original runtime log bytes beyond supplied hashes, actual `[N+0x14]` value, `RAM[EDX]` after return, `item_address` and its writer, or any retail gameplay / guest Draw* proof.
- **Historical v676 conclusion (not current v692 verdict):** `v676_receiver_state_nonempty_on_success_path` supported; `last_writer_receiver_plus_1c=0x0062f53d` and `last_writer_receiver_plus_24=0x004cb900` supported by trace; **`item_content_producer_join_unresolved`**, **`shared_queue_with_0x007ee360_unresolved`**, **`guest_draw_translation_unproven`**. No semantic changes recommended.

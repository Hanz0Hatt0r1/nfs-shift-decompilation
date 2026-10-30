# P4 Plan: PPC codegen diagnostics hardening

Status: planning / analysis. Not a fix. No code changed by this document.
Branch: `work/xbox360-retail-runtime-p1-20261023`. Date: 2026-10-30.
Process: P4 (PPC → C++ codegen lane). Related open gate: X1 (generation + first boot).

Every claim names a file and line, or is explicitly marked **unknown**. The point of this
document is to bound what the generator silently accepts, rate the risk of silent
wrong-code on the non-reference ladders (Vulkan 1.1 / Android ARM64), and specify tests
that can *prove* the generated C++ matches the retail PPC semantics for the affected
blocks.

---

## 0. Evidence base

- Codegen diagnostic record:
  `evidence/xbox360_rexglue_preflight_20261022.md:22` —
  "The run also reported an unresolved branch target from `0x826F0E60` to `0x826FF380` and
  repeated `Unexpected float16_4 pack instruction` diagnostics."
  The same line records the summary `505 written, 0 unchanged, 0 deleted` and states the
  generated output and logs remain outside Git.
- Codegen source (SDK clone, pinned — see `docs/XBOX360_BUILD_PINS_20261030.md`):
  `/home/pes/work/rexglue-sdk-xbox360-memory-lifecycle-20261025`.

---

## 1. Finding 1 — `Unexpected float16_4 pack instruction` is a *warning on a fully
implemented* opcode, not an unsupported instruction

This is the most important correction in this document. The phrasing invites the reading
"the generator does not implement this instruction and stubbed it". That reading is wrong.

Handler: `src/codegen/builders/vector.cpp:1325-1331` (SDK clone above).

```cpp
    case 5:  // float16_4
    {
      // Pack 4 elements into 64 bits (4 x 16-bit floats)
      // Guest element 0 goes to highest 16-bit position, element 3 to lowest
      // Output u16 index = (3-i) + 2*shift for element i
      if (ctx.insn.operands[3] != 2 || ctx.insn.operands[4] > 2)
        REXCODEGEN_WARN("Unexpected float16_4 pack instruction at {:X}", ctx.base);
```

- The switch is on the **PK** auxiliary/type field: `case 5` is `float16_4`. Sibling cases
  in the same function confirm the family and the style: `case 3 // FLOAT16_2`
  (`vector.cpp:1282`), `case 4 // NORMSHORT4` (`vector.cpp:1308`), `case 1 // NORMSHORT2`
  (`vector.cpp:1214`), and a D3DCOLOR case above it (`vector.cpp:~1180`).
- So this is the **`pk` (pack) builder** for PPC vector pack instructions, with the
  element-conversion algorithm written per case. `float16_4` **is emitted in full** —
  after the warning, the code iterates `for (size_t i = 0; i < 4; i++)` and emits
  bit-exact float→half conversion including NaN/overflow handling
  (`>= 65504.0f` → `0x7FFF`), sign injection, and the reversed element order that Xenos
  guest array layout requires (guest element 0 at host index 3).
- The warning fires **only** on the operand guard
  `operands[3] != 2 || operands[4] > 2`. `operands[3]` and `operands[4]` are the shift /
  mask-ish operands of the PK form; `operands[4]` is also indexed directly in the emitted
  code (`dstIdx = (3 - i) + (2 * ctx.insn.operands[4])`), which is only in range when the
  guard holds.

### 1.1 What that means

- **The generator emits correct-looking code anyway.** It does **not** trap, abort, or
  stub. It warns and proceeds with a formula that is *structurally* the same but was
  presumably only validated for the guarded operand values.
- The risk is therefore **silent wrong packing on unvalidated operand combinations**, not
  a missing implementation. That is a strictly worse failure mode than a trap, because
  nothing fails loudly at run time.
- **unknown**: which operand encodings actually trip the guard in the retail image, and
  whether the emitted formula is wrong for them or merely unverified. The `at {:X}`
  argument is `ctx.base` (the guest address), so the warning *does* carry the address of
  every offending instruction — the diagnostic is enumerable (see §3).

### 1.2 Likely PPC opcode identity

`float16_4` is a **4-element float→half pack**. On the Xbox 360 PPC-VMX ISA the
`pk` family writes to a GPR; the 4-lane form is the VMX/Altivec-side `vpkuhum`-class
operation fed the `3.0+`/float forms. **unknown (must be confirmed from the decoder, not
from memory)**: whether the guest instruction is the scalar `pk` form with the
`GQR`-selected type or an Altivec `vpkuhum`-family op. The correct authority is the same
decode table used by the builder — the codegen's instruction decoder that produced
`operands[3]`/`operands[4]` in the first place. That decoder is where the answer must be
read off, and it is a one-file lookup once the instruction pointer is known (§3, T2).

Relevant secondary consequence: `float16_4` converts between **float and half** — i.e. it
appears in code doing float packing for rendering/math upload. It is plausible (not
proven) that some of these sites are on the graphics path, which couples this lane to P2's
renderer work.

---

## 2. Finding 2 — the unresolved branch target is **not** in the same failure class: it
is a hard `REX_FATAL` at run time

`0x826F0E60 -> 0x826FF380` is reported as an "unresolved branch target". The emission site
is not a warning; it produces a run-time abort:

`src/codegen/builders/context.cpp:318` and `:326` (identical shape, two branches of
`emit_conditional_branch`):

```cpp
        REXCODEGEN_ERROR("Unresolved conditional branch to 0x{:08X} from 0x{:08X} (no CallTarget)", …);
        println("\tif ({}{}.{}) REX_FATAL(\"Unresolved branch from 0x{:08X} to 0x{:08X}\");",
                not_ ? "!" : "", cr(insn.operands[0]), cond, base, target);
```

and the call-side equivalents at `context.cpp:268-275`:

```cpp
    REXCODEGEN_ERROR("Unresolved function 0x{:08X} from 0x{:08X}", address, base);
    println("\t// FATAL: unresolved function 0x{:08X}", address);
    println("\tREX_FATAL(\"Unresolved call from 0x{:08X} to 0x{:08X}\");", base, address);
```

Properties that follow directly:

- **Fail-closed by construction**: the generated C++ contains `REX_FATAL("Unresolved
  branch from 0x826F0E60 to 0x826FF380")` guarded by the original CR condition. It fires
  **only when that branch condition is taken**. Not taken → no failure. This is why the
  preflight (evidence `xbox360_rexglue_preflight_20261022.md:22`) could complete with
  diagnostics present.
- **Not silent**: a failure here is loud and named, with both guest addresses.
- Classification by `classifyTarget` (`context.cpp:283-…`, called from
  `emit_conditional_branch`): `InternalLabel` (local goto), `Function`, `Import`,
  `Unknown`. The unresolved path is taken when `findCallTarget(base)` returns nothing (the
  target is unknown to the function graph) or the target kind is `Unknown`. That means the
  root problem is **function discovery**, not instruction semantics: the codegen never
  found (or never created) a `FunctionNode` covering `0x826FF380`.
- The title task's phrasing "0x826F0E60 -> 0x826FF380 analysis plan" is satisfied by §4.

**unknown**: whether `0x826FF380` lies inside an already-generated function body (in which
case the branch is a *local* branch whose target was misclassified — a graph bug) or
outside every discovered function (in which case it is genuinely undiscovered code, e.g.
reached only through a computed/virtual dispatch). These two cases have completely
different fixes and must be distinguished by §4 T1, not assumed.

---

## 3. Finding 3 — the diagnostics are enumerable and mostly unreachable-unknown

Three facts make a proper enumeration possible without re-running the whole codegen:

1. The `float16_4` warning prints `ctx.base` (`vector.cpp:1331`), i.e. **the guest address
   of every offending instruction**. A single codegen log therefore yields a complete list
   of offending addresses.
2. `REXCODEGEN_ERROR` and `REXCODEGEN_WARN` are distinct severities in the same logging
   facility, so the unresolved-target family and the pack family can be separated in the
   log without heuristics.
3. The generated C++ is a **plain text corpus** (`505 written` output units). Grepping it
   for `REX_FATAL("Unresolved branch from 0x826f0e60")` (case/format per emission) locates
   the exact unit and function, and a reverse map from unit → guest address range gives
   reachability analysis without executing anything.

For the pack warning there is no per-site generated marker (it is warning-only), which is
itself a hardening gap: **the generated C++ for an unvalidated `float16_4` site is
indistinguishable from a validated one**. That is the single most important thing to fix
(T3) — a comment marker at the emission site costs nothing and makes the corpus greppable.

### 3.1 Reachability from `xstart`

The startup ladder begins at the retail `xstart` entry (documented in the X2 rows of
`coordination/xbox360_rexglue_status.json` and the migration docs). Enumerating reachability
must be **static**, and in this order:

1. Build the call graph **from the generated C++**, not from the PPC: every emitted
   `<func>(ctx, base);` call (`context.cpp:261`) and every `if (…cr…) { <func>(ctx, base); }`
   conditional tail call (`context.cpp:~300`) is a direct edge; the address→name map comes
   from the same unit files. Function pointers / virtual dispatch appear as indirect calls
   and must be marked **unknown-edge**, not traversed as unreachable.
2. Seed with `xstart`; forward-reach; intersect with the offending-address list.
3. Report three sets: **reachable**, **unreached-but-resolvable**, and
   **unreachable-by-static-analysis** (only reachable via unknown edges) — the third set
   must be treated as "possibly executed" so that no site is silently declared dead.

**unknown until T1 runs**: the actual size of each set for the retail image. The preflight
line says "repeated … diagnostics" without a count (`xbox360_rexglue_preflight_20261022.md:22`),
so the committed evidence does **not** contain the number of affected sites. It must be
recovered from the codegen log, which the same line says remains outside Git — so the first
task is to regenerate or locate that log, not to guess.

---

## 4. Silent-wrong-code risk rating on the SHADOW LADDER

The ladder is the set of non-reference configurations (Vulkan 1.1 strict, Android ARM64 /
Mali) that must behave identically to the Linux x86-64 reference. Risk is rated on
*detectability*, because all of these paths are already fail-closed *somewhere* — the
question is whether the ladder catches them.

| Family | Wrong-code mechanism | Crash locally? | Detectable on ladder? | Rating |
|---|---|---|---|---|
| **`float16_4` unvalidated operands** (`vector.cpp:1325-1331`) | emits a *structurally plausible* pack formula for operand encodings it never validated; result is a silently mis-packed 64-bit value | **No** | **No** — code is identical on every platform, so the ladder cannot see the difference | **HIGH** (silent, portable, unprevented) |
| **Unresolved branch/call target** (`context.cpp:268-275`, `:318-326`) | `REX_FATAL` when the condition is taken, guarded correctly | **Yes, loud** — only if taken | **Yes** — same code, but the failure is explicit and address-named | **LOW** (loud, attributed) |
| Other opcode gaps | **unknown** — the preflight line names only these two families; a full census is T4 | unknown | unknown | **unknown** |

Concretely: a `float16_4` site with unexpected operands that is on the menu/render path
could produce a wrong packed value *identically on Linux x86-64, Vulkan 1.1 and Mali*, so
the ladder's differential comparison would show "all three agree" and **still be wrong**.
Cross-platform agreement is not evidence of correctness for this family. That is the core
reason this family deserves a HIGH rating despite never having produced a crash.

The one mitigating fact: the emitted algorithm is float→half conversion in code, and any
error is confined to the 4 half-precision elements (no memory corruption, no control-flow
effect). The blast radius is numerical, not structural.

---

## 5. Differential test design: generated C++ vs a reference decode

The goal is an **instruction-level** differential, not a whole-function one: a wrong pack
produces a wrong value, and only a per-block comparison names the culprit.

**Method**

1. **Extract** every offending block from the generated C++ by guest address (T3's marker
   makes this a grep).
2. **Reference decode**: take the same guest addresses and decode the retail PPC bytes with
   an independent decoder — `llvm-mc -triple=powerpc64-…` or `powerpc-linux-gnu-objdump -d`
   over the exact 16-byte window per instruction. This is deliberately a *different*
   implementation from the SDK's own decoder; agreeing with yourself proves nothing.
3. **Model**: execute the extracted C++ block and the reference instruction semantics on a
   parameter sweep over operand values, including the guard edges
   (`operands[3]` ∈ {2, ≠2}, `operands[4]` ∈ {0,1,2,3+}) and IEEE edges
   (`±0`, `±inf`, `NaN`, `65504.0f`, `65505.0f`, denormals). Compare the resulting
   64-bit outputs bit-for-bit.
4. **Report**: per-address mismatch count and the first divergent operand tuple. A
   mismatch is a *codegen bug*, and the operand tuple is the reproducer.

For the **unresolved branch target**, the differential is different: there is no wrong
value, there is a missing function. The test is a **graph differential** — compare the
set of branch targets classified `InternalLabel`/`Function`/`Import` against a reference
recovery (e.g. an independent linear/recursive-descent disassembly of the same range) and
assert every target lands in a generated function or a known import. Failing that,
assert the target is *deliberately* reported so `REX_FATAL` is expected-and-documented.

**Committed fixtures**: the differential must run in CI without the retail XEX (which is
outside Git). Therefore each test fixture is a small, legal-to-commit artefact: the guest
*instruction words* (16-byte windows), the generated C++ snippet address, and the expected
64-bit outputs computed by the reference decoder. The instruction words are retail data
derived from the XEX — **unknown whether the repo's content policy allows committing
16-byte instruction windows**; until that is resolved the fixture must be *derived at test
time* from a locally-present XEX and skipped (with an explicit `SKIP` result, never a pass)
when absent. **Do not paper over absence with a pass.**

---

## 6. CI gate design

Two gates, matching the fail-closed culture; neither may be satisfied by "no output".

**G1 — Diagnostics census gate (cheap, always-on, no XEX needed).**
A committed census file `coordination/xbox360_codegen_diagnostics_census.json` lists every
diagnostic site (guest address, family, function, unit file, reachability set from §3.1).
The gate asserts:
- every `float16_4` warning address appears in the census with an explicit
  `validated: true|false`;
- no site is silently added or removed (a codegen re-run producing a *new* warning address
  fails the gate until the census is updated — this is the anti-regression property that
  currently does not exist);
- every `REX_FATAL("Unresolved branch …")` site in the generated corpus has a census entry.

**G2 — Semantic differential gate (needs local XEX; skips loudly otherwise).**
Runs §5. Fails on any bit mismatch for `validated: false` sites; for `validated: true`
sites a mismatch is a *regression* and also fails. Must emit `SKIP (no retail image)` and a
non-zero-safe marker that the release checklist treats as **not green**.

Additional guard rail: both gates must run on the ladder (Linux x86-64 reference, Vulkan 1.1
strict, Android ARM64 build) even though the ladder cannot catch the pack family — running
them everywhere at least prevents the census from drifting between platforms.

**Testing style in this repo** for the scripts that accompany the gates: `tools/xbox360/`
`test_*.py` with a `main()` running asserts and exiting non-zero (see
`tools/xbox360/validate_status.py` usage in the docs-rewrite lane, and existing
`tools/xbox360/test_*.py`). The census validator should follow the same shape so the
existing CI invocation pattern picks it up unchanged.

---

## 7. Task list with acceptance criteria

**T1 — Locate the codegen log and enumerate.** Find or regenerate the preflight codegen log
(the evidence says it is outside Git). Extract every `at {:X}` from the `float16_4` warnings
and every `Unresolved … branch/call to 0x… from 0x…`. Acceptance: a committed census file
with **counts** and address lists; the doc's "unknown: number of sites" resolved.

**T2 — Resolve `0x826FF380`.** Decide, from the generated corpus, whether the address is
inside a generated function body (local-branch misclassification) or outside all functions
(undiscovered code); identify the `REX_FATAL` emission site (unit + function).
Acceptance: a committed note naming the case, the unit file, and the enclosing function; if
outside, the reachability chain that would reach it.

**T3 — Mark unvalidated emissions in the generated C++.** At `vector.cpp:1331`, in addition
to the warning, emit a comment marker into the generated source (e.g.
`// DRIFT: float16_4 unvalidated operands`). Acceptance: grepping the generated corpus finds
every warned site; no behaviour change; corpus diff limited to comments.

**T4 — Census the whole diagnostic surface.** The preflight line names two families; there
are likely more `REXCODEGEN_WARN` sites in `src/codegen/`. Enumerate every warning/error
name, classify it trap-vs-silent (as §1 does for `float16_4`), and extend §4's risk table.
Acceptance: a table in this doc listing every codegen diagnostic with severity class and
ladder detectability. This is the real measure of how much silent drift exists.

**T5 — Semantic differential harness** (§5). Acceptance: the reference decoder path is
`llvm-mc` or `objdump` (independent), the operand sweep includes the guard edges and IEEE
edges, and at least one real retail `float16_4` site is proven bit-identical or the
mismatch is captured as a bug.

**T6 — CI gates G1/G2** (§6) wired into the existing workflow, with the `SKIP`-is-not-green
rule documented in `PROCESS_INSTRUCTIONS.md` by the docs lane.

**T7 — Fix whatever T5 finds.** Only after a proven mismatch. Until then no translator
change to `float16_4` — tightening the formula speculatively would replace one unverified
implementation with another.

---

## 8. Open unknowns (explicit)

1. Number and addresses of `float16_4` sites in the retail image (evidence has counts)
   — T1.
2. Whether the emitted formula is *wrong* or merely *unvalidated* for the operands that
   trip the guard — T5.
3. The PPC instruction identity of the `pk … float16_4` form (decoder lookup) — §1.2.
4. Whether `0x826FF380` is inside a generated function or in undiscovered code — T2.
5. Whether the affected functions are reachable from `xstart` (static sets) — §3.1.
6. Whether the repo content policy permits committing 16-byte retail instruction windows
   as test fixtures — §5.
7. Whether any `float16_4` site is on the render path (couples to P2) — unknown.

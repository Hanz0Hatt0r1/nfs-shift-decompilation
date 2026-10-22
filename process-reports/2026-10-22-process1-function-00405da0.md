# Process 1 — retail function 0x00405DA0: MWL::SMS::cGameApp::ProcessEventQueue

**Date:** 2026-10-22. **Binary:** Need for Speed Shift PC retail 1.02, PE32, ImageBase 0x00400000.  
**SHA-256 (verified against supplied SHIFT.exe):** eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1.  
**Sources:** retail SHIFT.exe, complete SHIFT_objdump_full.txt, exact v757 runtime evidence supplied in task. Runtime was *not* rerun for this report. No source, runtime, field, or graphics-file modifications; no PR.

## 1. Main conclusion and runtime limitations

**0x00405DA0 is the retail event-queue consumer \`MWL::SMS::cGameApp::ProcessEventQueue\`**. The identification is unusually strong: the original ASCII string at **0x00AAA7B0** is exactly \`MWL::SMS::cGameApp::ProcessEventQueue\`; its address is supplied at **0x00405DD6** and subsequently in every event logging path. At **0x00AAA7D8** is \`App has recieved a message QueueID:%d EventType:%d\` (original spelling \`recieved\`). The code dispatches decoded events from a queue argument, executes named callbacks, releases each event, and repeats until the next pop returns NULL.

**A returning EAX=0 does *not* prove that the queue was empty at entry.** A direct empty-first-pop returns 0, but a successful finite drain also ends with a final failed pop setting EAX=0 at **0x004062EF–0x00406304**. Consequently v757's **585 calls, all returning EAX=0**, cannot by itself distinguish (a) 585 empty polls from (b) some nonempty drains. A trace at the first pop would distinguish them.

The supplied v757 evidence is bounded: 120 host frames, exit 0, \`validation_errors=0\`; 6,457 non-truncated guest call events; 585 calls to 0x00405DA0, all caller 0x0040BA50 with ECX=0x00BBF960 and stack arg 0x00BBFF80; 0x0040BA50 called by 0x00A69160, present on snapshot. Snapshot call chain 0x00A69160→0x0040BA50→0x0054BE00→0x0082F780→0x00853170. The count 585 is **not** one call per host frame; the call occurs in an updating loop. None of these runtime facts proves why a menu or Draw* call did not appear.

## 2. ABI, register/stack contract

- **ECX = game application object** (copied to EDI by **0x00405DA8**); this supplies callbacks and is *not* the event queue.
- **One DWORD stack argument [EBP+8] = pointer to queue object**. Loaded into ECX at **0x00405DAA** before virtual call, and again into ESI at **0x004062DB** for cleanup/re-poll. The target terminates **RET 4** at **0x00406304**, so it consumes one DWORD argument.
- **EDX inbound** unused as an explicit argument; overwritten with queue vtable slot or passed through nested calls. ABI consistent with MSVC x86 \`__thiscall\` + one stack parameter; exact source-language declaration not proven. EBP, ESI, EDI, EBX preserved; EBX pushed only after first non-null event.
- **EAX return** is 0 on all normal empty/fully drained exits, because the final \`queue.vtable+4\` call returns NULL and nothing subsequently modifies EAX before RET. Do not interpret this as a Boolean “handled nothing.” No separate processed-event count is returned.
- **Local [EBP-4]** holds current event pointer to be released through \`0x004C7150\`; **[EBP-8]** stores decoded event family byte for outer dispatch.
- The original caller **0x0040BA50** takes ECX=application \`0x00BBF960\`, at **0x0040BA64** computes \`app+0x620\`, at **0x0040BABA** pushes that pointer and **0x0040BABD** directly calls \`0x00405DA0\`. Hence the supplied runtime queue pointer **0x00BBF960+0x620=0x00BBFF80** is fully consistent with the retail static callsite. This is a **distinct** queue and receiver from the earlier 0x00BE2510 container; the latter is irrelevant to interpreting this event loop.

## 3. Meaning of the first virtual call and the queue internals

At **0x00405DAA–0x00405DBB**:

~~~asm
00405daa mov ecx,[ebp+8]    ; queue
00405dad mov eax,[ecx]      ; queue vptr
00405daf mov edx,[eax+4]    ; slot +4
00405db2 call edx           ; ECX=queue, no stack args
00405db4 mov esi,eax        ; current event pointer or 0
00405db6 test esi,esi
00405dbb je 0x004062FF    ; empty on first read
~~~

From the constructor/destructor family: **0x00633320 at 0x0063332C** writes queue vptr **0x00AE BDBC** (written without spacing: **0x00AEBDBC**). Original \`.rdata\` DWORD at **0x00AEBDC0** (vtable offset +4) = **0x00633370**; slot 0 at **0x00AE BDBC** (0x00AEBDBC) = **0x00633660**. This **resolves** the virtual method for the ordinary queue class; virtual dispatch remains dependent on the actual runtime vptr.

**0x00633370** invokes **0x006500E0** at **0x006333B3**, passing ECX=queue, EDX=&temporary record. **0x006500E0** at **0x0065011A–0x00650139** returns AL=0 if \`[queue+0xB4]==0\` (no head). If there is a head, **0x0065013A–0x0065014F** unlinks the head from the doubly linked structure: \`[queue+0xB4]=oldHead+0x1C\`, update newHead+0x18 or clear tail \`[queue+0xB8]\`. At **0x00650152–0x00650171** it copies five DWORDs of the removed record into the caller's temporary buffer and performs container-related cleanup. At **0x006333BC–0x006333E8**, the vtable getter returns the DWORD from its local temporary record at **[EBP-0x18]** (third copied DWORD) or zero if extraction failed. **This returned DWORD is the pointer interpreted by 0x00405DA0 as the event object.** The complete identity of the record-wrapper fields outside those accessed remains a separate reconstruction.

Thus slot +4 is **destructive dequeue/pop**, not a pure count query, peek-only getter or renderer draw. On the normal exit 0x004062DB–0x004062F8, the consumer first calls \`0x004C7150(queue,&currentEvent)\` to destroy/release the previously consumed event, then invokes slot +4 again for the next.

**0x004C7150**: **0x004C7186** loads \`currentEvent=[EDX]\`; if nonzero, at **0x004C718C–0x004C7192** invokes event's own vtable slot 0 with pushed **0**, then invokes **0x00632FB0** with ECX=queue and EDX=event at **0x004C7198**, and zeroes \`*EDX\` at **0x004C719D**. Do not conflate this event cleanup with the earlier destructive dequeue from 0x006500E0.

### Event byte layout used by this function

- **event+0x00**: first DWORD is an object vptr, used by cleanup callback in 0x004C7150.
- **event+0x04**: a DWORD read on **0x00405DC6**, masked by \`0xFF\`; only the **low BYTE** is the sub-event/code (\`QueueID\` in log).
- **event+0x05**: the **next byte of that same DWORD**, zero-extended at **0x00405DC2**; this drives **event-family dispatch** (\`EventType\` in log).
- Other event fields may exist; the consumer itself passes the whole event pointer to selected callbacks, which may access more fields. These names reflect exact log strings; broader enum declarations are not available.

## 4. Main branch selection and all three jump tables

**Logging:** **0x00405DCF–0x00405DF2** always logs an event's code/family via **0x008F3DF0** before dispatch if the event pointer is nonzero, with format string \`App has recieved a message QueueID:%d EventType:%d\` and name string \`MWL::SMS::cGameApp::ProcessEventQueue\`. The common logger uses global **[0x00BE47E8]+0x2A0**. Logger results are ignored. Subsequent branches log individual named events with adjacent ASCII strings.

**Outer family switch** (**0x00405DF8–0x00405E0D**):
- family **0** -> **0x00406110**: NetLink event, sub-code interpreted as 5–15, table C.
- family **7** -> **0x00405F8E**: Matchmaker event, sub-code 1–8, table B.
- family **8** -> **0x00405E13**: Application event, sub-code 0–6, table A.
- any other family -> **0x004062DB** cleanup and next event, no named callback here.

All three decoded jump tables reside *after* the function at **0x00406308+**. objdump -D may misrepresent those bytes as executable instructions. The following is based on actual little-endian DWORDs from SHIFT.exe .text and is **data**, not code:

**Table A** \`0x00406308–0x00406323\`, 7 entries for family 8, codes 0..6:
\`[0x00405E45, 0x00405E74, 0x00405EA2, 0x00405ED1, 0x00405F00, 0x00405F2E, 0x00405F5E]\`.

| Event family 8 code | Retail branch | Exact log label | Direct callback |
| ---: | --- | --- | --- |
| 0 | 0x00405E45 | eEvent_EnterRace | 0x00404BF0 (ECX=app, no explicit stack arg) |
| 1 | 0x00405E74 | eEvent_ClientEnterRace | 0x00405330 (ECX=app, push event pointer) |
| 2 | 0x00405EA2 | eEvent_GUILanguageChange | 0x00403DF0 (ECX=app, no explicit stack arg) |
| 3 | 0x00405ED1 | eEvent_EnterMainMenu | 0x00403C60 (ECX=app, no explicit stack arg) |
| 4 | 0x00405F00 | eEvent_MPTeamManagerUpdate | 0x00405CD0 (ECX=app, push event pointer) |
| 5 | 0x00405F2E | eEvent_MPTeamManagerTagName | 0x00405D60 (ECX=app, push event pointer) |
| 6 | 0x00405F5E | eEvent_MPTextChat | 0x00404950 (ECX=app, push event pointer) |

**Table B** \`0x00406324–0x00406343\`, 8 entries for family 7, codes 1..8:
\`[0x00405FC2, 0x00405FCC, 0x00405FFC, 0x0040602A, 0x004060B8, 0x0040605A, 0x0040608A, 0x004060E8]\`. The code executes **EBX=eventCode-1** on **0x00405FAC**; unsigned \`EBX<=7\` check at **0x00405FB2–0x00405FB5**.

| Family 7 code | Branch | Exact log label | Callback |
| ---: | --- | --- | --- |
| 1 | 0x00405FC2 | eMatchmakerEvent_ReplayDataIsReady | Log only, jumps to shared log block 0x00406149 |
| 2 | 0x00405FCC | eMatchmakerEvent_InviteRecieved | 0x00404100 (ECX=app, push event) |
| 3 | 0x00405FFC | eMatchmakerEvent_InviteAccepted | 0x00404130 (ECX=app, push event) |
| 4 | 0x0040602A | eMatchmakerEvent_InviteDeclined | 0x00404160 (ECX=app, push event) |
| 5 | 0x004060B8 | eMatchmakerEvent_InviteCanceled | 0x00404190 (ECX=app, push event) |
| 6 | 0x0040605A | eMatchmakerEvent_InviteIgnored | 0x004041C0 (ECX=app, push event) |
| 7 | 0x0040608A | eMatchmakerEvent_InviteTimedOut | 0x004041F0 (ECX=app, push event) |
| 8 | 0x004060E8 | eMatchmakerEvent_FriendListUpdated | Log only; shared cleanup |

**Table C** \`0x00406344–0x0040636F\`, 11 entries for family 0, codes 5..15:
\`[0x00406258, 0x00406144, 0x0040616C, 0x0040619C, 0x004061CA, 0x004061FA, 0x0040622A, 0x004062DB, 0x004062DB, 0x00406285, 0x004062B2]\`. Subtracts **5** on **0x0040612E**; unsigned \`code-5<=10\` check at **0x00406134–0x00406137**.

| Family 0 code | Branch | Exact log label | Callback |
| ---: | --- | --- | --- |
| 5 | 0x00406258 | eNetLinkEvent_SessionEnded | 0x00403F20 (ECX=app, push event) |
| 6 | 0x00406144 | eNetLinkEvent_TextChat | Log only, common block |
| 7 | 0x0040616C | eNetLinkEvent_NodeAdded | 0x00405470 (ECX=app, push event) |
| 8 | 0x0040619C | eNetLinkEvent_NodeRemoved | 0x00404410 (ECX=app, push event) |
| 9 | 0x004061CA | eNetLinkEvent_VirtualHostMigration | 0x00405720 (ECX=app, push event) |
| 10 | 0x004061FA | eNetLinkEvent_PlatinumTrophyUnlocked | 0x004043A0 (ECX=app, push event) |
| 11 | 0x0040622A | eNetLinkEvent_AppApplyEntitlement | 0x00403E90 (ECX=app, push event) |
| 12 | 0x004062DB | no log label here | no callback; cleanup |
| 13 | 0x004062DB | no log label here | no callback; cleanup |
| 14 | 0x00406285 | eNetLinkEvent_LiveryTransfer | 0x00404850 (ECX=app, push event) |
| 15 | 0x004062B2 | eNetLinkEvent_DisconnectionMessage | 0x00404220 (ECX=app, push event) |

For all families, out-of-range codes fall through to **0x004062DB**. Callback names above are intentionally given as **addresses and log-associated labels**, not fabricated C++ symbol identities; handlers' deeper side effects are not fully established by this function alone.

## 5. Consumer loop and who can enqueue

**0x004062DB–0x00406304:** after any recognized/unrecognized non-null event, load queue from [EBP+8]; call \`0x004C7150(queue,&localEvent)\` at **0x004062E3**, then call queue's **vtable+4** again at **0x004062EF**. Store EAX in ESI and local; repeat from **0x00405DC2** while nonzero. There is no per-call upper bound on events processed. A callback is permitted to mutate the queue; the next pop observes its updated state. Returning EAX=0 means the *last* pop failed, not that no callbacks ran.

### Identified event creation / producer routes

- **Concrete route for main-menu event:** **0x004052B0** is a direct producer candidate taking **ECX=app**. At **0x004052B5**, it computes \`queue=app+0x620\`; at **0x004052C2** it invokes \`0x0045B530\` to obtain an event object, tests AL. On success **0x004052D0** writes **BYTE [event+5]=8**, **0x004052D4** writes **BYTE [event+4]=3**, matching family 8 / code 3 (\`eEvent_EnterMainMenu\`). It passes ECX=queue and EDX=event to **0x004049D0** on **0x004052D8**. If that call returns false, **0x004052ED** calls \`0x004C7150\` for cleanup. This is an exact *code path capable of attempting* to produce the desired event, **not proof it ran in v757**.
- **Concrete route for enter-race event:** **0x00405C1E–0x00405C65** computes queue as owner+0x620, calls \`0x0045B530\`, then writes event+5=8, event+4=0 at **0x00405C5D–0x00405C61**, invokes \`0x004049D0\` at **0x00405C65**. This corresponds to family 8/code 0.
- **Queue insertion mechanism:** **0x004049D0** (and a sibling **0x0040B680**) checks queue settings/initialized flag \`queue+0x25C\`, may route through \`0x00632FE0\` and **0x0045B530/0x0040B5C0\`**, and on reachable paths calls **0x006333F0(queue, EDX=0, stack event*)** (e.g. **0x00404A4F**, **0x00404AB0**, **0x0040B6FF**, **0x0040B760**). **0x006333F0** links event records into the queue, operating with head/tail fields \`queue+0xB4/+0xB8\`, record link fields \`+0x18/+0x1C\`, and ordering/priority-related field \`event+0x08\` (e.g. **0x00633454–0x006334C0**).
- **Initialization / registration:** at **0x0040D754** owner+0x620 becomes ECX for **0x00632E30** (0x0040D763), then at **0x0040D779–0x0040D77B** calls **0x006335F0** on the same queue. At **0x0040A9EF–0x0040A9F5** a cleanup path invokes **0x00633150(queue)**; at **0x0040A1D3–0x0040A1D9** invokes **0x00633320(queue)**. The vtable \`0x00AEBDBC\` is installed by the latter. This establishes a queue object lifecycle independent of the event-dispatch function.
- **Static callsite inventory:** \`0x00405DA0\` has a directly decoded \`CALL rel32\` at **0x0040BABD**. The sender helper \`0x004049D0\` has direct callsites **0x004052D8**, **0x00405C65**, **0x004623E2**. Other posting mechanisms via queue configuration, callbacks or indirect dispatch are not excluded. **0x004052B0 has no direct \`call rel32\` in the full objdump search**, so its upstream runtime reachability cannot be asserted from a simple direct-call lookup; it may be called through another mechanism.

These are independently anchored static relationships. We **cannot claim v757 created a menu event**, cannot count processed events from EAX, and cannot infer failure of render initialization from queue state.

## 6. Confidence ledger and one next trace target

**Directly proven by retail bytes:** register ABI and RET 4, app/queue pointer offsets, queue vtable slot +4 entry and pop behavior (for ordinary queue vptr), on-empty EAX=0, re-poll loop, family/code byte accesses and exact three jump tables, every listed logger/callback address and argument-push shape, cleanup call, producer *code path* for family8/code3, queue link helper and initialization/cleanup addresses.

**Runtime-observed (only as supplied):** v757's 585 invocations from 0x0040BA50, ECX=0x00BBF960, arg=0x00BBFF80, every terminal EAX=0, 6,457 guest trace events, bounded 120-frame run and active snapshot chain. These events do not reveal *initial* pop values, actual callback counts, or producer execution in this run.

**Hypotheses / unknown:** specific original enum declaration apart from embedded log labels, semantics of queue scheduling/priority bits, occurrence of any particular event in v757, source of missing menu/draw, complete downstream side effects of callbacks; no causal assertion based solely on snapshot/EAX=0.

**Exactly one next retail trace address: \`0x004052B0\`.** This is the most targeted candidate for **production of the \`eEvent_EnterMainMenu\` event (family8/code3)**. Trace its entry, event allocation return, writes at 0x004052D0/0x004052D4 and \`0x004049D0\` AL on 0x004052D8; record whether the code actually reaches the queue consumer. This is a trace recommendation, *not* a requested runtime patch or field forcing.

## 7. Complete original objdump block 0x00405DA0–0x00406304

The block below is all executable instructions of the given retail function, unabridged. **0x00406308+ is jump-table data**, decoded above and excluded from the executable block. 0x00406307 is NOP padding.

~~~asm
00405da0: 55                    push ebp
00405da1: 8b ec                 mov ebp,esp
00405da3: 83 ec 08              sub esp,0x8
00405da6: 56                    push esi
00405da7: 57                    push edi
00405da8: 8b f9                 mov edi,ecx
00405daa: 8b 4d 08              mov ecx,DWORD PTR [ebp+0x8]
00405dad: 8b 01                 mov eax,DWORD PTR [ecx]
00405daf: 8b 50 04              mov edx,DWORD PTR [eax+0x4]
00405db2: ff d2                 call edx
00405db4: 8b f0                 mov esi,eax
00405db6: 85 f6                 test esi,esi
00405db8: 89 75 fc              mov DWORD PTR [ebp-0x4],esi
00405dbb: 0f 84 3e 05 00 00     je 0x4062ff
00405dc1: 53                    push ebx
00405dc2: 0f b6 46 05           movzx eax,BYTE PTR [esi+0x5]
00405dc6: 8b 5e 04              mov ebx,DWORD PTR [esi+0x4]
00405dc9: 81 e3 ff 00 00 00     and ebx,0xff
00405dcf: 53                    push ebx
00405dd0: 50                    push eax
00405dd1: 68 d8 a7 aa 00        push 0xaaa7d8
00405dd6: 68 b0 a7 aa 00        push 0xaaa7b0
00405ddb: 89 45 f8              mov DWORD PTR [ebp-0x8],eax
00405dde: a1 e8 47 be 00        mov eax,ds:0xbe47e8
00405de3: 6a 04                 push 0x4
00405de5: 05 a0 02 00 00        add eax,0x2a0
00405dea: 6a 00                 push 0x0
00405dec: 50                    push eax
00405ded: e8 fe df 4e 00        call 0x8f3df0
00405df2: 8b 45 f8              mov eax,DWORD PTR [ebp-0x8]
00405df5: 83 c4 1c              add esp,0x1c
00405df8: 83 e8 00              sub eax,0x0
00405dfb: 0f 84 0f 03 00 00     je 0x406110
00405e01: 83 e8 07              sub eax,0x7
00405e04: 0f 84 84 01 00 00     je 0x405f8e
00405e0a: 83 e8 01              sub eax,0x1
00405e0d: 0f 85 c8 04 00 00     jne 0x4062db
00405e13: 8b 0d e8 47 be 00     mov ecx,DWORD PTR ds:0xbe47e8
00405e19: 68 98 a7 aa 00        push 0xaaa798
00405e1e: 68 b0 a7 aa 00        push 0xaaa7b0
00405e23: 6a 04                 push 0x4
00405e25: 50                    push eax
00405e26: 81 c1 a0 02 00 00     add ecx,0x2a0
00405e2c: 51                    push ecx
00405e2d: e8 be df 4e 00        call 0x8f3df0
00405e32: 83 c4 14              add esp,0x14
00405e35: 83 fb 06              cmp ebx,0x6
00405e38: 0f 87 9d 04 00 00     ja 0x4062db
00405e3e: ff 24 9d 08 63 40 00  jmp DWORD PTR [ebx*4+0x406308]
00405e45: 8b 15 e8 47 be 00     mov edx,DWORD PTR ds:0xbe47e8
00405e4b: 68 78 a7 aa 00        push 0xaaa778
00405e50: 68 b0 a7 aa 00        push 0xaaa7b0
00405e55: 6a 04                 push 0x4
00405e57: 81 c2 a0 02 00 00     add edx,0x2a0
00405e5d: 6a 00                 push 0x0
00405e5f: 52                    push edx
00405e60: e8 8b df 4e 00        call 0x8f3df0
00405e65: 83 c4 14              add esp,0x14
00405e68: 8b cf                 mov ecx,edi
00405e6a: e8 81 ed ff ff        call 0x404bf0
00405e6f: e9 67 04 00 00        jmp 0x4062db
00405e74: a1 e8 47 be 00        mov eax,ds:0xbe47e8
00405e79: 68 54 a7 aa 00        push 0xaaa754
00405e7e: 68 b0 a7 aa 00        push 0xaaa7b0
00405e83: 6a 04                 push 0x4
00405e85: 05 a0 02 00 00        add eax,0x2a0
00405e8a: 6a 00                 push 0x0
00405e8c: 50                    push eax
00405e8d: e8 5e df 4e 00        call 0x8f3df0
00405e92: 83 c4 14              add esp,0x14
00405e95: 56                    push esi
00405e96: 8b cf                 mov ecx,edi
00405e98: e8 93 f4 ff ff        call 0x405330
00405e9d: e9 39 04 00 00        jmp 0x4062db
00405ea2: 8b 0d e8 47 be 00     mov ecx,DWORD PTR ds:0xbe47e8
00405ea8: 68 2c a7 aa 00        push 0xaaa72c
00405ead: 68 b0 a7 aa 00        push 0xaaa7b0
00405eb2: 6a 04                 push 0x4
00405eb4: 81 c1 a0 02 00 00     add ecx,0x2a0
00405eba: 6a 00                 push 0x0
00405ebc: 51                    push ecx
00405ebd: e8 2e df 4e 00        call 0x8f3df0
00405ec2: 83 c4 14              add esp,0x14
00405ec5: 8b cf                 mov ecx,edi
00405ec7: e8 24 df ff ff        call 0x403df0
00405ecc: e9 0a 04 00 00        jmp 0x4062db
00405ed1: 8b 15 e8 47 be 00     mov edx,DWORD PTR ds:0xbe47e8
00405ed7: 68 08 a7 aa 00        push 0xaaa708
00405edc: 68 b0 a7 aa 00        push 0xaaa7b0
00405ee1: 6a 04                 push 0x4
00405ee3: 81 c2 a0 02 00 00     add edx,0x2a0
00405ee9: 6a 00                 push 0x0
00405eeb: 52                    push edx
00405eec: e8 ff de 4e 00        call 0x8f3df0
00405ef1: 83 c4 14              add esp,0x14
00405ef4: 8b cf                 mov ecx,edi
00405ef6: e8 65 dd ff ff        call 0x403c60
00405efb: e9 db 03 00 00        jmp 0x4062db
00405f00: a1 e8 47 be 00        mov eax,ds:0xbe47e8
00405f05: 68 e0 a6 aa 00        push 0xaaa6e0
00405f0a: 68 b0 a7 aa 00        push 0xaaa7b0
00405f0f: 6a 04                 push 0x4
00405f11: 05 a0 02 00 00        add eax,0x2a0
00405f16: 6a 00                 push 0x0
00405f18: 50                    push eax
00405f19: e8 d2 de 4e 00        call 0x8f3df0
00405f1e: 83 c4 14              add esp,0x14
00405f21: 56                    push esi
00405f22: 8b cf                 mov ecx,edi
00405f24: e8 a7 fd ff ff        call 0x405cd0
00405f29: e9 ad 03 00 00        jmp 0x4062db
00405f2e: 8b 0d e8 47 be 00     mov ecx,DWORD PTR ds:0xbe47e8
00405f34: 68 b8 a6 aa 00        push 0xaaa6b8
00405f39: 68 b0 a7 aa 00        push 0xaaa7b0
00405f3e: 6a 04                 push 0x4
00405f40: 81 c1 a0 02 00 00     add ecx,0x2a0
00405f46: 6a 00                 push 0x0
00405f48: 51                    push ecx
00405f49: e8 a2 de 4e 00        call 0x8f3df0
00405f4e: 83 c4 14              add esp,0x14
00405f51: 56                    push esi
00405f52: 8b cf                 mov ecx,edi
00405f54: e8 07 fe ff ff        call 0x405d60
00405f59: e9 7d 03 00 00        jmp 0x4062db
00405f5e: 8b 15 e8 47 be 00     mov edx,DWORD PTR ds:0xbe47e8
00405f64: 68 98 a6 aa 00        push 0xaaa698
00405f69: 68 b0 a7 aa 00        push 0xaaa7b0
00405f6e: 6a 04                 push 0x4
00405f70: 81 c2 a0 02 00 00     add edx,0x2a0
00405f76: 6a 00                 push 0x0
00405f78: 52                    push edx
00405f79: e8 72 de 4e 00        call 0x8f3df0
00405f7e: 83 c4 14              add esp,0x14
00405f81: 56                    push esi
00405f82: 8b cf                 mov ecx,edi
00405f84: e8 c7 e9 ff ff        call 0x404950
00405f89: e9 4d 03 00 00        jmp 0x4062db
00405f8e: a1 e8 47 be 00        mov eax,ds:0xbe47e8
00405f93: 68 84 a6 aa 00        push 0xaaa684
00405f98: 68 b0 a7 aa 00        push 0xaaa7b0
00405f9d: 6a 04                 push 0x4
00405f9f: 05 a0 02 00 00        add eax,0x2a0
00405fa4: 6a 00                 push 0x0
00405fa6: 50                    push eax
00405fa7: e8 44 de 4e 00        call 0x8f3df0
00405fac: 83 c3 ff              add ebx,0xffffffff
00405faf: 83 c4 14              add esp,0x14
00405fb2: 83 fb 07              cmp ebx,0x7
00405fb5: 0f 87 20 03 00 00     ja 0x4062db
00405fbb: ff 24 9d 24 63 40 00  jmp DWORD PTR [ebx*4+0x406324]
00405fc2: 68 54 a6 aa 00        push 0xaaa654
00405fc7: e9 7d 01 00 00        jmp 0x406149
00405fcc: 8b 15 e8 47 be 00     mov edx,DWORD PTR ds:0xbe47e8
00405fd2: 68 28 a6 aa 00        push 0xaaa628
00405fd7: 68 b0 a7 aa 00        push 0xaaa7b0
00405fdc: 6a 04                 push 0x4
00405fde: 81 c2 a0 02 00 00     add edx,0x2a0
00405fe4: 6a 00                 push 0x0
00405fe6: 52                    push edx
00405fe7: e8 04 de 4e 00        call 0x8f3df0
00405fec: 83 c4 14              add esp,0x14
00405fef: 56                    push esi
00405ff0: 8b cf                 mov ecx,edi
00405ff2: e8 09 e1 ff ff        call 0x404100
00405ff7: e9 df 02 00 00        jmp 0x4062db
00405ffc: a1 e8 47 be 00        mov eax,ds:0xbe47e8
00406001: 68 fc a5 aa 00        push 0xaaa5fc
00406006: 68 b0 a7 aa 00        push 0xaaa7b0
0040600b: 6a 04                 push 0x4
0040600d: 05 a0 02 00 00        add eax,0x2a0
00406012: 6a 00                 push 0x0
00406014: 50                    push eax
00406015: e8 d6 dd 4e 00        call 0x8f3df0
0040601a: 83 c4 14              add esp,0x14
0040601d: 56                    push esi
0040601e: 8b cf                 mov ecx,edi
00406020: e8 0b e1 ff ff        call 0x404130
00406025: e9 b1 02 00 00        jmp 0x4062db
0040602a: 8b 0d e8 47 be 00     mov ecx,DWORD PTR ds:0xbe47e8
00406030: 68 d0 a5 aa 00        push 0xaaa5d0
00406035: 68 b0 a7 aa 00        push 0xaaa7b0
0040603a: 6a 04                 push 0x4
0040603c: 81 c1 a0 02 00 00     add ecx,0x2a0
00406042: 6a 00                 push 0x0
00406044: 51                    push ecx
00406045: e8 a6 dd 4e 00        call 0x8f3df0
0040604a: 83 c4 14              add esp,0x14
0040604d: 56                    push esi
0040604e: 8b cf                 mov ecx,edi
00406050: e8 0b e1 ff ff        call 0x404160
00406055: e9 81 02 00 00        jmp 0x4062db
0040605a: 8b 15 e8 47 be 00     mov edx,DWORD PTR ds:0xbe47e8
00406060: 68 a4 a5 aa 00        push 0xaaa5a4
00406065: 68 b0 a7 aa 00        push 0xaaa7b0
0040606a: 6a 04                 push 0x4
0040606c: 81 c2 a0 02 00 00     add edx,0x2a0
00406072: 6a 00                 push 0x0
00406074: 52                    push edx
00406075: e8 76 dd 4e 00        call 0x8f3df0
0040607a: 83 c4 14              add esp,0x14
0040607d: 56                    push esi
0040607e: 8b cf                 mov ecx,edi
00406080: e8 3b e1 ff ff        call 0x4041c0
00406085: e9 51 02 00 00        jmp 0x4062db
0040608a: a1 e8 47 be 00        mov eax,ds:0xbe47e8
0040608f: 68 78 a5 aa 00        push 0xaaa578
00406094: 68 b0 a7 aa 00        push 0xaaa7b0
00406099: 6a 04                 push 0x4
0040609b: 05 a0 02 00 00        add eax,0x2a0
004060a0: 6a 00                 push 0x0
004060a2: 50                    push eax
004060a3: e8 48 dd 4e 00        call 0x8f3df0
004060a8: 83 c4 14              add esp,0x14
004060ab: 56                    push esi
004060ac: 8b cf                 mov ecx,edi
004060ae: e8 3d e1 ff ff        call 0x4041f0
004060b3: e9 23 02 00 00        jmp 0x4062db
004060b8: 8b 0d e8 47 be 00     mov ecx,DWORD PTR ds:0xbe47e8
004060be: 68 4c a5 aa 00        push 0xaaa54c
004060c3: 68 b0 a7 aa 00        push 0xaaa7b0
004060c8: 6a 04                 push 0x4
004060ca: 81 c1 a0 02 00 00     add ecx,0x2a0
004060d0: 6a 00                 push 0x0
004060d2: 51                    push ecx
004060d3: e8 18 dd 4e 00        call 0x8f3df0
004060d8: 83 c4 14              add esp,0x14
004060db: 56                    push esi
004060dc: 8b cf                 mov ecx,edi
004060de: e8 ad e0 ff ff        call 0x404190
004060e3: e9 f3 01 00 00        jmp 0x4062db
004060e8: 8b 15 e8 47 be 00     mov edx,DWORD PTR ds:0xbe47e8
004060ee: 68 1c a5 aa 00        push 0xaaa51c
004060f3: 68 b0 a7 aa 00        push 0xaaa7b0
004060f8: 6a 04                 push 0x4
004060fa: 81 c2 a0 02 00 00     add edx,0x2a0
00406100: 6a 00                 push 0x0
00406102: 52                    push edx
00406103: e8 e8 dc 4e 00        call 0x8f3df0
00406108: 83 c4 14              add esp,0x14
0040610b: e9 cb 01 00 00        jmp 0x4062db
00406110: a1 e8 47 be 00        mov eax,ds:0xbe47e8
00406115: 68 0c a5 aa 00        push 0xaaa50c
0040611a: 68 b0 a7 aa 00        push 0xaaa7b0
0040611f: 6a 04                 push 0x4
00406121: 05 a0 02 00 00        add eax,0x2a0
00406126: 6a 00                 push 0x0
00406128: 50                    push eax
00406129: e8 c2 dc 4e 00        call 0x8f3df0
0040612e: 83 c3 fb              add ebx,0xfffffffb
00406131: 83 c4 14              add esp,0x14
00406134: 83 fb 0a              cmp ebx,0xa
00406137: 0f 87 9e 01 00 00     ja 0x4062db
0040613d: ff 24 9d 44 63 40 00  jmp DWORD PTR [ebx*4+0x406344]
00406144: 68 e8 a4 aa 00        push 0xaaa4e8
00406149: 8b 0d e8 47 be 00     mov ecx,DWORD PTR ds:0xbe47e8
0040614f: 68 b0 a7 aa 00        push 0xaaa7b0
00406154: 6a 04                 push 0x4
00406156: 81 c1 a0 02 00 00     add ecx,0x2a0
0040615c: 6a 00                 push 0x0
0040615e: 51                    push ecx
0040615f: e8 8c dc 4e 00        call 0x8f3df0
00406164: 83 c4 14              add esp,0x14
00406167: e9 6f 01 00 00        jmp 0x4062db
0040616c: 8b 15 e8 47 be 00     mov edx,DWORD PTR ds:0xbe47e8
00406172: 68 c4 a4 aa 00        push 0xaaa4c4
00406177: 68 b0 a7 aa 00        push 0xaaa7b0
0040617c: 6a 04                 push 0x4
0040617e: 81 c2 a0 02 00 00     add edx,0x2a0
00406184: 6a 00                 push 0x0
00406186: 52                    push edx
00406187: e8 64 dc 4e 00        call 0x8f3df0
0040618c: 83 c4 14              add esp,0x14
0040618f: 56                    push esi
00406190: 8b cf                 mov ecx,edi
00406192: e8 d9 f2 ff ff        call 0x405470
00406197: e9 3f 01 00 00        jmp 0x4062db
0040619c: a1 e8 47 be 00        mov eax,ds:0xbe47e8
004061a1: 68 9c a4 aa 00        push 0xaaa49c
004061a6: 68 b0 a7 aa 00        push 0xaaa7b0
004061ab: 6a 04                 push 0x4
004061ad: 05 a0 02 00 00        add eax,0x2a0
004061b2: 6a 00                 push 0x0
004061b4: 50                    push eax
004061b5: e8 36 dc 4e 00        call 0x8f3df0
004061ba: 83 c4 14              add esp,0x14
004061bd: 56                    push esi
004061be: 8b cf                 mov ecx,edi
004061c0: e8 4b e2 ff ff        call 0x404410
004061c5: e9 11 01 00 00        jmp 0x4062db
004061ca: 8b 0d e8 47 be 00     mov ecx,DWORD PTR ds:0xbe47e8
004061d0: 68 6c a4 aa 00        push 0xaaa46c
004061d5: 68 b0 a7 aa 00        push 0xaaa7b0
004061da: 6a 04                 push 0x4
004061dc: 81 c1 a0 02 00 00     add ecx,0x2a0
004061e2: 6a 00                 push 0x0
004061e4: 51                    push ecx
004061e5: e8 06 dc 4e 00        call 0x8f3df0
004061ea: 83 c4 14              add esp,0x14
004061ed: 56                    push esi
004061ee: 8b cf                 mov ecx,edi
004061f0: e8 2b f5 ff ff        call 0x405720
004061f5: e9 e1 00 00 00        jmp 0x4062db
004061fa: 8b 15 e8 47 be 00     mov edx,DWORD PTR ds:0xbe47e8
00406200: 68 38 a4 aa 00        push 0xaaa438
00406205: 68 b0 a7 aa 00        push 0xaaa7b0
0040620a: 6a 04                 push 0x4
0040620c: 81 c2 a0 02 00 00     add edx,0x2a0
00406212: 6a 00                 push 0x0
00406214: 52                    push edx
00406215: e8 d6 db 4e 00        call 0x8f3df0
0040621a: 83 c4 14              add esp,0x14
0040621d: 56                    push esi
0040621e: 8b cf                 mov ecx,edi
00406220: e8 7b e1 ff ff        call 0x4043a0
00406225: e9 b1 00 00 00        jmp 0x4062db
0040622a: a1 e8 47 be 00        mov eax,ds:0xbe47e8
0040622f: 68 08 a4 aa 00        push 0xaaa408
00406234: 68 b0 a7 aa 00        push 0xaaa7b0
00406239: 6a 04                 push 0x4
0040623b: 05 a0 02 00 00        add eax,0x2a0
00406240: 6a 00                 push 0x0
00406242: 50                    push eax
00406243: e8 a8 db 4e 00        call 0x8f3df0
00406248: 83 c4 14              add esp,0x14
0040624b: 56                    push esi
0040624c: 8b cf                 mov ecx,edi
0040624e: e8 3d dc ff ff        call 0x403e90
00406253: e9 83 00 00 00        jmp 0x4062db
00406258: 8b 0d e8 47 be 00     mov ecx,DWORD PTR ds:0xbe47e8
0040625e: 68 e0 a3 aa 00        push 0xaaa3e0
00406263: 68 b0 a7 aa 00        push 0xaaa7b0
00406268: 6a 04                 push 0x4
0040626a: 81 c1 a0 02 00 00     add ecx,0x2a0
00406270: 6a 00                 push 0x0
00406272: 51                    push ecx
00406273: e8 78 db 4e 00        call 0x8f3df0
00406278: 83 c4 14              add esp,0x14
0040627b: 56                    push esi
0040627c: 8b cf                 mov ecx,edi
0040627e: e8 9d dc ff ff        call 0x403f20
00406283: eb 56                 jmp 0x4062db
00406285: 8b 15 e8 47 be 00     mov edx,DWORD PTR ds:0xbe47e8
0040628b: 68 b4 a3 aa 00        push 0xaaa3b4
00406290: 68 b0 a7 aa 00        push 0xaaa7b0
00406295: 6a 04                 push 0x4
00406297: 81 c2 a0 02 00 00     add edx,0x2a0
0040629d: 6a 00                 push 0x0
0040629f: 52                    push edx
004062a0: e8 4b db 4e 00        call 0x8f3df0
004062a5: 83 c4 14              add esp,0x14
004062a8: 56                    push esi
004062a9: 8b cf                 mov ecx,edi
004062ab: e8 a0 e5 ff ff        call 0x404850
004062b0: eb 29                 jmp 0x4062db
004062b2: a1 e8 47 be 00        mov eax,ds:0xbe47e8
004062b7: 68 84 a3 aa 00        push 0xaaa384
004062bc: 68 b0 a7 aa 00        push 0xaaa7b0
004062c1: 6a 04                 push 0x4
004062c3: 05 a0 02 00 00        add eax,0x2a0
004062c8: 6a 00                 push 0x0
004062ca: 50                    push eax
004062cb: e8 20 db 4e 00        call 0x8f3df0
004062d0: 83 c4 14              add esp,0x14
004062d3: 56                    push esi
004062d4: 8b cf                 mov ecx,edi
004062d6: e8 45 df ff ff        call 0x404220
004062db: 8b 75 08              mov esi,DWORD PTR [ebp+0x8]
004062de: 8d 55 fc              lea edx,[ebp-0x4]
004062e1: 8b ce                 mov ecx,esi
004062e3: e8 68 0e 0c 00        call 0x4c7150
004062e8: 8b 16                 mov edx,DWORD PTR [esi]
004062ea: 8b 42 04              mov eax,DWORD PTR [edx+0x4]
004062ed: 8b ce                 mov ecx,esi
004062ef: ff d0                 call eax
004062f1: 8b f0                 mov esi,eax
004062f3: 85 f6                 test esi,esi
004062f5: 89 75 fc              mov DWORD PTR [ebp-0x4],esi
004062f8: 0f 85 c4 fa ff ff     jne 0x405dc2
004062fe: 5b                    pop ebx
004062ff: 5f                    pop edi
00406300: 5e                    pop esi
00406301: 8b e5                 mov esp,ebp
00406303: 5d                    pop ebp
00406304: c2 04 00              ret 0x4
~~~

**Out-of-function data:** \`0x00406308–0x0040636F\` contains the three DWORD tables enumerated above; instructions printed there by indiscriminate \`objdump -D\` must not be treated as executable code.

# Process 1 — offline network import stubs (2026-10-21)

This change gives the imported socket, DNS, NetBIOS, and online-session APIs
deterministic offline failures so the guest can continue through paths that do
not require an online session. It does not implement networking, DNS, NetBIOS
transport, or SSPI/TLS. The original PC retail 1.02 `SHIFT.exe` used to
establish the import set has SHA-256
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

## Runtime behavior

- Winsock socket creation, connection, I/O, and option calls fail immediately;
  after successful `WSAStartup`, `WSAGetLastError` reports `WSAENETDOWN`
  (`10050`), and before startup it reports `WSANOTINITIALISED` (`10093`).
- Name resolution returns `WSAHOST_NOT_FOUND` (`11001`), with `getaddrinfo`
  clearing its output pointer. No host resolver or network socket is called.
- `Netbios` completes with `NRC_ENVNOTDEF` (`0x34`) in both the return value and
  the NCB status bytes. An async NCB signals a guest event when one was supplied.
- SSPI setup/record operations return `SEC_E_UNSUPPORTED_FUNCTION`
  (`0x80090302`); handle/buffer cleanup calls are harmless success no-ops.
- Winsock startup/cleanup, byte-order conversion, Winsock event creation,
  signaling, reset, close, and wait keep their guest compatibility behavior.
- Legacy WSOCK32 hostname/address calls fail locally; cancellation is a no-op.

The retail PE's network/session import coverage is WS2_32 ordinals `#1`–`#11`,
`#13`–`#23`, `#52`, `#57`, `#111`, `#115`, and `#116`, plus its named resolver,
receive, ioctl, event, and overlapped-result imports; all three WSOCK32 imports;
NETAPI32 `Netbios`; and the nine imported Secur32 SSPI APIs. The regression
fixture exercises representative imports and state transitions, not every
entry in that list.

The stubs are limited to network/session paths. The retail PE also imports
CRYPT32 certificate-chain/message APIs, WINTRUST, and ImageHlp certificate
enumeration APIs. This change does not stub or bypass those imports; their
call sites and relevance to the offline startup path have not been established.

## Verification

The synthetic PE32 regression fixture checks import mapping and representative
calls from WS2_32, WSOCK32, NETAPI32, and Secur32, including startup state,
offline errors, stack cleanup, resolver output clearing, NetBIOS completion,
SSPI failure, and guest event behavior. It is not a full retail import-table
execution.

- `shift_runtime` build: SHA-256
  `51f98a376ecfbe87aeaf4f94e3a3f7b7fd302da9ea6bf23bff4dcf947f7ea8eb`.
- Focused regression executable: SHA-256
  `7ece2fe1876036b5ad13c932c0606a6519171e5efbe94815aa8386593d731a7d`.
- `shift_runtime_recompiled_pcode_module` passed (1/1).
- `git diff --check` passed.

No fresh retail P-code replay was performed for this patch: the matching full
P-code module set needed by the existing retail-frontier runner was unavailable
in the searched evidence locations. The passing test therefore establishes
stub/import behavior only. It does not establish that this import surface is
reached in retail execution, that the frontend or race advances, or that online
features are supported. Host-frame and dispatch counts are not treated as proof
of game launch.

Machine-readable evidence: `evidence/retail_frontier_20261021/process1_offline_network_stubs_20261021.json`.

# Xbox 360 Linux guest-memory mapping lifecycle

Date: 2026-10-24

## Change under review

ReXGlue PR [#530](https://github.com/rexglue/rexglue-sdk/pull/530) adds an explicit POSIX unlink-after-open mode for process-local guest memory. The original four-argument `CreateFileMappingHandle` symbol and its named-mapping behavior remain available. `Memory::Initialize` opts into the private mode; an already-open descriptor remains usable for mapping views after its name is removed.

## Verification

- Built the Linux AMD64 Debug `unit_tests` and `rexglue` targets against ReXGlue `main` at v0.10.0.
- `unit_tests "[memory][posix]"`: 2 test cases, 10 assertions passed. One case verifies that the unnamed mapping remains usable; the other verifies that the default named mapping remains discoverable until close.
- `nm -D` confirmed both the original four-argument symbol and the new five-argument overload in the rebuilt runtime.
- A bounded Linux host run with the rebuilt runtime reached title shader-storage initialization and was stopped by an external timeout. One pre-existing orphan under `/dev/shm` remained unchanged; the run created no additional `xenia_memory_*` name.

## Relative shader-cache path observation

A separate GDB trace of the Linux host's `NtCreateFile` call found a request for `render\\shaders\\cache\\`. `VirtualFileSystem::OpenFile` received `root_entry=null`; the guest `OBJECT_ATTRIBUTES.RootDirectory` was the big-endian `0xFFFFFFFD` `ObDosDevices` sentinel, and the creation disposition was `FILE_OPEN` (`1`). The request returned `0xC000000F` (`STATUS_NO_SUCH_FILE`) because the VFS path had no device prefix. The PPC caller chain begins at `0x826EF1A0`, then `0x823FDCB0`, `0x8264A038`, and `0x82FBCFD8`.

This is evidence of a relative shader-cache open/probe. The trace does not show that this failure prevents menu or race progress, so it is not treated as a confirmed blocker or patched here. Static analysis of the complete caller body remains the next check.

## Limits

This smoke run does not demonstrate the retail main menu or an offline race. It used an older copied GPU plugin, so its renderer output is not evidence about the current Process 2 build. The change was built and tested on Linux AMD64; Android/ARM64 and Windows builds have not been verified here. No game files or private storage links are part of this evidence or the ReXGlue PR.

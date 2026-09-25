# Phase 226 — retail research input manifest

Phase 226 adds a compact identity-only manifest for the real local reverse-engineering
inputs. It records path, file name, byte size and SHA-256 for binaries/archives without
copying their contents into the repository.

Optional expected hashes turn known retail artifacts into strict intake checks. A
missing file or hash mismatch is a hard blocker.

This is intended for the Linux research workstation, not for CI artifacts containing
retail game binaries.

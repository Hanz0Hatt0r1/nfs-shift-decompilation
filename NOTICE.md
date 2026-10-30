# Attribution / research references

## Project license posture

Unless otherwise noted, project-authored source code is declared under
`GPL-3.0-only`; see `LICENSE`.

This is a conservative compliance choice based on the repository's documented
LZX provenance. The earliest `shift_importer.py` history currently retained in
this repository (`337c88aa3b1cbacc4869db3b336416ef623cdeab`) already contains the
pure-Python LZX decoder and states that the implementation follows the public
algorithm used by OpenAssetTools's LZX implementation and its documented XMem
framing behavior. Because that provenance does not support treating the current
LZX work as an unambiguously clean-room implementation independent of the GPL
reference implementation, the project does not rely on such a characterization
for licensing.

OpenAssetTools is distributed under GPLv3. Its referenced
`thirdparty/lzx/lzx.c` carries GPL-2.0-or-later terms inherited from the
Wine/cabextract lineage. `GPL-3.0-only` is used for project-authored code as a
conservative project-level licensing posture compatible with those referenced
GPL sources. This notice records provenance and licensing intent; it is not a
claim that every algorithmic similarity is independently copyrightable or that
all format knowledge is derived code.

The project license covers project source code only. It does not grant rights to
Need for Speed: SHIFT, Electronic Arts trademarks, retail executables, game
resources, or other third-party copyrighted assets. Those remain subject to
their respective rights holders' terms and are not distributed by this project.

## Research references

BFF extraction is cross-checked against the public QuickBMS `nfsshift.bms`
script for Need for Speed: SHIFT / Shift 2 / Project Cars. The project uses this
as a format-research reference; this notice does not claim ownership of that
script or relicense it.

XMem/LZX framing and decoder state were cross-checked against the public
OpenAssetTools implementation. The project keeps its implementation separate
from the original game binaries.

BMT/BML structure was cross-checked against the public `bmt2xml` format notes.
Additional practical MEB/BMT relationships were checked against public SHIFT
modding documentation and tools.

References:

- https://github.com/ermo/s2u_ucp/blob/master/nfsshift.bms
- https://git.alterware.dev/zone/OpenAssetTools/src/commit/0c2f5714193c01e43991ff43c62270c55be36d18/src/XMemCompress/XMemDecompress.cpp
- https://git.alterware.dev/zone/OpenAssetTools/src/branch/main/thirdparty/lzx/lzx.c
- https://projects.pappkartong.se/bmt2xml/
- https://github.com/auvy/nfs-shift-to-blender
- https://www.sim-garage.co.uk/files/3DSimEDHelp.pdf
- https://www.sim-garage.co.uk/files/Working%20with%20NFS%20Shift.pdf

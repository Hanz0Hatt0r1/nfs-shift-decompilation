# Attribution / research references

BFF extraction is cross-checked against the public QuickBMS `nfsshift.bms` script for Need for Speed: SHIFT / Shift 2 / Project Cars.

XMem/LZX framing and decoder state were cross-checked against the public OpenAssetTools implementation. The project keeps its own implementation separate from the original game binaries.

BMT/BML structure was cross-checked against the public `bmt2xml` format notes. Additional practical MEB/BMT relationships were checked against public SHIFT modding documentation and tools.

References:

- https://github.com/ermo/s2u_ucp/blob/master/nfsshift.bms
- https://git.alterware.dev/zone/OpenAssetTools/src/commit/0c2f5714193c01e43991ff43c62270c55be36d18/src/XMemCompress/XMemDecompress.cpp
- https://git.alterware.dev/zone/OpenAssetTools/src/branch/main/thirdparty/lzx/lzx.c
- https://projects.pappkartong.se/bmt2xml/
- https://github.com/auvy/nfs-shift-to-blender
- https://www.sim-garage.co.uk/files/3DSimEDHelp.pdf
- https://www.sim-garage.co.uk/files/Working%20with%20NFS%20Shift.pdf

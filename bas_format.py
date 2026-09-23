from __future__ import annotations
import struct
import xml.etree.ElementTree as ET
from typing import Any

def _matrix_from_hex(text: str) -> list[float]:
    words=text.split()
    if len(words)!=16:
        raise ValueError(f"BAS TRANSFORM expects 16 DWORDs, got {len(words)}")
    vals=[struct.unpack("<f",struct.pack("<I",int(w,16)))[0] for w in words]
    return vals

def parse_bas(data: bytes | str) -> dict[str, Any]:
    root=ET.fromstring(data)
    if root.tag.upper()!="SKELETON":
        raise ValueError(f"expected SKELETON root, got {root.tag!r}")
    nodes=[]
    def walk(node: ET.Element, parent: int | None) -> int:
        idx=len(nodes)
        rec={"index":idx,"name":node.get("name",""),"mirror":node.get("mirror"),"parent":parent}
        tr=node.find("TRANSFORM")
        if tr is not None:
            raw=tr.get("data","")
            rec["matrix"]= _matrix_from_hex(raw)
            rec["translation"]= [rec["matrix"][12],rec["matrix"][13],rec["matrix"][14]]
        nodes.append(rec)
        for child in node.findall("NODE"):
            walk(child,idx)
        return idx
    for n in root.findall("NODE"): walk(n,None)
    return {
        "format":"SHIFT.BAS",
        "version":1,
        "name":root.get("name",""),
        "mirroring":root.get("mirroring"),
        "exporter":None if root.find("EXPORTER/Tool") is None else dict(root.find("EXPORTER/Tool").attrib),
        "nodes":nodes,
        "root_count":sum(1 for n in nodes if n["parent"] is None),
        "node_count":len(nodes),
    }

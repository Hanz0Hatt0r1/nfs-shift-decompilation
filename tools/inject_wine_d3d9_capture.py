#!/usr/bin/env python3
"""Inject the SHIFT D3D9 JSONL producer into Wine 10.0's builtin d3d9 tree."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAPTURE_DIR = ROOT / "wine_capture"
PRODUCER = CAPTURE_DIR / "shift_d3d9_capture.c"
HEADER = CAPTURE_DIR / "shift_d3d9_capture.h"


class PatchError(RuntimeError):
    pass


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise PatchError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def patch_function(text: str, name: str, transform) -> str:
    pattern = re.compile(
        rf"(static\s+(?:HRESULT|void|ULONG|BOOL)\s+WINAPI\s+{re.escape(name)}\b.*?)(?=\nstatic\s+)",
        re.DOTALL,
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise PatchError(f"{name}: expected one function, found {len(matches)}")

    match = matches[0]
    body = match.group(1)
    patched = transform(body)
    if patched == body:
        raise PatchError(f"{name}: transformation made no changes")
    return text[:match.start(1)] + patched + text[match.end(1):]


def function_body(text: str, name: str) -> str:
    pattern = re.compile(
        rf"(static\\s+(?:HRESULT|void|ULONG|BOOL)\\s+WINAPI\\s+{re.escape(name)}\\b.*?)(?=\\nstatic\\s+)",
        re.DOTALL,
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise PatchError(f"{name}: expected one function, found {len(matches)}")
    return matches[0].group(1)


def patch_device(device: Path) -> None:
    text = device.read_text(encoding="utf-8")

    def create_decl(body: str) -> str:
        return replace_once(
            body,
            "        *declaration = &object->IDirect3DVertexDeclaration9_iface;\n",
            "        *declaration = &object->IDirect3DVertexDeclaration9_iface;\n"
            "        shift_capture_create_vertex_declaration(iface, elements, *declaration);\n",
            "CreateVertexDeclaration",
        )

    def set_decl(body: str) -> str:
        return replace_once(
            body,
            "    wined3d_mutex_unlock();\n\n    return D3D_OK;\n",
            "    wined3d_mutex_unlock();\n"
            "    shift_capture_set_vertex_declaration(iface, declaration);\n\n"
            "    return D3D_OK;\n",
            "SetVertexDeclaration",
        )

    def set_stream(body: str) -> str:
        return replace_once(
            body,
            "    wined3d_mutex_unlock();\n\n    return hr;\n",
            "    wined3d_mutex_unlock();\n"
            "    if (SUCCEEDED(hr))\n"
            "        shift_capture_set_stream_source(iface, stream_idx, buffer, offset, stride);\n\n"
            "    return hr;\n",
            "SetStreamSource",
        )

    def set_indices(body: str) -> str:
        return replace_once(
            body,
            "    wined3d_mutex_unlock();\n\n    return D3D_OK;\n",
            "    wined3d_mutex_unlock();\n"
            "    shift_capture_set_indices(iface, buffer,\n"
            "            ib ? d3dformat_from_wined3dformat(ib->format) : D3DFMT_UNKNOWN);\n\n"
            "    return D3D_OK;\n",
            "SetIndices",
        )

    def set_texture(body: str) -> str:
        return replace_once(
            body,
            "    texture_impl = unsafe_impl_from_IDirect3DBaseTexture9(texture);\n",
            "    texture_impl = unsafe_impl_from_IDirect3DBaseTexture9(texture);\n"
            "    shift_capture_set_texture(iface, stage, texture);\n",
            "SetTexture",
        )

    def create_vs(body: str) -> str:
        return replace_once(
            body,
            "    *shader = &object->IDirect3DVertexShader9_iface;\n",
            "    *shader = &object->IDirect3DVertexShader9_iface;\n"
            "    shift_capture_create_vertex_shader(iface, byte_code, *shader);\n",
            "CreateVertexShader",
        )

    def set_vs(body: str) -> str:
        return replace_once(
            body,
            "    wined3d_mutex_unlock();\n\n    return D3D_OK;\n",
            "    wined3d_mutex_unlock();\n"
            "    shift_capture_set_vertex_shader(iface, shader);\n\n"
            "    return D3D_OK;\n",
            "SetVertexShader",
        )

    def set_vs_const(body: str) -> str:
        return replace_once(
            body,
            "    wined3d_mutex_unlock();\n\n    return hr;\n",
            "    wined3d_mutex_unlock();\n"
            "    if (SUCCEEDED(hr))\n"
            "        shift_capture_set_vertex_shader_constant_f(iface, reg_idx, data, count);\n\n"
            "    return hr;\n",
            "SetVertexShaderConstantF",
        )

    def create_ps(body: str) -> str:
        return replace_once(
            body,
            "    *shader = &object->IDirect3DPixelShader9_iface;\n",
            "    *shader = &object->IDirect3DPixelShader9_iface;\n"
            "    shift_capture_create_pixel_shader(iface, byte_code, *shader);\n",
            "CreatePixelShader",
        )

    def set_ps(body: str) -> str:
        return replace_once(
            body,
            "    wined3d_mutex_unlock();\n\n    return D3D_OK;\n",
            "    wined3d_mutex_unlock();\n"
            "    shift_capture_set_pixel_shader(iface, shader);\n\n"
            "    return D3D_OK;\n",
            "SetPixelShader",
        )

    def set_ps_const(body: str) -> str:
        return replace_once(
            body,
            "    wined3d_mutex_unlock();\n\n    return hr;\n",
            "    wined3d_mutex_unlock();\n"
            "    if (SUCCEEDED(hr))\n"
            "        shift_capture_set_pixel_shader_constant_f(iface, reg_idx, data, count);\n\n"
            "    return hr;\n",
            "SetPixelShaderConstantF",
        )

    def draw(body: str) -> str:
        return replace_once(
            body,
            "    wined3d_device_context_draw_indexed(device->immediate_context, base_vertex_idx, start_idx, index_count, 0,\n",
            "    shift_capture_draw_indexed_primitive(iface, primitive_type, base_vertex_idx,\n"
            "            min_vertex_idx, vertex_count, start_idx, primitive_count);\n"
            "    wined3d_device_context_draw_indexed(device->immediate_context, base_vertex_idx, start_idx, index_count, 0,\n",
            "DrawIndexedPrimitive",
        )

    def present(body: str) -> str:
        return replace_once(
            body,
            "    wined3d_mutex_unlock();\n\n    return D3D_OK;\n",
            "    wined3d_mutex_unlock();\n"
            "    shift_capture_present(iface);\n\n"
            "    return D3D_OK;\n",
            "Present",
        )

    transforms = (
        ("d3d9_device_CreateVertexDeclaration", create_decl),
        ("d3d9_device_SetVertexDeclaration", set_decl),
        ("d3d9_device_SetStreamSource", set_stream),
        ("d3d9_device_SetIndices", set_indices),
        ("d3d9_device_SetTexture", set_texture),
        ("d3d9_device_CreateVertexShader", create_vs),
        ("d3d9_device_SetVertexShader", set_vs),
        ("d3d9_device_SetVertexShaderConstantF", set_vs_const),
        ("d3d9_device_CreatePixelShader", create_ps),
        ("d3d9_device_SetPixelShader", set_ps),
        ("d3d9_device_SetPixelShaderConstantF", set_ps_const),
        ("d3d9_device_DrawIndexedPrimitive", draw),
        ("d3d9_device_Present", present),
    )

    for name, transform in transforms:
        if "shift_capture_" in function_body(text, name):
            continue
        text = patch_function(text, name, transform)

    device.write_text(text, encoding="utf-8")


def patch_private_header(header: Path) -> None:
    text = header.read_text(encoding="utf-8")
    if '#include "shift_d3d9_capture.h"' not in text:
        text = replace_once(
            text,
            '#include "wine/wined3d.h"\n',
            '#include "wine/wined3d.h"\n#include "shift_d3d9_capture.h"\n',
            "d3d9_private.h include",
        )
        header.write_text(text, encoding="utf-8")


def patch_makefile(makefile: Path) -> None:
    text = makefile.read_text(encoding="utf-8")
    if "shift_d3d9_capture.c" not in text:
        text = replace_once(
            text,
            "\td3d9_main.c \\\n",
            "\td3d9_main.c \\\n\tshift_d3d9_capture.c \\\n",
            "Makefile.in sources",
        )
        makefile.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wine_source", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    source = args.wine_source.expanduser().resolve()
    d3d9_dir = source / "dlls" / "d3d9"

    required = [
        source / "configure",
        d3d9_dir / "Makefile.in",
        d3d9_dir / "d3d9_private.h",
        d3d9_dir / "device.c",
        d3d9_dir / "d3d9_main.c",
    ]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise SystemExit("Not a Wine source tree:\n  " + "\n  ".join(missing))

    main_c = (d3d9_dir / "d3d9_main.c").read_text(encoding="utf-8")
    if "IDirect3D9 * WINAPI DECLSPEC_HOTPATCH Direct3DCreate9(UINT sdk_version)" not in main_c:
        raise SystemExit("Wine source does not match the expected 10.0 Direct3DCreate9 anchor")

    if args.check_only:
        print(f"Wine D3D9 source looks patchable: {source}")
        return 0

    shutil.copy2(PRODUCER, d3d9_dir / PRODUCER.name)
    shutil.copy2(HEADER, d3d9_dir / HEADER.name)

    patch_private_header(d3d9_dir / "d3d9_private.h")
    patch_makefile(d3d9_dir / "Makefile.in")
    patch_device(d3d9_dir / "device.c")

    print(f"Patched Wine D3D9 capture integration: {source}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PatchError as exc:
        raise SystemExit(f"patch failed: {exc}")

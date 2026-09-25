from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INJECTOR = ROOT / "tools" / "inject_wine_d3d9_capture.py"

FIXTURE_MAIN = """#include "initguid.h"
#include "d3d9_private.h"

IDirect3D9 * WINAPI DECLSPEC_HOTPATCH Direct3DCreate9(UINT sdk_version)
{
    return 0;
}
"""

FIXTURE_PRIVATE = '#include "d3d9.h"\\n#include "wine/wined3d.h"\\n'

FIXTURE_MAKEFILE = """MODULE    = d3d9.dll
IMPORTLIB = d3d9
IMPORTS   = dxguid uuid wined3d

SOURCES = \\
\tbuffer.c \\
\td3d9_main.c \\
\tdevice.c
"""

FIXTURE_DEVICE = r'''
static HRESULT WINAPI d3d9_device_CreateVertexDeclaration(IDirect3DDevice9Ex *iface,
        const D3DVERTEXELEMENT9 *elements, IDirect3DVertexDeclaration9 **declaration)
{
    HRESULT hr;
    if (SUCCEEDED(hr = d3d9_vertex_declaration_create(device, elements, &object)))
        *declaration = &object->IDirect3DVertexDeclaration9_iface;
    return hr;
}

static HRESULT WINAPI d3d9_device_SetVertexDeclaration(IDirect3DDevice9Ex *iface,
        IDirect3DVertexDeclaration9 *declaration)
{
    wined3d_mutex_unlock();

    return D3D_OK;
}

static HRESULT WINAPI d3d9_device_SetStreamSource(IDirect3DDevice9Ex *iface,
        UINT stream_idx, IDirect3DVertexBuffer9 *buffer, UINT offset, UINT stride)
{
    HRESULT hr;
    wined3d_mutex_unlock();

    return hr;
}

static HRESULT WINAPI d3d9_device_SetIndices(IDirect3DDevice9Ex *iface,
        IDirect3DIndexBuffer9 *buffer)
{
    wined3d_mutex_unlock();

    return D3D_OK;
}

static HRESULT WINAPI d3d9_device_SetTexture(IDirect3DDevice9Ex *iface,
        DWORD stage, IDirect3DBaseTexture9 *texture)
{
    texture_impl = unsafe_impl_from_IDirect3DBaseTexture9(texture);

    return D3D_OK;
}

static HRESULT WINAPI d3d9_device_CreateVertexShader(IDirect3DDevice9Ex *iface,
        const DWORD *byte_code, IDirect3DVertexShader9 **shader)
{
    *shader = &object->IDirect3DVertexShader9_iface;
    return D3D_OK;
}

static HRESULT WINAPI d3d9_device_SetVertexShader(IDirect3DDevice9Ex *iface,
        IDirect3DVertexShader9 *shader)
{
    wined3d_mutex_unlock();

    return D3D_OK;
}

static HRESULT WINAPI d3d9_device_SetVertexShaderConstantF(IDirect3DDevice9Ex *iface,
        UINT reg_idx, const float *data, UINT count)
{
    HRESULT hr;
    wined3d_mutex_unlock();

    return hr;
}

static HRESULT WINAPI d3d9_device_CreatePixelShader(IDirect3DDevice9Ex *iface,
        const DWORD *byte_code, IDirect3DPixelShader9 **shader)
{
    *shader = &object->IDirect3DPixelShader9_iface;
    return D3D_OK;
}

static HRESULT WINAPI d3d9_device_SetPixelShader(IDirect3DDevice9Ex *iface,
        IDirect3DPixelShader9 *shader)
{
    wined3d_mutex_unlock();

    return D3D_OK;
}

static HRESULT WINAPI d3d9_device_SetPixelShaderConstantF(IDirect3DDevice9Ex *iface,
        UINT reg_idx, const float *data, UINT count)
{
    HRESULT hr;
    wined3d_mutex_unlock();

    return hr;
}

static HRESULT WINAPI d3d9_device_DrawIndexedPrimitive(IDirect3DDevice9Ex *iface,
        D3DPRIMITIVETYPE primitive_type, INT base_vertex_idx, UINT min_vertex_idx,
        UINT vertex_count, UINT start_idx, UINT primitive_count)
{
    wined3d_device_context_draw_indexed(device->immediate_context, base_vertex_idx, start_idx, index_count, 0,
            device->stateblock_state->streams[0].frequency);
    return D3D_OK;
}

static HRESULT WINAPI DECLSPEC_HOTPATCH d3d9_device_Present(IDirect3DDevice9Ex *iface,
        const RECT *src_rect, const RECT *dst_rect, HWND dst_window_override, const RGNDATA *dirty_region)
{
    wined3d_mutex_unlock();

    return D3D_OK;
}

static void shift_fixture_sentinel(void) {}
'''


def make_tree(tmp_path: Path) -> Path:
    source = tmp_path / "wine"
    d3d9 = source / "dlls" / "d3d9"
    d3d9.mkdir(parents=True)
    (source / "configure").write_text("#!/bin/sh\\nexit 0\\n", encoding="utf-8")
    (d3d9 / "d3d9_main.c").write_text(FIXTURE_MAIN, encoding="utf-8")
    (d3d9 / "d3d9_private.h").write_text(FIXTURE_PRIVATE, encoding="utf-8")
    (d3d9 / "Makefile.in").write_text(FIXTURE_MAKEFILE, encoding="utf-8")
    (d3d9 / "device.c").write_text(FIXTURE_DEVICE, encoding="utf-8")
    return source


def test_wine_d3d9_injector(tmp_path: Path) -> None:
    source = make_tree(tmp_path)

    subprocess.run(
        ["python3", str(INJECTOR), str(source), "--check-only"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        ["python3", str(INJECTOR), str(source)],
        cwd=ROOT,
        check=True,
    )

    device = source / "dlls" / "d3d9" / "device.c"
    patched = device.read_text(encoding="utf-8")

    expected = [
        "shift_capture_create_vertex_declaration(",
        "shift_capture_set_vertex_declaration(",
        "shift_capture_set_stream_source(",
        "shift_capture_set_indices(",
        "shift_capture_set_texture(",
        "shift_capture_create_vertex_shader(",
        "shift_capture_set_vertex_shader(",
        "shift_capture_set_vertex_shader_constant_f(",
        "shift_capture_create_pixel_shader(",
        "shift_capture_set_pixel_shader(",
        "shift_capture_set_pixel_shader_constant_f(",
        "shift_capture_draw_indexed_primitive(",
        "shift_capture_present(",
    ]

    for marker in expected:
        assert patched.count(marker) == 1, marker

    makefile = (source / "dlls" / "d3d9" / "Makefile.in").read_text(encoding="utf-8")
    assert "\tshift_d3d9_capture.c \\\n" in makefile

    private = (source / "dlls" / "d3d9" / "d3d9_private.h").read_text(encoding="utf-8")
    assert '#include "shift_d3d9_capture.h"' in private

    producer = source / "dlls" / "d3d9" / "shift_d3d9_capture.c"
    header = source / "dlls" / "d3d9" / "shift_d3d9_capture.h"
    assert producer.read_text(encoding="utf-8") == (ROOT / "wine_capture" / "shift_d3d9_capture.c").read_text(encoding="utf-8")
    assert header.read_text(encoding="utf-8") == (ROOT / "wine_capture" / "shift_d3d9_capture.h").read_text(encoding="utf-8")

    before = patched
    subprocess.run(
        ["python3", str(INJECTOR), str(source)],
        cwd=ROOT,
        check=True,
    )
    assert device.read_text(encoding="utf-8") == before

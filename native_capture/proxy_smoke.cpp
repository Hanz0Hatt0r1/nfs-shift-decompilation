#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <d3d9.h>

#include <cstdio>
#include <string>

namespace {
using Direct3DCreate9Fn = IDirect3D9* (WINAPI*)(UINT);
using PerfBeginFn = int (WINAPI*)(D3DCOLOR, LPCWSTR);
using PerfEndFn = int (WINAPI*)();

bool require_export(HMODULE module, const char* name) {
    if (GetProcAddress(module, name)) return true;
    std::fprintf(stderr, "missing export: %s\\n", name);
    return false;
}
}

int wmain(int argc, wchar_t** argv) {
    if (argc < 2) {
        std::fwprintf(stderr, L"usage: %ls <d3d9.dll> [log.jsonl]\\n", argv[0]);
        return 2;
    }

    SetEnvironmentVariableW(L"SHIFT_D3D9_CAPTURE_MODE", L"passthrough");
    SetEnvironmentVariableW(L"SHIFT_D3D9_CAPTURE_FLUSH", L"1");
    if (argc >= 3) SetEnvironmentVariableW(L"SHIFT_D3D9_CAPTURE", argv[2]);

    HMODULE proxy = LoadLibraryW(argv[1]);
    if (!proxy) {
        std::fprintf(stderr, "LoadLibrary failed: %lu\\n", GetLastError());
        return 3;
    }

    const char* required[] = {
        "Direct3DCreate9",
        "Direct3DCreate9Ex",
        "D3DPERF_BeginEvent",
        "D3DPERF_EndEvent",
        "D3DPERF_GetStatus",
        "D3DPERF_QueryRepeatFrame",
        "D3DPERF_SetMarker",
        "D3DPERF_SetOptions",
        "D3DPERF_SetRegion",
        "DebugSetLevel",
        "DebugSetMute",
    };
    for (const char* name : required) {
        if (!require_export(proxy, name)) {
            FreeLibrary(proxy);
            return 4;
        }
    }

    auto create9 = reinterpret_cast<Direct3DCreate9Fn>(
        GetProcAddress(proxy, "Direct3DCreate9"));
    IDirect3D9* d3d = create9(D3D_SDK_VERSION);
    if (!d3d) {
        std::fprintf(stderr, "Direct3DCreate9 returned null\\n");
        FreeLibrary(proxy);
        return 5;
    }
    d3d->Release();

    auto begin = reinterpret_cast<PerfBeginFn>(
        GetProcAddress(proxy, "D3DPERF_BeginEvent"));
    auto end = reinterpret_cast<PerfEndFn>(
        GetProcAddress(proxy, "D3DPERF_EndEvent"));
    begin(D3DCOLOR_XRGB(1, 2, 3), L"shift-proxy-smoke");
    end();

    FreeLibrary(proxy);
    return 0;
}

#pragma once

#ifdef _WIN32
#include <d3d9.h>
#include <stdint.h>

extern "C" {
__declspec(dllexport) HRESULT ShiftD3D9TraceInstall(IDirect3DDevice9* device);
__declspec(dllexport) HRESULT ShiftD3D9TraceSetOutput(const char* path);
__declspec(dllexport) void ShiftD3D9TraceSetFrame(uint64_t frame);
__declspec(dllexport) void ShiftD3D9TraceSetResource(const char* resource_path, const char* resource_sha256);
__declspec(dllexport) void ShiftD3D9TraceFlush(void);
__declspec(dllexport) void ShiftD3D9TraceShutdown(void);
}
#endif
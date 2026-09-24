#ifdef _WIN32
#include "shift_d3d9_trace.h"

#include <windows.h>
#include <d3d9.h>
#include <atomic>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <new>
#include <vector>

namespace {

constexpr size_t kDeviceVtableSlots = 119;
constexpr size_t kMaxDeclarationElements = 256;
constexpr size_t kMaxShaderDwords = 262144;

constexpr size_t kSetVertexDeclaration = 87;
constexpr size_t kCreateVertexShader = 91;
constexpr size_t kSetVertexShader = 92;
constexpr size_t kSetVertexShaderConstantF = 94;
constexpr size_t kSetStreamSource = 100;
constexpr size_t kSetIndices = 104;
constexpr size_t kCreatePixelShader = 106;
constexpr size_t kSetPixelShader = 107;
constexpr size_t kSetPixelShaderConstantF = 109;
constexpr size_t kDrawIndexedPrimitive = 82;

using SetVertexDeclarationFn = HRESULT (WINAPI*)(IDirect3DDevice9*, IDirect3DVertexDeclaration9*);
using CreateVertexShaderFn = HRESULT (WINAPI*)(IDirect3DDevice9*, const DWORD*, IDirect3DVertexShader9**);
using SetVertexShaderFn = HRESULT (WINAPI*)(IDirect3DDevice9*, IDirect3DVertexShader9*);
using SetVertexShaderConstantFFn = HRESULT (WINAPI*)(IDirect3DDevice9*, UINT, const float*, UINT);
using SetStreamSourceFn = HRESULT (WINAPI*)(IDirect3DDevice9*, UINT, IDirect3DVertexBuffer9*, UINT, UINT);
using SetIndicesFn = HRESULT (WINAPI*)(IDirect3DDevice9*, IDirect3DIndexBuffer9*);
using CreatePixelShaderFn = HRESULT (WINAPI*)(IDirect3DDevice9*, const DWORD*, IDirect3DPixelShader9**);
using SetPixelShaderFn = HRESULT (WINAPI*)(IDirect3DDevice9*, IDirect3DPixelShader9*);
using SetPixelShaderConstantFFn = HRESULT (WINAPI*)(IDirect3DDevice9*, UINT, const float*, UINT);
using DrawIndexedPrimitiveFn = HRESULT (WINAPI*)(IDirect3DDevice9*, D3DPRIMITIVETYPE, INT, UINT, UINT, UINT, UINT);

struct TraceState {
  IDirect3DDevice9* device = nullptr;
  void** original_vtable = nullptr;
  void** hooked_vtable = nullptr;
  FILE* output = nullptr;
  CRITICAL_SECTION io_lock{};
  bool lock_initialized = false;
  std::atomic<unsigned long long> sequence{0};
  unsigned long long frame = 0;
  char resource_path[1024]{};
  char resource_sha256[65]{};
};

TraceState g_state;

void ensure_lock() {
  ensure_lock();
}

template <typename T>
T original(size_t slot) {
  return reinterpret_cast<T>(g_state.original_vtable[slot]);
}

void json_string(FILE* fp, const char* value) {
  fputc('"', fp);
  const unsigned char* p = reinterpret_cast<const unsigned char*>(value ? value : "");
  for (; *p; ++p) {
    switch (*p) {
      case '\\': fputs("\\\\", fp); break;
      case '"': fputs("\\\"", fp); break;
      case '\n': fputs("\\n", fp); break;
      case '\r': fputs("\\r", fp); break;
      case '\t': fputs("\\t", fp); break;
      default:
        if (*p < 0x20) fprintf(fp, "\\u%04x", static_cast<unsigned>(*p));
        else fputc(*p, fp);
        break;
    }
  }
  fputc('"', fp);
}

void begin_event(const char* name) {
  if (!g_state.output || !g_state.lock_initialized) return;
  EnterCriticalSection(&g_state.io_lock);
  fprintf(g_state.output, "{\\"event\\":");
  json_string(g_state.output, name);
  fprintf(g_state.output, ",\\"sequence\\":%llu,\\"frame\\":%llu,\\"thread_id\\":%lu",
          ++g_state.sequence, g_state.frame,
          static_cast<unsigned long>(GetCurrentThreadId()));
}

void append_resource_context() {
  if (!g_state.output) return;
  if (g_state.resource_path[0]) {
    fputs(",\\"resource_path\\":", g_state.output);
    json_string(g_state.output, g_state.resource_path);
  }
  if (g_state.resource_sha256[0]) {
    fputs(",\\"resource_sha256\\":", g_state.output);
    json_string(g_state.output, g_state.resource_sha256);
  }
}

void end_event() {
  if (!g_state.output || !g_state.lock_initialized) return;
  fputs("}\n", g_state.output);
  fflush(g_state.output);
  LeaveCriticalSection(&g_state.io_lock);
}

size_t declaration_bytes(const D3DVERTEXELEMENT9* elements) {
  if (!elements) return 0;
  for (size_t i = 0; i < kMaxDeclarationElements; ++i) {
    const D3DVERTEXELEMENT9& e = elements[i];
    if (e.Stream == 0xffff && e.Offset == 0 && e.Type == D3DDECLTYPE_UNUSED &&
        e.Method == 0 && e.Usage == 0 && e.UsageIndex == 0) {
      return (i + 1) * sizeof(D3DVERTEXELEMENT9);
    }
  }
  return 0;
}

size_t shader_bytes(const DWORD* code) {
  if (!code) return 0;
  for (size_t i = 0; i < kMaxShaderDwords; ++i) {
    if (code[i] == 0x0000ffff) return (i + 1) * sizeof(DWORD);
  }
  return 0;
}

void write_hex(const unsigned char* data, size_t size) {
  static const char digits[] = "0123456789abcdef";
  for (size_t i = 0; i < size; ++i) {
    fputc(digits[(data[i] >> 4) & 0xf], g_state.output);
    fputc(digits[data[i] & 0xf], g_state.output);
  }
}

void log_declaration_create(const D3DVERTEXELEMENT9* elements, IDirect3DVertexDeclaration9* object, HRESULT hr) {
  begin_event("create_vertex_declaration");
  if (g_state.output) {
    fprintf(g_state.output, ",\\"declaration_ptr\\":\\"0x%p\\",\\"hr\\":%ld", object, static_cast<long>(hr));
    append_resource_context();
    const size_t bytes = declaration_bytes(elements);
    if (bytes) {
      fputs(",\\"bytes_hex\\":\\"", g_state.output);
      write_hex(reinterpret_cast<const unsigned char*>(elements), bytes);
      fputc('"', g_state.output);
    }
  }
  end_event();
}

void log_shader_create(const char* event_name, const void* object, const DWORD* code, HRESULT hr) {
  begin_event(event_name);
  if (g_state.output) {
    fprintf(g_state.output, ",\\"shader_ptr\\":\\"0x%p\\",\\"hr\\":%ld", object, static_cast<long>(hr));
    append_resource_context();
    const size_t bytes = shader_bytes(code);
    if (bytes) {
      fputs(",\\"bytes_hex\\":\\"", g_state.output);
      write_hex(reinterpret_cast<const unsigned char*>(code), bytes);
      fputc('"', g_state.output);
    }
  }
  end_event();
}

void log_bind_pointer(const char* event_name, const void* object) {
  begin_event(event_name);
  if (g_state.output) fprintf(g_state.output, ",\\"shader_ptr\\":\\"0x%p\\"", object);
  end_event();
}

void log_constant_write(const char* event_name, UINT start_register, const float* values, UINT vector_count) {
  begin_event(event_name);
  if (g_state.output) {
    fprintf(g_state.output, ",\\"start_register\\":%u,\\"vector4f_count\\":%u,\\"values\\":[", start_register, vector_count);
    const size_t count = static_cast<size_t>(vector_count) * 4;
    for (size_t i = 0; i < count; ++i) {
      if (i) fputc(',', g_state.output);
      fprintf(g_state.output, "%.9g", static_cast<double>(values[i]));
    }
    fputc(']', g_state.output);
  }
  end_event();
}

HRESULT WINAPI hook_SetVertexDeclaration(IDirect3DDevice9* self, IDirect3DVertexDeclaration9* declaration) {
  const HRESULT hr = original<SetVertexDeclarationFn>(kSetVertexDeclaration)(self, declaration);
  begin_event("set_vertex_declaration");
  if (g_state.output) fprintf(g_state.output, ",\\"declaration_ptr\\":\\"0x%p\\",\\"hr\\":%ld", declaration, static_cast<long>(hr));
  end_event();
  return hr;
}

HRESULT WINAPI hook_CreateVertexShader(IDirect3DDevice9* self, const DWORD* code, IDirect3DVertexShader9** out) {
  const HRESULT hr = original<CreateVertexShaderFn>(kCreateVertexShader)(self, code, out);
  log_shader_create("create_vertex_shader", (out && SUCCEEDED(hr)) ? *out : nullptr, code, hr);
  return hr;
}

HRESULT WINAPI hook_SetVertexShader(IDirect3DDevice9* self, IDirect3DVertexShader9* shader) {
  const HRESULT hr = original<SetVertexShaderFn>(kSetVertexShader)(self, shader);
  log_bind_pointer("set_vertex_shader", shader);
  return hr;
}

HRESULT WINAPI hook_SetVertexShaderConstantF(IDirect3DDevice9* self, UINT start, const float* values, UINT count) {
  const HRESULT hr = original<SetVertexShaderConstantFFn>(kSetVertexShaderConstantF)(self, start, values, count);
  if (values && count) log_constant_write("set_vertex_shader_constant_f", start, values, count);
  return hr;
}

HRESULT WINAPI hook_SetStreamSource(IDirect3DDevice9* self, UINT stream, IDirect3DVertexBuffer9* buffer, UINT offset, UINT stride) {
  const HRESULT hr = original<SetStreamSourceFn>(kSetStreamSource)(self, stream, buffer, offset, stride);
  begin_event("set_stream_source");
  if (g_state.output) fprintf(g_state.output, ",\\"stream\\":%u,\\"buffer_ptr\\":\\"0x%p\\",\\"offset\\":%u,\\"stride\\":%u,\\"hr\\":%ld", stream, buffer, offset, stride, static_cast<long>(hr));
  end_event();
  return hr;
}

HRESULT WINAPI hook_SetIndices(IDirect3DDevice9* self, IDirect3DIndexBuffer9* buffer) {
  const HRESULT hr = original<SetIndicesFn>(kSetIndices)(self, buffer);
  begin_event("set_indices");
  if (g_state.output) fprintf(g_state.output, ",\\"index_buffer_ptr\\":\\"0x%p\\",\\"hr\\":%ld", buffer, static_cast<long>(hr));
  end_event();
  return hr;
}

HRESULT WINAPI hook_CreatePixelShader(IDirect3DDevice9* self, const DWORD* code, IDirect3DPixelShader9** out) {
  const HRESULT hr = original<CreatePixelShaderFn>(kCreatePixelShader)(self, code, out);
  log_shader_create("create_pixel_shader", (out && SUCCEEDED(hr)) ? *out : nullptr, code, hr);
  return hr;
}

HRESULT WINAPI hook_SetPixelShader(IDirect3DDevice9* self, IDirect3DPixelShader9* shader) {
  const HRESULT hr = original<SetPixelShaderFn>(kSetPixelShader)(self, shader);
  log_bind_pointer("set_pixel_shader", shader);
  return hr;
}

HRESULT WINAPI hook_SetPixelShaderConstantF(IDirect3DDevice9* self, UINT start, const float* values, UINT count) {
  const HRESULT hr = original<SetPixelShaderConstantFFn>(kSetPixelShaderConstantF)(self, start, values, count);
  if (values && count) log_constant_write("set_pixel_shader_constant_f", start, values, count);
  return hr;
}

HRESULT WINAPI hook_DrawIndexedPrimitive(IDirect3DDevice9* self, D3DPRIMITIVETYPE type, INT base_vertex_index, UINT min_vertex_index, UINT num_vertices, UINT start_index, UINT primitive_count) {
  const HRESULT hr = original<DrawIndexedPrimitiveFn>(kDrawIndexedPrimitive)(self, type, base_vertex_index, min_vertex_index, num_vertices, start_index, primitive_count);
  begin_event("draw_indexed_primitive");
  if (g_state.output) fprintf(g_state.output, ",\\"primitive_type\\":%u,\\"base_vertex_index\\":%ld,\\"min_vertex_index\\":%u,\\"num_vertices\\":%u,\\"start_index\\":%u,\\"primitive_count\\":%u,\\"hr\\":%ld", static_cast<unsigned>(type), static_cast<long>(base_vertex_index), min_vertex_index, num_vertices, start_index, primitive_count, static_cast<long>(hr));
  end_event();
  return hr;
}

void patch(void** table, size_t slot, void* hook) {
  table[slot] = hook;
}

bool swap_vtable(IDirect3DDevice9* device, void** table) {
  if (!device || !table) return false;
  void*** object = reinterpret_cast<void***>(device);
  DWORD old_protect = 0;
  if (!VirtualProtect(object, sizeof(void*), PAGE_READWRITE, &old_protect)) return false;
  *object = table;
  DWORD restored = 0;
  VirtualProtect(object, sizeof(void*), old_protect, &restored);
  return true;
}

} // namespace

extern "C" __declspec(dllexport) HRESULT ShiftD3D9TraceSetOutput(const char* path) {
  if (!path || !path[0]) return E_INVALIDARG;
  ensure_lock();
  EnterCriticalSection(&g_state.io_lock);
  if (g_state.output) fclose(g_state.output);
  g_state.output = fopen(path, "ab");
  const HRESULT result = g_state.output ? S_OK : E_FAIL;
  LeaveCriticalSection(&g_state.io_lock);
  return result;
}

extern "C" __declspec(dllexport) void ShiftD3D9TraceSetFrame(unsigned long long frame) {
  g_state.frame = frame;
}

extern "C" __declspec(dllexport) void ShiftD3D9TraceSetResource(const char* path, const char* sha256) {
  ensure_lock();
  EnterCriticalSection(&g_state.io_lock);
  strncpy_s(g_state.resource_path, sizeof(g_state.resource_path), path ? path : "", _TRUNCATE);
  strncpy_s(g_state.resource_sha256, sizeof(g_state.resource_sha256), sha256 ? sha256 : "", _TRUNCATE);
  LeaveCriticalSection(&g_state.io_lock);
}

extern "C" __declspec(dllexport) HRESULT ShiftD3D9TraceInstall(IDirect3DDevice9* device) {
  if (!device) return E_INVALIDARG;
  if (g_state.device) return g_state.device == device ? S_FALSE : HRESULT_FROM_WIN32(ERROR_ALREADY_EXISTS);
  if (!g_state.lock_initialized) {
    InitializeCriticalSection(&g_state.io_lock);
    g_state.lock_initialized = true;
  }
  g_state.device = device;
  g_state.original_vtable = *reinterpret_cast<void***>(device);
  g_state.hooked_vtable = new (std::nothrow) void*[kDeviceVtableSlots];
  if (!g_state.hooked_vtable) return E_OUTOFMEMORY;
  std::memcpy(g_state.hooked_vtable, g_state.original_vtable, sizeof(void*) * kDeviceVtableSlots);
  patch(g_state.hooked_vtable, kSetVertexDeclaration, reinterpret_cast<void*>(&hook_SetVertexDeclaration));
  patch(g_state.hooked_vtable, kCreateVertexShader, reinterpret_cast<void*>(&hook_CreateVertexShader));
  patch(g_state.hooked_vtable, kSetVertexShader, reinterpret_cast<void*>(&hook_SetVertexShader));
  patch(g_state.hooked_vtable, kSetVertexShaderConstantF, reinterpret_cast<void*>(&hook_SetVertexShaderConstantF));
  patch(g_state.hooked_vtable, kSetStreamSource, reinterpret_cast<void*>(&hook_SetStreamSource));
  patch(g_state.hooked_vtable, kSetIndices, reinterpret_cast<void*>(&hook_SetIndices));
  patch(g_state.hooked_vtable, kCreatePixelShader, reinterpret_cast<void*>(&hook_CreatePixelShader));
  patch(g_state.hooked_vtable, kSetPixelShader, reinterpret_cast<void*>(&hook_SetPixelShader));
  patch(g_state.hooked_vtable, kSetPixelShaderConstantF, reinterpret_cast<void*>(&hook_SetPixelShaderConstantF));
  patch(g_state.hooked_vtable, kDrawIndexedPrimitive, reinterpret_cast<void*>(&hook_DrawIndexedPrimitive));
  if (!swap_vtable(device, g_state.hooked_vtable)) {
    delete[] g_state.hooked_vtable;
    g_state.hooked_vtable = nullptr;
    g_state.device = nullptr;
    g_state.original_vtable = nullptr;
    return HRESULT_FROM_WIN32(GetLastError());
  }
  return S_OK;
}

extern "C" __declspec(dllexport) void ShiftD3D9TraceFlush(void) {
  if (g_state.output) fflush(g_state.output);
}

extern "C" __declspec(dllexport) void ShiftD3D9TraceShutdown(void) {
  if (g_state.device && g_state.original_vtable) swap_vtable(g_state.device, g_state.original_vtable);
  if (g_state.output) { fclose(g_state.output); g_state.output = nullptr; }
  delete[] g_state.hooked_vtable;
  g_state.hooked_vtable = nullptr;
  g_state.original_vtable = nullptr;
  g_state.device = nullptr;
  if (g_state.lock_initialized) {
    DeleteCriticalSection(&g_state.io_lock);
    g_state.lock_initialized = false;
  }
}

#endif
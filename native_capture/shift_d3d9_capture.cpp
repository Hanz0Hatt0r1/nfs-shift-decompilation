#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#define Direct3DCreate9 SHIFT_SYSTEM_Direct3DCreate9
#include <d3d9.h>
#undef Direct3DCreate9

#include <atomic>
#include <cmath>
#include <locale>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <limits>
#include <mutex>
#include <sstream>
#include <string>
#include <vector>

namespace {

constexpr std::size_t D3D9_VTABLE_COUNT = 119;
constexpr std::size_t IDIRECT3D9_VTABLE_COUNT = 17;

constexpr std::size_t SLOT_PRESENT = 17;
constexpr std::size_t SLOT_SET_TEXTURE = 65;
constexpr std::size_t SLOT_DRAW_INDEXED_PRIMITIVE = 82;
constexpr std::size_t SLOT_CREATE_VERTEX_SHADER = 91;
constexpr std::size_t SLOT_CREATE_VERTEX_DECLARATION = 86;
constexpr std::size_t SLOT_SET_VERTEX_DECLARATION = 87;
constexpr std::size_t SLOT_SET_VERTEX_SHADER = 92;
constexpr std::size_t SLOT_SET_VERTEX_SHADER_CONSTANT_F = 94;
constexpr std::size_t SLOT_SET_STREAM_SOURCE = 100;
constexpr std::size_t SLOT_SET_INDICES = 104;
constexpr std::size_t SLOT_CREATE_PIXEL_SHADER = 106;
constexpr std::size_t SLOT_SET_PIXEL_SHADER = 107;
constexpr std::size_t SLOT_SET_PIXEL_SHADER_CONSTANT_F = 109;

using Direct3DCreate9Fn = IDirect3D9* (WINAPI*)(UINT);
using CreateDeviceFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3D9*, UINT, D3DDEVTYPE, HWND, DWORD, D3DPRESENT_PARAMETERS*, IDirect3DDevice9**);
using PresentFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, const RECT*, const RECT*, HWND, const RGNDATA*);
using CreateVertexDeclarationFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, const D3DVERTEXELEMENT9*, IDirect3DVertexDeclaration9**);
using SetVertexDeclarationFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, IDirect3DVertexDeclaration9*);
using SetStreamSourceFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, UINT, IDirect3DVertexBuffer9*, UINT, UINT);
using SetIndicesFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, IDirect3DIndexBuffer9*);
using SetTextureFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, DWORD, IDirect3DBaseTexture9*);
using CreateVertexShaderFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, const DWORD*, IDirect3DVertexShader9**);
using SetVertexShaderFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, IDirect3DVertexShader9*);
using SetVertexShaderConstantFFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, UINT, const float*, UINT);
using CreatePixelShaderFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, const DWORD*, IDirect3DPixelShader9**);
using SetPixelShaderFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, IDirect3DPixelShader9*);
using SetPixelShaderConstantFFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, UINT, const float*, UINT);
using DrawIndexedPrimitiveFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, D3DPRIMITIVETYPE, INT, UINT, UINT, UINT, UINT);

HMODULE g_system_d3d9 = nullptr;
Direct3DCreate9Fn g_real_direct3d_create9 = nullptr;
CreateDeviceFn g_real_create_device = nullptr;
PresentFn g_real_present = nullptr;
CreateVertexDeclarationFn g_real_create_vertex_declaration = nullptr;
SetVertexDeclarationFn g_real_set_vertex_declaration = nullptr;
SetStreamSourceFn g_real_set_stream_source = nullptr;
SetIndicesFn g_real_set_indices = nullptr;
SetTextureFn g_real_set_texture = nullptr;
CreateVertexShaderFn g_real_create_vertex_shader = nullptr;
SetVertexShaderFn g_real_set_vertex_shader = nullptr;
SetVertexShaderConstantFFn g_real_set_vertex_shader_constant_f = nullptr;
CreatePixelShaderFn g_real_create_pixel_shader = nullptr;
SetPixelShaderFn g_real_set_pixel_shader = nullptr;
SetPixelShaderConstantFFn g_real_set_pixel_shader_constant_f = nullptr;
DrawIndexedPrimitiveFn g_real_draw_indexed_primitive = nullptr;

std::mutex g_hook_mutex;
std::atomic<unsigned long long> g_event_index{0};
std::atomic<unsigned long long> g_frame{0};

struct CaptureWriter {
    std::mutex mutex;
    std::ofstream out;
    std::string path;
    bool initialized = false;

    void ensure_open() {
        if (initialized) return;
        const char* env = std::getenv("SHIFT_D3D9_CAPTURE");
        path = (env && *env) ? env : "shift_d3d9_capture.jsonl";
        out.open(path, std::ios::out | std::ios::app);
        initialized = true;
    }

    static std::string quote(const std::string& value) {
        std::ostringstream s;
        s << '"';
        for (unsigned char c : value) {
            switch (c) {
            case '\\': s << "\\\\"; break;
            case '"': s << "\\\""; break;
            case '\n': s << "\\n"; break;
            case '\r': s << "\\r"; break;
            case '\t': s << "\\t"; break;
            default:
                if (c < 0x20) {
                    s << "\\u"
                      << std::hex << std::setw(4) << std::setfill('0')
                      << static_cast<unsigned>(c)
                      << std::dec << std::setfill(' ');
                } else {
                    s << static_cast<char>(c);
                }
            }
        }
        s << '"';
        return s.str();
    }

    static std::string ptr(const void* value) {
        if (!value) return "null";
        std::ostringstream s;
        s << '"' << "0x" << std::hex
          << reinterpret_cast<std::uintptr_t>(value) << '"';
        return s.str();
    }

    static std::string hex_bytes(const std::vector<unsigned char>& bytes) {
        std::ostringstream s;
        s << std::hex << std::setfill('0');
        for (unsigned char b : bytes) s << std::setw(2) << static_cast<unsigned>(b);
        return s.str();
    }

    static std::string float_json(float value) {
        if (!std::isfinite(value)) return "null";
        std::ostringstream s;
        s.imbue(std::locale::classic());
        s << std::setprecision(std::numeric_limits<float>::max_digits10) << value;
        return s.str();
    }

    void write_event(const std::string& event, const std::string& fields) {
        std::lock_guard<std::mutex> lock(mutex);
        ensure_open();
        if (!out.is_open()) return;
        const auto seq = g_event_index.fetch_add(1);
        out << "{\"event_index\":" << seq
            << ",\"frame\":" << g_frame.load()
            << ",\"thread_id\":" << GetCurrentThreadId()
            << ",\"event\":" << quote(event);
        if (!fields.empty()) out << "," << fields;
        out << "}\n";
        const char* flush_env = std::getenv("SHIFT_D3D9_CAPTURE_FLUSH");
        if (!flush_env || std::string(flush_env) != "0") out.flush();
    }
};

CaptureWriter& writer() {
    static CaptureWriter value;
    return value;
}

std::vector<unsigned char> copy_declaration(const D3DVERTEXELEMENT9* declaration) {
    std::vector<unsigned char> bytes;
    if (!declaration) return bytes;
    constexpr std::size_t MAX_ELEMENTS = 64;
    for (std::size_t i = 0; i < MAX_ELEMENTS; ++i) {
        const auto* element = declaration + i;
        const auto* raw = reinterpret_cast<const unsigned char*>(element);
        bytes.insert(bytes.end(), raw, raw + sizeof(D3DVERTEXELEMENT9));
        if (element->Stream == 0xFF) return bytes;
    }
    return {};
}

std::vector<unsigned char> copy_shader(const DWORD* shader) {
    std::vector<unsigned char> bytes;
    if (!shader) return bytes;
    constexpr std::size_t MAX_DWORDS = 1u << 20;
    constexpr DWORD SHADER_END = 0x0000FFFFu;
    for (std::size_t i = 0; i < MAX_DWORDS; ++i) {
        const DWORD value = shader[i];
        const auto* raw = reinterpret_cast<const unsigned char*>(&value);
        bytes.insert(bytes.end(), raw, raw + sizeof(DWORD));
        if (value == SHADER_END) return bytes;
    }
    return {};
}

void patch_object_vtable(
    void* object,
    std::size_t count,
    std::size_t slot,
    void* hook,
    void** original_out) {

    if (!object || slot >= count) return;
    auto*** object_vtable = reinterpret_cast<void***>(object);
    void** original_vtable = *object_vtable;
    if (!original_vtable) return;

    const std::size_t bytes = count * sizeof(void*);
    auto* clone = static_cast<void**>(HeapAlloc(GetProcessHeap(), 0, bytes));
    if (!clone) return;
    std::memcpy(clone, original_vtable, bytes);

    if (original_out) *original_out = original_vtable[slot];

    DWORD old_protect = 0;
    if (!VirtualProtect(object_vtable, sizeof(void*), PAGE_READWRITE, &old_protect)) {
        HeapFree(GetProcessHeap(), 0, clone);
        return;
    }
    *object_vtable = clone;
    VirtualProtect(object_vtable, sizeof(void*), old_protect, &old_protect);
    clone[slot] = hook;
}

void patch_device(IDirect3DDevice9* device);

HRESULT STDMETHODCALLTYPE hook_create_device(
    IDirect3D9* self,
    UINT adapter,
    D3DDEVTYPE type,
    HWND window,
    DWORD behavior_flags,
    D3DPRESENT_PARAMETERS* params,
    IDirect3DDevice9** out_device) {
    const HRESULT hr = g_real_create_device
        ? g_real_create_device(self, adapter, type, window, behavior_flags, params, out_device)
        : E_FAIL;
    if (SUCCEEDED(hr) && out_device && *out_device) patch_device(*out_device);
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_present(
    IDirect3DDevice9* self,
    const RECT* src,
    const RECT* dst,
    HWND override_window,
    const RGNDATA* dirty_region) {
    const HRESULT hr = g_real_present
        ? g_real_present(self, src, dst, override_window, dirty_region)
        : E_FAIL;
    if (SUCCEEDED(hr)) g_frame.fetch_add(1);
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_create_vertex_declaration(
    IDirect3DDevice9* self,
    const D3DVERTEXELEMENT9* declaration,
    IDirect3DVertexDeclaration9** out_decl) {
    const HRESULT hr = g_real_create_vertex_declaration
        ? g_real_create_vertex_declaration(self, declaration, out_decl)
        : E_FAIL;
    if (SUCCEEDED(hr) && out_decl && *out_decl) {
        const auto bytes = copy_declaration(declaration);
        std::ostringstream f;
        f << "\"declaration_ptr\":" << CaptureWriter::ptr(*out_decl)
          << ",\"device_ptr\":" << CaptureWriter::ptr(self)
          << ",\"bytes_hex\":\"" << CaptureWriter::hex_bytes(bytes) << "\"";
        writer().write_event("create_vertex_declaration", f.str());
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_set_vertex_declaration(
    IDirect3DDevice9* self,
    IDirect3DVertexDeclaration9* decl) {
    const HRESULT hr = g_real_set_vertex_declaration
        ? g_real_set_vertex_declaration(self, decl)
        : E_FAIL;
    if (SUCCEEDED(hr)) {
        std::ostringstream f;
        f << "\"declaration_ptr\":" << CaptureWriter::ptr(decl)
          << ",\"device_ptr\":" << CaptureWriter::ptr(self);
        writer().write_event("set_vertex_declaration", f.str());
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_set_stream_source(
    IDirect3DDevice9* self,
    UINT stream,
    IDirect3DVertexBuffer9* buffer,
    UINT offset,
    UINT stride) {
    const HRESULT hr = g_real_set_stream_source
        ? g_real_set_stream_source(self, stream, buffer, offset, stride)
        : E_FAIL;
    if (SUCCEEDED(hr)) {
        std::ostringstream f;
        f << "\"vertex_buffer_ptr\":" << CaptureWriter::ptr(buffer)
          << ",\"device_ptr\":" << CaptureWriter::ptr(self)
          << ",\"stream\":" << stream
          << ",\"offset_in_bytes\":" << offset
          << ",\"stride\":" << stride;
        writer().write_event("set_stream_source", f.str());
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_set_indices(
    IDirect3DDevice9* self,
    IDirect3DIndexBuffer9* buffer) {
    const HRESULT hr = g_real_set_indices
        ? g_real_set_indices(self, buffer)
        : E_FAIL;
    if (SUCCEEDED(hr)) {
        std::ostringstream f;
        f << "\"index_buffer_ptr\":" << CaptureWriter::ptr(buffer)
          << ",\"device_ptr\":" << CaptureWriter::ptr(self);
        writer().write_event("set_indices", f.str());
    }
    return hr;
}



const char* d3d_resource_type_name(D3DRESOURCETYPE type) {
    switch (type) {
    case D3DRTYPE_TEXTURE: return "texture2d";
    case D3DRTYPE_VOLUMETEXTURE: return "volume_texture";
    case D3DRTYPE_CUBETEXTURE: return "cube_texture";
    default: return "other";
    }
}

void append_texture_descriptor_json(
    std::ostringstream& out,
    IDirect3DBaseTexture9* texture) {
    if (!texture) {
        out << ",\"resource_descriptor_status\":\"null\"";
        return;
    }

    const D3DRESOURCETYPE type = texture->GetType();
    out << ",\"resource_type\":" << static_cast<unsigned>(type)
        << ",\"resource_type_name\":\""
        << d3d_resource_type_name(type) << "\"";

    D3DSURFACE_DESC surface{};
    HRESULT hr = E_FAIL;
    if (type == D3DRTYPE_TEXTURE) {
        hr = static_cast<IDirect3DTexture9*>(texture)->GetLevelDesc(0, &surface);
    } else if (type == D3DRTYPE_CUBETEXTURE) {
        hr = static_cast<IDirect3DCubeTexture9*>(texture)->GetLevelDesc(0, &surface);
    }
    if (SUCCEEDED(hr)) {
        out << ",\"resource_descriptor_status\":\"observed\""
            << ",\"width\":" << surface.Width
            << ",\"height\":" << surface.Height
            << ",\"format\":" << static_cast<unsigned>(surface.Format)
            << ",\"mip_levels\":" << surface.Pool;
        // Pool is intentionally not exposed as mip_levels; replace with the
        // actual base-texture level count below.
    } else {
        out << ",\"resource_descriptor_status\":\"type-only\"";
    }

    if (type == D3DRTYPE_TEXTURE) {
        out << ",\"level_count\":"
            << static_cast<unsigned>(static_cast<IDirect3DTexture9*>(texture)->GetLevelCount());
    } else if (type == D3DRTYPE_CUBETEXTURE) {
        out << ",\"level_count\":"
            << static_cast<unsigned>(static_cast<IDirect3DCubeTexture9*>(texture)->GetLevelCount());
    } else if (type == D3DRTYPE_VOLUMETEXTURE) {
        D3DVOLUME_DESC volume{};
        if (SUCCEEDED(static_cast<IDirect3DVolumeTexture9*>(texture)->GetLevelDesc(0, &volume))) {
            out << ",\"resource_descriptor_status\":\"observed\""
                << ",\"width\":" << volume.Width
                << ",\"height\":" << volume.Height
                << ",\"depth\":" << volume.Depth
                << ",\"format\":" << static_cast<unsigned>(volume.Format)
                << ",\"level_count\":"
                << static_cast<unsigned>(static_cast<IDirect3DVolumeTexture9*>(texture)->GetLevelCount());
        }
    }
}

HRESULT STDMETHODCALLTYPE hook_set_texture(
    IDirect3DDevice9* self,
    DWORD stage,
    IDirect3DBaseTexture9* texture) {
    const HRESULT hr = g_real_set_texture
        ? g_real_set_texture(self, stage, texture)
        : E_FAIL;
    if (SUCCEEDED(hr)) {
        std::ostringstream f;
        f << "\"texture_ptr\":" << CaptureWriter::ptr(texture)
          << ",\"device_ptr\":" << CaptureWriter::ptr(self)
          << ",\"stage\":" << stage;
        append_texture_descriptor_json(f, texture);
        writer().write_event("set_texture", f.str());
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_create_vertex_shader(
    IDirect3DDevice9* self,
    const DWORD* function,
    IDirect3DVertexShader9** out_shader) {
    const HRESULT hr = g_real_create_vertex_shader
        ? g_real_create_vertex_shader(self, function, out_shader)
        : E_FAIL;
    if (SUCCEEDED(hr) && out_shader && *out_shader) {
        const auto bytes = copy_shader(function);
        std::ostringstream f;
        f << "\"shader_ptr\":" << CaptureWriter::ptr(*out_shader)
          << ",\"device_ptr\":" << CaptureWriter::ptr(self)
          << ",\"bytes_hex\":\"" << CaptureWriter::hex_bytes(bytes) << "\"";
        writer().write_event("create_vertex_shader", f.str());
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_set_vertex_shader(
    IDirect3DDevice9* self,
    IDirect3DVertexShader9* shader) {
    const HRESULT hr = g_real_set_vertex_shader
        ? g_real_set_vertex_shader(self, shader)
        : E_FAIL;
    if (SUCCEEDED(hr)) {
        std::ostringstream f;
        f << "\"shader_ptr\":" << CaptureWriter::ptr(shader)
          << ",\"device_ptr\":" << CaptureWriter::ptr(self);
        writer().write_event("set_vertex_shader", f.str());
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_set_vertex_shader_constant_f(
    IDirect3DDevice9* self,
    UINT start_register,
    const float* data,
    UINT vector4f_count) {
    const HRESULT hr = g_real_set_vertex_shader_constant_f
        ? g_real_set_vertex_shader_constant_f(self, start_register, data, vector4f_count)
        : E_FAIL;
    if (SUCCEEDED(hr) && data && vector4f_count) {
        std::ostringstream f;
        f << "\"device_ptr\":" << CaptureWriter::ptr(self)
          << ",\"start_register\":" << start_register
          << ",\"vector4f_count\":" << vector4f_count
          << ",\"values\":[";
        const std::size_t count = static_cast<std::size_t>(vector4f_count) * 4u;
        for (std::size_t i = 0; i < count; ++i) {
            if (i) f << ",";
            f << CaptureWriter::float_json(data[i]);
        }
        f << "]";
        writer().write_event("set_vertex_shader_constant_f", f.str());
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_create_pixel_shader(
    IDirect3DDevice9* self,
    const DWORD* function,
    IDirect3DPixelShader9** out_shader) {
    const HRESULT hr = g_real_create_pixel_shader
        ? g_real_create_pixel_shader(self, function, out_shader)
        : E_FAIL;
    if (SUCCEEDED(hr) && out_shader && *out_shader) {
        const auto bytes = copy_shader(function);
        std::ostringstream f;
        f << "\"shader_ptr\":" << CaptureWriter::ptr(*out_shader)
          << ",\"device_ptr\":" << CaptureWriter::ptr(self)
          << ",\"bytes_hex\":\"" << CaptureWriter::hex_bytes(bytes) << "\"";
        writer().write_event("create_pixel_shader", f.str());
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_set_pixel_shader(
    IDirect3DDevice9* self,
    IDirect3DPixelShader9* shader) {
    const HRESULT hr = g_real_set_pixel_shader
        ? g_real_set_pixel_shader(self, shader)
        : E_FAIL;
    if (SUCCEEDED(hr)) {
        std::ostringstream f;
        f << "\"shader_ptr\":" << CaptureWriter::ptr(shader)
          << ",\"device_ptr\":" << CaptureWriter::ptr(self);
        writer().write_event("set_pixel_shader", f.str());
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_set_pixel_shader_constant_f(
    IDirect3DDevice9* self,
    UINT start_register,
    const float* data,
    UINT vector4f_count) {
    const HRESULT hr = g_real_set_pixel_shader_constant_f
        ? g_real_set_pixel_shader_constant_f(self, start_register, data, vector4f_count)
        : E_FAIL;
    if (SUCCEEDED(hr) && data && vector4f_count) {
        std::ostringstream f;
        f << "\"device_ptr\":" << CaptureWriter::ptr(self)
          << ",\"start_register\":" << start_register
          << ",\"vector4f_count\":" << vector4f_count
          << ",\"values\":[";
        const std::size_t count = static_cast<std::size_t>(vector4f_count) * 4u;
        for (std::size_t i = 0; i < count; ++i) {
            if (i) f << ",";
            f << CaptureWriter::float_json(data[i]);
        }
        f << "]";
        writer().write_event("set_pixel_shader_constant_f", f.str());
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_draw_indexed_primitive(
    IDirect3DDevice9* self,
    D3DPRIMITIVETYPE primitive_type,
    INT base_vertex_index,
    UINT min_vertex_index,
    UINT num_vertices,
    UINT start_index,
    UINT primitive_count) {
    const HRESULT hr = g_real_draw_indexed_primitive
        ? g_real_draw_indexed_primitive(
            self, primitive_type, base_vertex_index, min_vertex_index,
            num_vertices, start_index, primitive_count)
        : E_FAIL;
    if (SUCCEEDED(hr)) {
        std::ostringstream f;
        f << "\"device_ptr\":" << CaptureWriter::ptr(self)
          << ",\"primitive_type\":" << static_cast<unsigned>(primitive_type)
          << ",\"base_vertex_index\":" << base_vertex_index
          << ",\"min_vertex_index\":" << min_vertex_index
          << ",\"num_vertices\":" << num_vertices
          << ",\"start_index\":" << start_index
          << ",\"primitive_count\":" << primitive_count;
        writer().write_event("draw_indexed_primitive", f.str());
    }
    return hr;
}

void patch_device(IDirect3DDevice9* device) {
    std::lock_guard<std::mutex> lock(g_hook_mutex);

    patch_object_vtable(device, D3D9_VTABLE_COUNT, SLOT_PRESENT,
                        reinterpret_cast<void*>(&hook_present),
                        reinterpret_cast<void**>(&g_real_present));
    patch_object_vtable(device, D3D9_VTABLE_COUNT, SLOT_CREATE_VERTEX_DECLARATION,
                        reinterpret_cast<void*>(&hook_create_vertex_declaration),
                        reinterpret_cast<void**>(&g_real_create_vertex_declaration));
    patch_object_vtable(device, D3D9_VTABLE_COUNT, SLOT_SET_VERTEX_DECLARATION,
                        reinterpret_cast<void*>(&hook_set_vertex_declaration),
                        reinterpret_cast<void**>(&g_real_set_vertex_declaration));
    patch_object_vtable(device, D3D9_VTABLE_COUNT, SLOT_SET_STREAM_SOURCE,
                        reinterpret_cast<void*>(&hook_set_stream_source),
                        reinterpret_cast<void**>(&g_real_set_stream_source));
    patch_object_vtable(device, D3D9_VTABLE_COUNT, SLOT_SET_INDICES,
                        reinterpret_cast<void*>(&hook_set_indices),
                        reinterpret_cast<void**>(&g_real_set_indices));
    patch_object_vtable(device, D3D9_VTABLE_COUNT, SLOT_SET_TEXTURE,
                        reinterpret_cast<void*>(&hook_set_texture),
                        reinterpret_cast<void**>(&g_real_set_texture));
    patch_object_vtable(device, D3D9_VTABLE_COUNT, SLOT_CREATE_VERTEX_SHADER,
                        reinterpret_cast<void*>(&hook_create_vertex_shader),
                        reinterpret_cast<void**>(&g_real_create_vertex_shader));
    patch_object_vtable(device, D3D9_VTABLE_COUNT, SLOT_SET_VERTEX_SHADER,
                        reinterpret_cast<void*>(&hook_set_vertex_shader),
                        reinterpret_cast<void**>(&g_real_set_vertex_shader));
    patch_object_vtable(device, D3D9_VTABLE_COUNT, SLOT_SET_VERTEX_SHADER_CONSTANT_F,
                        reinterpret_cast<void*>(&hook_set_vertex_shader_constant_f),
                        reinterpret_cast<void**>(&g_real_set_vertex_shader_constant_f));
    patch_object_vtable(device, D3D9_VTABLE_COUNT, SLOT_CREATE_PIXEL_SHADER,
                        reinterpret_cast<void*>(&hook_create_pixel_shader),
                        reinterpret_cast<void**>(&g_real_create_pixel_shader));
    patch_object_vtable(device, D3D9_VTABLE_COUNT, SLOT_SET_PIXEL_SHADER,
                        reinterpret_cast<void*>(&hook_set_pixel_shader),
                        reinterpret_cast<void**>(&g_real_set_pixel_shader));
    patch_object_vtable(device, D3D9_VTABLE_COUNT, SLOT_SET_PIXEL_SHADER_CONSTANT_F,
                        reinterpret_cast<void*>(&hook_set_pixel_shader_constant_f),
                        reinterpret_cast<void**>(&g_real_set_pixel_shader_constant_f));
    patch_object_vtable(device, D3D9_VTABLE_COUNT, SLOT_DRAW_INDEXED_PRIMITIVE,
                        reinterpret_cast<void*>(&hook_draw_indexed_primitive),
                        reinterpret_cast<void**>(&g_real_draw_indexed_primitive));
}

void patch_direct3d9(IDirect3D9* d3d) {
    std::lock_guard<std::mutex> lock(g_hook_mutex);
    void** vtable = *reinterpret_cast<void***>(d3d);
    if (!vtable) return;
    g_real_create_device = reinterpret_cast<CreateDeviceFn>(vtable[16]);
    patch_object_vtable(d3d, IDIRECT3D9_VTABLE_COUNT, 16,
                        reinterpret_cast<void*>(&hook_create_device), nullptr);
}

bool ensure_system_d3d9() {
    if (g_real_direct3d_create9) return true;
    wchar_t system_dir[MAX_PATH] = {};
    const UINT length = GetSystemDirectoryW(system_dir, MAX_PATH);
    if (!length || length >= MAX_PATH) return false;

    std::wstring path(system_dir, length);
    path += L"\\d3d9.dll";
    g_system_d3d9 = LoadLibraryW(path.c_str());
    if (!g_system_d3d9) return false;

    g_real_direct3d_create9 =
        reinterpret_cast<Direct3DCreate9Fn>(
            GetProcAddress(g_system_d3d9, "Direct3DCreate9"));
    return g_real_direct3d_create9 != nullptr;
}

} // namespace

extern "C" __declspec(dllexport)
IDirect3D9* WINAPI Direct3DCreate9(UINT sdk_version) {
    if (!ensure_system_d3d9()) return nullptr;
    IDirect3D9* d3d = g_real_direct3d_create9(sdk_version);
    if (d3d) patch_direct3d9(d3d);
    return d3d;
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) DisableThreadLibraryCalls(instance);
    if (reason == DLL_PROCESS_DETACH && g_system_d3d9) FreeLibrary(g_system_d3d9);
    return TRUE;
}

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#define Direct3DCreate9 SHIFT_SYSTEM_Direct3DCreate9
#include <d3d9.h>
#undef Direct3DCreate9

#include "capture_helpers.h"

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cctype>
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
#include <unordered_map>

namespace {

constexpr std::size_t D3D9_VTABLE_COUNT = 119;
constexpr std::size_t IDIRECT3D9_VTABLE_COUNT = 17;
constexpr std::size_t TEXTURE_VTABLE_COUNT = 22;
constexpr std::size_t CUBE_TEXTURE_VTABLE_COUNT = 22;
constexpr std::size_t BUFFER_VTABLE_COUNT = 14;

constexpr std::size_t SLOT_TEST_COOPERATIVE_LEVEL = 3;
constexpr std::size_t SLOT_RESET = 16;
constexpr std::size_t SLOT_PRESENT = 17;
constexpr std::size_t SLOT_BEGIN_SCENE = 41;
constexpr std::size_t SLOT_END_SCENE = 42;
constexpr std::size_t SLOT_CLEAR = 43;
constexpr std::size_t SLOT_CREATE_TEXTURE = 23;
constexpr std::size_t SLOT_CREATE_CUBE_TEXTURE = 25;
constexpr std::size_t SLOT_CREATE_VERTEX_BUFFER = 26;
constexpr std::size_t SLOT_CREATE_INDEX_BUFFER = 27;
constexpr std::size_t SLOT_BUFFER_LOCK = 11;
constexpr std::size_t SLOT_BUFFER_UNLOCK = 12;
constexpr std::size_t SLOT_TEXTURE_LOCK_RECT = 19;
constexpr std::size_t SLOT_TEXTURE_UNLOCK_RECT = 20;
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
using Direct3DCreate9ExFn = HRESULT (WINAPI*)(UINT, IDirect3D9Ex**);
using D3DPERFBeginEventFn = int (WINAPI*)(D3DCOLOR, LPCWSTR);
using D3DPERFEndEventFn = int (WINAPI*)();
using D3DPERFGetStatusFn = DWORD (WINAPI*)();
using D3DPERFQueryRepeatFrameFn = BOOL (WINAPI*)();
using D3DPERFSetMarkerFn = void (WINAPI*)(D3DCOLOR, LPCWSTR);
using D3DPERFSetOptionsFn = void (WINAPI*)(DWORD);
using D3DPERFSetRegionFn = void (WINAPI*)(D3DCOLOR, LPCWSTR);
using DebugSetLevelFn = void (WINAPI*)(DWORD);
using DebugSetMuteFn = void (WINAPI*)();
using CreateDeviceFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3D9*, UINT, D3DDEVTYPE, HWND, DWORD, D3DPRESENT_PARAMETERS*, IDirect3DDevice9**);
using TestCooperativeLevelFn = HRESULT (STDMETHODCALLTYPE*)(IDirect3DDevice9*);
using ResetFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, D3DPRESENT_PARAMETERS*);
using PresentFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, const RECT*, const RECT*, HWND, const RGNDATA*);
using BeginSceneFn = HRESULT (STDMETHODCALLTYPE*)(IDirect3DDevice9*);
using EndSceneFn = HRESULT (STDMETHODCALLTYPE*)(IDirect3DDevice9*);
using ClearFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, DWORD, const D3DRECT*, DWORD, D3DCOLOR, float, DWORD);
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
using CreateTextureFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, UINT, UINT, UINT, DWORD, D3DFORMAT, D3DPOOL, IDirect3DTexture9**, HANDLE*);
using CreateCubeTextureFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, UINT, UINT, DWORD, D3DFORMAT, D3DPOOL, IDirect3DCubeTexture9**, HANDLE*);
using CreateVertexBufferFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, UINT, DWORD, DWORD, D3DPOOL, IDirect3DVertexBuffer9**, HANDLE*);
using CreateIndexBufferFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DDevice9*, UINT, DWORD, D3DFORMAT, D3DPOOL, IDirect3DIndexBuffer9**, HANDLE*);
using VertexBufferLockFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DVertexBuffer9*, UINT, UINT, void**, DWORD);
using VertexBufferUnlockFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DVertexBuffer9*);
using IndexBufferLockFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DIndexBuffer9*, UINT, UINT, void**, DWORD);
using IndexBufferUnlockFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DIndexBuffer9*);
using TextureLockRectFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DTexture9*, UINT, D3DLOCKED_RECT*, const RECT*, DWORD);
using TextureUnlockRectFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DTexture9*, UINT);
using CubeTextureLockRectFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DCubeTexture9*, D3DCUBEMAP_FACES, UINT, D3DLOCKED_RECT*, const RECT*, DWORD);
using CubeTextureUnlockRectFn = HRESULT (STDMETHODCALLTYPE*)(
    IDirect3DCubeTexture9*, D3DCUBEMAP_FACES, UINT);
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

HMODULE g_proxy_module = nullptr;
HMODULE g_system_d3d9 = nullptr;
std::once_flag g_system_d3d9_once;
bool g_system_d3d9_ready = false;
std::string g_system_d3d9_path;
Direct3DCreate9Fn g_real_direct3d_create9 = nullptr;
Direct3DCreate9ExFn g_real_direct3d_create9_ex = nullptr;
D3DPERFBeginEventFn g_real_d3dperf_begin_event = nullptr;
D3DPERFEndEventFn g_real_d3dperf_end_event = nullptr;
D3DPERFGetStatusFn g_real_d3dperf_get_status = nullptr;
D3DPERFQueryRepeatFrameFn g_real_d3dperf_query_repeat_frame = nullptr;
D3DPERFSetMarkerFn g_real_d3dperf_set_marker = nullptr;
D3DPERFSetOptionsFn g_real_d3dperf_set_options = nullptr;
D3DPERFSetRegionFn g_real_d3dperf_set_region = nullptr;
DebugSetLevelFn g_real_debug_set_level = nullptr;
DebugSetMuteFn g_real_debug_set_mute = nullptr;
CreateDeviceFn g_real_create_device = nullptr;
TestCooperativeLevelFn g_real_test_cooperative_level = nullptr;
ResetFn g_real_reset = nullptr;
PresentFn g_real_present = nullptr;
BeginSceneFn g_real_begin_scene = nullptr;
EndSceneFn g_real_end_scene = nullptr;
ClearFn g_real_clear = nullptr;
CreateVertexDeclarationFn g_real_create_vertex_declaration = nullptr;
SetVertexDeclarationFn g_real_set_vertex_declaration = nullptr;
CreateTextureFn g_real_create_texture = nullptr;
CreateCubeTextureFn g_real_create_cube_texture = nullptr;
CreateVertexBufferFn g_real_create_vertex_buffer = nullptr;
CreateIndexBufferFn g_real_create_index_buffer = nullptr;
VertexBufferLockFn g_real_vertex_buffer_lock = nullptr;
VertexBufferUnlockFn g_real_vertex_buffer_unlock = nullptr;
IndexBufferLockFn g_real_index_buffer_lock = nullptr;
IndexBufferUnlockFn g_real_index_buffer_unlock = nullptr;
TextureLockRectFn g_real_texture_lock_rect = nullptr;
TextureUnlockRectFn g_real_texture_unlock_rect = nullptr;
CubeTextureLockRectFn g_real_cube_texture_lock_rect = nullptr;
CubeTextureUnlockRectFn g_real_cube_texture_unlock_rect = nullptr;
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
std::atomic<bool> g_proxy_entry_reported{false};
std::atomic<unsigned long long> g_perf_event_calls{0};
std::atomic<unsigned long long> g_present_calls{0};

enum class CaptureMode {
    Passthrough,
    Diagnostic,
    Capture,
};

CaptureMode capture_mode() {
    static const CaptureMode mode = [] {
        const char* value = std::getenv("SHIFT_D3D9_CAPTURE_MODE");
        if (!value || !*value) return CaptureMode::Capture;
        std::string text(value);
        std::transform(text.begin(), text.end(), text.begin(), [](unsigned char c) {
            return static_cast<char>(std::tolower(c));
        });
        if (text == "passthrough" || text == "off" || text == "0") {
            return CaptureMode::Passthrough;
        }
        if (text == "diagnostic" || text == "diag" || text == "1") {
            return CaptureMode::Diagnostic;
        }
        return CaptureMode::Capture;
    }();
    return mode;
}

const char* capture_mode_name() {
    switch (capture_mode()) {
    case CaptureMode::Passthrough: return "passthrough";
    case CaptureMode::Diagnostic: return "diagnostic";
    case CaptureMode::Capture: return "capture";
    }
    return "capture";
}

std::string hresult_hex(HRESULT hr) {
    std::ostringstream s;
    s << "\"0x" << std::hex << std::setw(8) << std::setfill('0')
      << static_cast<unsigned long>(hr) << "\"";
    return s.str();
}

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
        if (!out.is_open() && (!env || !*env)) {
            char temp_path[MAX_PATH] = {};
            const DWORD length = GetTempPathA(MAX_PATH, temp_path);
            if (length > 0 && length < MAX_PATH) {
                path.assign(temp_path, length);
                if (!path.empty() && path.back() != '\\' && path.back() != '/') {
                    path.push_back('\\');
                }
                path += "shift_d3d9_capture.jsonl";
                out.clear();
                out.open(path, std::ios::out | std::ios::app);
            }
        }
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
        const auto seq = g_event_index.fetch_add(1);
        std::ostringstream line;
        line << "{\"event_index\":" << seq
             << ",\"frame\":" << g_frame.load()
             << ",\"tick_ms\":" << GetTickCount64()
             << ",\"process_id\":" << GetCurrentProcessId()
             << ",\"thread_id\":" << GetCurrentThreadId()
             << ",\"event\":" << quote(event);
        if (!fields.empty()) line << "," << fields;
        line << "}\n";

        if (out.is_open()) {
            out << line.str();
            const char* flush_env = std::getenv("SHIFT_D3D9_CAPTURE_FLUSH");
            if (!flush_env || std::string(flush_env) != "0") out.flush();
        }
        const char* debug_env = std::getenv("SHIFT_D3D9_CAPTURE_DEBUG_OUTPUT");
        const bool debug_output =
            debug_env && *debug_env &&
            std::string(debug_env) != "0" &&
            std::string(debug_env) != "false";
        if (debug_output || !out.is_open()) {
            OutputDebugStringA(line.str().c_str());
        }
    }
};

CaptureWriter& writer() {
    static CaptureWriter value;
    return value;
}


bool env_enabled(const char* name) {
    const char* value = std::getenv(name);
    if (!value || !*value) return false;
    return std::string(value) != "0" && std::string(value) != "false";
}

unsigned long long env_u64(const char* name, unsigned long long fallback) {
    const char* value = std::getenv(name);
    if (!value || !*value) return fallback;
    char* end = nullptr;
    unsigned long long parsed = std::strtoull(value, &end, 0);
    return (end && *end == '\0') ? parsed : fallback;
}

bool write_backbuffer_ppm(
    IDirect3DDevice9* device,
    IDirect3DSurface9* backbuffer,
    unsigned long long frame,
    std::string& output_path) {
    if (!device || !backbuffer) return false;

    D3DSURFACE_DESC desc{};
    if (FAILED(backbuffer->GetDesc(&desc))) return false;
    const bool supported_format =
        desc.Format == D3DFMT_A8R8G8B8 ||
        desc.Format == D3DFMT_X8R8G8B8 ||
        desc.Format == D3DFMT_R5G6B5;
    if (!supported_format) return false;

    IDirect3DSurface9* staging = nullptr;
    if (FAILED(device->CreateOffscreenPlainSurface(
            desc.Width, desc.Height, desc.Format,
            D3DPOOL_SYSTEMMEM, &staging, nullptr))) {
        return false;
    }

    bool ok = SUCCEEDED(device->GetRenderTargetData(backbuffer, staging));
    D3DLOCKED_RECT locked{};
    bool locked_ok = false;
    if (ok) {
        ok = SUCCEEDED(staging->LockRect(
            &locked, nullptr, D3DLOCK_READONLY));
        locked_ok = ok;
    }

    if (ok) {
        const char* directory = std::getenv("SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR");
        std::string dir = (directory && *directory) ? directory : ".";
        if (!dir.empty() && dir.back() != '\\' && dir.back() != '/') dir.push_back('\\');
        std::ostringstream filename;
        filename << dir << "shift_d3d9_frame_" << frame << ".ppm";
        output_path = filename.str();

        std::ofstream image(output_path, std::ios::binary);
        ok = image.is_open();
        if (ok) {
            image << "P6\n" << desc.Width << " " << desc.Height << "\n255\n";
            for (UINT y = 0; y < desc.Height && ok; ++y) {
                const auto* row = static_cast<const unsigned char*>(locked.pBits) +
                                  static_cast<std::size_t>(y) * locked.Pitch;
                for (UINT x = 0; x < desc.Width; ++x) {
                    unsigned char rgb[3]{};
                    if (desc.Format == D3DFMT_R5G6B5) {
                        const auto value =
                            *reinterpret_cast<const std::uint16_t*>(row + x * 2);
                        rgb[0] = static_cast<unsigned char>(((value >> 11) & 0x1f) * 255 / 31);
                        rgb[1] = static_cast<unsigned char>(((value >> 5) & 0x3f) * 255 / 63);
                        rgb[2] = static_cast<unsigned char>((value & 0x1f) * 255 / 31);
                    } else {
                        const auto* pixel = row + x * 4;
                        rgb[0] = pixel[2];
                        rgb[1] = pixel[1];
                        rgb[2] = pixel[0];
                    }
                    image.write(reinterpret_cast<const char*>(rgb), sizeof(rgb));
                    if (!image) {
                        ok = false;
                        break;
                    }
                }
            }
        }
    }

    if (locked_ok) staging->UnlockRect();
    staging->Release();
    return ok;
}



std::string capture_texture_snapshot_dir() {
    const char* directory = std::getenv("SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT_DIR");
    std::string value = (directory && *directory) ? directory : ".";
    if (!value.empty() && value.back() != '\\' && value.back() != '/') {
        value.push_back('\\');
    }
    return value;
}

bool texture_snapshot_stage_enabled(DWORD stage) {
    if (!env_enabled("SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT")) return false;
    const char* stages = std::getenv("SHIFT_D3D9_CAPTURE_TEXTURE_STAGES");
    std::string list = (stages && *stages) ? stages : "0,1,2,3,4";
    std::size_t begin = 0;
    while (begin < list.size()) {
        std::size_t end = list.find(',', begin);
        if (end == std::string::npos) end = list.size();
        std::string token = list.substr(begin, end - begin);
        char* parse_end = nullptr;
        unsigned long value = std::strtoul(token.c_str(), &parse_end, 0);
        if (parse_end != token.c_str() && *parse_end == '\0' && value == stage) {
            return true;
        }
        begin = end + 1;
    }
    return false;
}

const char* cube_face_name(D3DCUBEMAP_FACES face) {
    switch (face) {
    case D3DCUBEMAP_FACE_POSITIVE_X: return "px";
    case D3DCUBEMAP_FACE_NEGATIVE_X: return "nx";
    case D3DCUBEMAP_FACE_POSITIVE_Y: return "py";
    case D3DCUBEMAP_FACE_NEGATIVE_Y: return "ny";
    case D3DCUBEMAP_FACE_POSITIVE_Z: return "pz";
    case D3DCUBEMAP_FACE_NEGATIVE_Z: return "nz";
    default: return "unknown";
    }
}

bool write_texture_surface_ppm(
    IDirect3DDevice9* device,
    IDirect3DSurface9* source,
    const D3DSURFACE_DESC& desc,
    const std::string& output_path) {
    if (!device || !source) return false;
    const bool supported =
        desc.Format == D3DFMT_A8R8G8B8 ||
        desc.Format == D3DFMT_X8R8G8B8 ||
        desc.Format == D3DFMT_R5G6B5;
    if (!supported || desc.Width == 0 || desc.Height == 0) return false;

    IDirect3DSurface9* render_target = nullptr;
    if (FAILED(device->CreateRenderTarget(
            desc.Width, desc.Height, desc.Format,
            D3DMULTISAMPLE_NONE, 0, TRUE, &render_target, nullptr))) {
        return false;
    }

    bool ok = SUCCEEDED(device->StretchRect(
        source, nullptr, render_target, nullptr, D3DTEXF_NONE));

    IDirect3DSurface9* staging = nullptr;
    if (ok) {
        ok = SUCCEEDED(device->CreateOffscreenPlainSurface(
            desc.Width, desc.Height, desc.Format,
            D3DPOOL_SYSTEMMEM, &staging, nullptr));
    }
    if (ok) {
        ok = SUCCEEDED(device->GetRenderTargetData(render_target, staging));
    }

    D3DLOCKED_RECT locked{};
    if (ok) ok = SUCCEEDED(staging->LockRect(&locked, nullptr, D3DLOCK_READONLY));

    if (ok) {
        std::ofstream image(output_path, std::ios::binary);
        ok = image.is_open();
        if (ok) {
            image << "P6\n" << desc.Width << " " << desc.Height << "\n255\n";
            for (UINT y = 0; y < desc.Height && ok; ++y) {
                const auto* row = static_cast<const unsigned char*>(locked.pBits) +
                                  static_cast<std::size_t>(y) * locked.Pitch;
                for (UINT x = 0; x < desc.Width; ++x) {
                    unsigned char rgb[3]{};
                    if (desc.Format == D3DFMT_R5G6B5) {
                        const auto value =
                            *reinterpret_cast<const std::uint16_t*>(row + x * 2);
                        rgb[0] = static_cast<unsigned char>(((value >> 11) & 0x1f) * 255 / 31);
                        rgb[1] = static_cast<unsigned char>(((value >> 5) & 0x3f) * 255 / 63);
                        rgb[2] = static_cast<unsigned char>((value & 0x1f) * 255 / 31);
                    } else {
                        const auto* pixel = row + x * 4;
                        rgb[0] = pixel[2];
                        rgb[1] = pixel[1];
                        rgb[2] = pixel[0];
                    }
                    image.write(reinterpret_cast<const char*>(rgb), sizeof(rgb));
                    if (!image) {
                        ok = false;
                        break;
                    }
                }
            }
        }
    }

    if (staging && ok) staging->UnlockRect();
    if (staging) staging->Release();
    render_target->Release();
    return ok;
}

void append_texture_snapshot_json(
    std::ostringstream& out,
    IDirect3DDevice9* device,
    DWORD stage,
    IDirect3DBaseTexture9* texture) {
    if (!texture_snapshot_stage_enabled(stage) || !texture) return;

    const auto type = texture->GetType();
    const std::string dir = capture_texture_snapshot_dir();
    const std::string pointer_text = CaptureWriter::ptr(texture);
    std::ostringstream prefix;
    prefix << dir << "shift_d3d9_s" << stage << "_" << pointer_text.substr(1, pointer_text.size() - 2);

    if (type == D3DRTYPE_TEXTURE) {
        auto* tex = static_cast<IDirect3DTexture9*>(texture);
        IDirect3DSurface9* surface = nullptr;
        bool captured = false;
        if (SUCCEEDED(tex->GetSurfaceLevel(0, &surface))) {
            D3DSURFACE_DESC desc{};
            if (SUCCEEDED(surface->GetDesc(&desc))) {
                captured = write_texture_surface_ppm(
                    device, surface, desc, prefix.str() + ".ppm");
            }
            surface->Release();
        }
        out << ",\"snapshot_status\":" << CaptureWriter::quote(captured ? "captured" : "capture-failed");
        if (captured) {
            out << ",\"snapshot_paths\":[" << CaptureWriter::quote(prefix.str() + ".ppm") << "]";
        }
        return;
    }

    if (type == D3DRTYPE_CUBETEXTURE) {
        auto* cube = static_cast<IDirect3DCubeTexture9*>(texture);
        const D3DCUBEMAP_FACES faces[] = {
            D3DCUBEMAP_FACE_POSITIVE_X, D3DCUBEMAP_FACE_NEGATIVE_X,
            D3DCUBEMAP_FACE_POSITIVE_Y, D3DCUBEMAP_FACE_NEGATIVE_Y,
            D3DCUBEMAP_FACE_POSITIVE_Z, D3DCUBEMAP_FACE_NEGATIVE_Z,
        };
        bool captured_any = false;
        bool all_captured = true;
        std::ostringstream json_paths;
        bool first = true;
        for (const auto face : faces) {
            IDirect3DSurface9* surface = nullptr;
            bool captured = false;
            if (SUCCEEDED(cube->GetCubeMapSurface(face, 0, &surface))) {
                D3DSURFACE_DESC desc{};
                if (SUCCEEDED(surface->GetDesc(&desc))) {
                    std::string path = prefix.str() + "_" + cube_face_name(face) + ".ppm";
                    captured = write_texture_surface_ppm(device, surface, desc, path);
                    if (captured) {
                        if (!first) json_paths << ",";
                        json_paths << CaptureWriter::quote(path);
                        first = false;
                        captured_any = true;
                    }
                }
                surface->Release();
            }
            if (!captured) all_captured = false;
        }
        out << ",\"snapshot_status\":" << CaptureWriter::quote(all_captured ? "captured" : (captured_any ? "partial" : "capture-failed"));
        if (captured_any) {
            out << ",\"snapshot_paths\":[" << json_paths.str() << "]";
        }
        return;
    }

    out << ",\"snapshot_status\":\"unsupported-resource-type\"";
}

void append_texture_descriptor_json(
    std::ostringstream& out,
    IDirect3DBaseTexture9* texture);

struct VtablePatch {
    std::size_t slot = 0;
    void* hook = nullptr;
    void** original_out = nullptr;
};

bool patch_object_vtable_batch(
    void* object,
    std::size_t count,
    const std::vector<VtablePatch>& patches,
    const char* label) {

    if (!object || patches.empty()) return false;
    auto*** object_vtable = reinterpret_cast<void***>(object);
    void** original_vtable = *object_vtable;
    if (!original_vtable) return false;

    for (const auto& patch : patches) {
        if (patch.slot >= count || !patch.hook) {
            std::ostringstream fields;
            fields << "\"label\":" << CaptureWriter::quote(label ? label : "unknown")
                   << ",\"object_ptr\":" << CaptureWriter::ptr(object)
                   << ",\"reason\":\"invalid-slot-or-hook\"";
            writer().write_event("vtable_patch_failed", fields.str());
            return false;
        }
    }

    const std::size_t bytes = count * sizeof(void*);
    auto* clone = static_cast<void**>(HeapAlloc(GetProcessHeap(), 0, bytes));
    if (!clone) {
        writer().write_event("vtable_patch_failed", "\"reason\":\"heap-allocation-failed\"");
        return false;
    }
    std::memcpy(clone, original_vtable, bytes);

    bool changed = false;
    for (const auto& patch : patches) {
        if (original_vtable[patch.slot] == patch.hook) continue;
        if (patch.original_out) {
            *patch.original_out = original_vtable[patch.slot];
        }
        clone[patch.slot] = patch.hook;
        changed = true;
    }
    if (!changed) {
        HeapFree(GetProcessHeap(), 0, clone);
        return true;
    }

    DWORD old_protect = 0;
    if (!VirtualProtect(object_vtable, sizeof(void*), PAGE_READWRITE, &old_protect)) {
        const DWORD error = GetLastError();
        HeapFree(GetProcessHeap(), 0, clone);
        std::ostringstream fields;
        fields << "\"label\":" << CaptureWriter::quote(label ? label : "unknown")
               << ",\"object_ptr\":" << CaptureWriter::ptr(object)
               << ",\"win32_error\":" << error
               << ",\"reason\":\"virtual-protect-failed\"";
        writer().write_event("vtable_patch_failed", fields.str());
        return false;
    }

    *object_vtable = clone;
    DWORD ignored = 0;
    VirtualProtect(object_vtable, sizeof(void*), old_protect, &ignored);

    if (env_enabled("SHIFT_D3D9_CAPTURE_VTABLE_LOG")) {
        std::ostringstream fields;
        fields << "\"label\":" << CaptureWriter::quote(label ? label : "unknown")
               << ",\"object_ptr\":" << CaptureWriter::ptr(object)
               << ",\"patch_count\":" << patches.size();
        writer().write_event("vtable_patch_installed", fields.str());
    }
    return true;
}

void patch_object_vtable(
    void* object,
    std::size_t count,
    std::size_t slot,
    void* hook,
    void** original_out) {
    patch_object_vtable_batch(
        object,
        count,
        {{slot, hook, original_out}},
        "single");
}

void append_present_parameters(
    std::ostringstream& fields,
    const D3DPRESENT_PARAMETERS* params) {
    if (!params) {
        fields << "\"present_parameters\":null";
        return;
    }
    fields << "\"backbuffer_width\":" << params->BackBufferWidth
           << ",\"backbuffer_height\":" << params->BackBufferHeight
           << ",\"backbuffer_format\":" << static_cast<unsigned>(params->BackBufferFormat)
           << ",\"backbuffer_count\":" << params->BackBufferCount
           << ",\"multisample_type\":" << static_cast<unsigned>(params->MultiSampleType)
           << ",\"multisample_quality\":" << params->MultiSampleQuality
           << ",\"swap_effect\":" << static_cast<unsigned>(params->SwapEffect)
           << ",\"device_window\":" << CaptureWriter::ptr(params->hDeviceWindow)
           << ",\"windowed\":" << (params->Windowed ? "true" : "false")
           << ",\"auto_depth_stencil\":" << (params->EnableAutoDepthStencil ? "true" : "false")
           << ",\"depth_stencil_format\":" << static_cast<unsigned>(params->AutoDepthStencilFormat)
           << ",\"presentation_flags\":" << params->Flags
           << ",\"refresh_rate_hz\":" << params->FullScreen_RefreshRateInHz
           << ",\"presentation_interval\":" << params->PresentationInterval;
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
    {
        std::ostringstream fields;
        fields << "\"d3d9_ptr\":" << CaptureWriter::ptr(self)
               << ",\"adapter\":" << adapter
               << ",\"device_type\":" << static_cast<unsigned>(type)
               << ",\"focus_window\":" << CaptureWriter::ptr(window)
               << ",\"behavior_flags\":" << behavior_flags << ",";
        append_present_parameters(fields, params);
        writer().write_event("create_device_begin", fields.str());
    }

    if (out_device) *out_device = nullptr;
    const HRESULT hr = g_real_create_device
        ? g_real_create_device(self, adapter, type, window, behavior_flags, params, out_device)
        : E_FAIL;

    {
        std::ostringstream fields;
        fields << "\"hresult\":" << hresult_hex(hr)
               << ",\"success\":" << (SUCCEEDED(hr) ? "true" : "false")
               << ",\"device_ptr\":" << CaptureWriter::ptr(
                      out_device ? *out_device : nullptr);
        writer().write_event("create_device_result", fields.str());
    }

    if (SUCCEEDED(hr) && out_device && *out_device) patch_device(*out_device);
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_test_cooperative_level(IDirect3DDevice9* self) {
    const HRESULT hr = g_real_test_cooperative_level
        ? g_real_test_cooperative_level(self)
        : E_FAIL;
    if (FAILED(hr)) {
        std::ostringstream fields;
        fields << "\"device_ptr\":" << CaptureWriter::ptr(self)
               << ",\"hresult\":" << hresult_hex(hr);
        writer().write_event("test_cooperative_level", fields.str());
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_reset(
    IDirect3DDevice9* self,
    D3DPRESENT_PARAMETERS* params) {
    {
        std::ostringstream fields;
        fields << "\"device_ptr\":" << CaptureWriter::ptr(self) << ",";
        append_present_parameters(fields, params);
        writer().write_event("reset_begin", fields.str());
    }
    const HRESULT hr = g_real_reset ? g_real_reset(self, params) : E_FAIL;
    {
        std::ostringstream fields;
        fields << "\"device_ptr\":" << CaptureWriter::ptr(self)
               << ",\"hresult\":" << hresult_hex(hr)
               << ",\"success\":" << (SUCCEEDED(hr) ? "true" : "false") << ",";
        append_present_parameters(fields, params);
        writer().write_event("reset_result", fields.str());
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_begin_scene(IDirect3DDevice9* self) {
    const HRESULT hr = g_real_begin_scene ? g_real_begin_scene(self) : E_FAIL;
    if (FAILED(hr)) {
        std::ostringstream fields;
        fields << "\"device_ptr\":" << CaptureWriter::ptr(self)
               << ",\"hresult\":" << hresult_hex(hr);
        writer().write_event("begin_scene_failed", fields.str());
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_end_scene(IDirect3DDevice9* self) {
    const HRESULT hr = g_real_end_scene ? g_real_end_scene(self) : E_FAIL;
    if (FAILED(hr)) {
        std::ostringstream fields;
        fields << "\"device_ptr\":" << CaptureWriter::ptr(self)
               << ",\"hresult\":" << hresult_hex(hr);
        writer().write_event("end_scene_failed", fields.str());
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_clear(
    IDirect3DDevice9* self,
    DWORD count,
    const D3DRECT* rects,
    DWORD flags,
    D3DCOLOR color,
    float depth,
    DWORD stencil) {
    const HRESULT hr = g_real_clear
        ? g_real_clear(self, count, rects, flags, color, depth, stencil)
        : E_FAIL;
    if (FAILED(hr)) {
        std::ostringstream fields;
        fields << "\"device_ptr\":" << CaptureWriter::ptr(self)
               << ",\"hresult\":" << hresult_hex(hr)
               << ",\"clear_flags\":" << flags;
        writer().write_event("clear_failed", fields.str());
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_present(
    IDirect3DDevice9* self,
    const RECT* src,
    const RECT* dst,
    HWND override_window,
    const RGNDATA* dirty_region) {
    if (env_enabled("SHIFT_D3D9_CAPTURE_SCREENSHOT")) {
        const auto every = std::max<unsigned long long>(
            1, env_u64("SHIFT_D3D9_CAPTURE_SCREENSHOT_EVERY", 1));
        if ((g_frame.load() % every) == 0) {
            IDirect3DSurface9* backbuffer = nullptr;
            std::string screenshot_path;
            if (SUCCEEDED(self->GetRenderTarget(0, &backbuffer))) {
                const bool captured = write_backbuffer_ppm(
                    self, backbuffer, g_frame.load(), screenshot_path);
                if (captured) {
                    std::ostringstream f;
                    f << "\"path\":" << CaptureWriter::quote(screenshot_path);
                    writer().write_event("present_screenshot", f.str());
                } else {
                    writer().write_event(
                        "present_screenshot_failed",
                        "\"reason\":\"get-render-target-data-failed\"");
                }
                backbuffer->Release();
            }
        }
    }

    const HRESULT hr = g_real_present
        ? g_real_present(self, src, dst, override_window, dirty_region)
        : E_FAIL;
    const auto call_index = g_present_calls.fetch_add(1);
    if (SUCCEEDED(hr)) g_frame.fetch_add(1);

    const auto every = std::max<unsigned long long>(
        1, env_u64("SHIFT_D3D9_DIAG_PRESENT_EVERY", 300));
    if (FAILED(hr) || call_index < 8 || (call_index % every) == 0) {
        std::ostringstream fields;
        fields << "\"device_ptr\":" << CaptureWriter::ptr(self)
               << ",\"present_call\":" << call_index
               << ",\"hresult\":" << hresult_hex(hr)
               << ",\"success\":" << (SUCCEEDED(hr) ? "true" : "false");
        writer().write_event("present_result", fields.str());
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_create_vertex_buffer(
    IDirect3DDevice9* self,
    UINT length,
    DWORD usage,
    DWORD fvf,
    D3DPOOL pool,
    IDirect3DVertexBuffer9** out_buffer,
    HANDLE* shared_handle) {
    const HRESULT hr = g_real_create_vertex_buffer
        ? g_real_create_vertex_buffer(self, length, usage, fvf, pool, out_buffer, shared_handle)
        : E_FAIL;
    if (SUCCEEDED(hr) && out_buffer && *out_buffer) {
        std::ostringstream f;
        f << "\"vertex_buffer_ptr\":" << CaptureWriter::ptr(*out_buffer)
          << ",\"device_ptr\":" << CaptureWriter::ptr(self)
          << ",\"length\":" << length
          << ",\"usage\":" << usage
          << ",\"fvf\":" << fvf
          << ",\"pool\":" << static_cast<unsigned>(pool);
        writer().write_event("create_vertex_buffer", f.str());
        patch_vertex_buffer_object(*out_buffer);
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_create_index_buffer(
    IDirect3DDevice9* self,
    UINT length,
    DWORD usage,
    D3DFORMAT format,
    D3DPOOL pool,
    IDirect3DIndexBuffer9** out_buffer,
    HANDLE* shared_handle) {
    const HRESULT hr = g_real_create_index_buffer
        ? g_real_create_index_buffer(self, length, usage, format, pool, out_buffer, shared_handle)
        : E_FAIL;
    if (SUCCEEDED(hr) && out_buffer && *out_buffer) {
        std::ostringstream f;
        f << "\"index_buffer_ptr\":" << CaptureWriter::ptr(*out_buffer)
          << ",\"device_ptr\":" << CaptureWriter::ptr(self)
          << ",\"length\":" << length
          << ",\"usage\":" << usage
          << ",\"format\":" << static_cast<unsigned>(format)
          << ",\"pool\":" << static_cast<unsigned>(pool);
        writer().write_event("create_index_buffer", f.str());
        patch_index_buffer_object(*out_buffer);
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_create_texture(
    IDirect3DDevice9* self,
    UINT width,
    UINT height,
    UINT levels,
    DWORD usage,
    D3DFORMAT format,
    D3DPOOL pool,
    IDirect3DTexture9** out_texture,
    HANDLE* shared_handle) {
    const HRESULT hr = g_real_create_texture
        ? g_real_create_texture(self, width, height, levels, usage, format, pool, out_texture, shared_handle)
        : E_FAIL;
    if (SUCCEEDED(hr) && out_texture && *out_texture) {
        std::ostringstream f;
        f << "\"texture_ptr\":" << CaptureWriter::ptr(*out_texture)
          << ",\"device_ptr\":" << CaptureWriter::ptr(self)
          << ",\"width\":" << width
          << ",\"height\":" << height
          << ",\"levels\":" << levels
          << ",\"usage\":" << usage
          << ",\"format\":" << static_cast<unsigned>(format)
          << ",\"pool\":" << static_cast<unsigned>(pool);
        append_texture_descriptor_json(f, *out_texture);
        writer().write_event("create_texture", f.str());
        patch_texture_object(*out_texture);
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_create_cube_texture(
    IDirect3DDevice9* self,
    UINT edge_length,
    UINT levels,
    DWORD usage,
    D3DFORMAT format,
    D3DPOOL pool,
    IDirect3DCubeTexture9** out_texture,
    HANDLE* shared_handle) {
    const HRESULT hr = g_real_create_cube_texture
        ? g_real_create_cube_texture(self, edge_length, levels, usage, format, pool, out_texture, shared_handle)
        : E_FAIL;
    if (SUCCEEDED(hr) && out_texture && *out_texture) {
        std::ostringstream f;
        f << "\"texture_ptr\":" << CaptureWriter::ptr(*out_texture)
          << ",\"device_ptr\":" << CaptureWriter::ptr(self)
          << ",\"edge_length\":" << edge_length
          << ",\"levels\":" << levels
          << ",\"usage\":" << usage
          << ",\"format\":" << static_cast<unsigned>(format)
          << ",\"pool\":" << static_cast<unsigned>(pool);
        append_texture_descriptor_json(f, *out_texture);
        writer().write_event("create_cube_texture", f.str());
        patch_cube_texture_object(*out_texture);
    }
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
            << ",\"pool\":" << static_cast<unsigned>(surface.Pool);
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
        append_texture_snapshot_json(f, self, stage, texture);
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
    patch_object_vtable(device, D3D9_VTABLE_COUNT, SLOT_CREATE_TEXTURE,
                        reinterpret_cast<void*>(&hook_create_texture),
                        reinterpret_cast<void**>(&g_real_create_texture));
    patch_object_vtable(device, D3D9_VTABLE_COUNT, SLOT_CREATE_CUBE_TEXTURE,
                        reinterpret_cast<void*>(&hook_create_cube_texture),
                        reinterpret_cast<void**>(&g_real_create_cube_texture));
    patch_object_vtable(device, D3D9_VTABLE_COUNT, SLOT_CREATE_VERTEX_BUFFER,
                        reinterpret_cast<void*>(&hook_create_vertex_buffer),
                        reinterpret_cast<void**>(&g_real_create_vertex_buffer));
    patch_object_vtable(device, D3D9_VTABLE_COUNT, SLOT_CREATE_INDEX_BUFFER,
                        reinterpret_cast<void*>(&hook_create_index_buffer),
                        reinterpret_cast<void**>(&g_real_create_index_buffer));
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
    bool expected = false;
    if (g_proxy_entry_reported.compare_exchange_strong(expected, true)) {
        writer().write_event("proxy_direct3dcreate9",
                             "sdk_version=" + std::to_string(sdk_version));
    }
    if (!ensure_system_d3d9()) {
        writer().write_event("proxy_system_d3d9_load_failed",
                             "error_code=" + std::to_string(GetLastError()));
        return nullptr;
    }
    writer().write_event("proxy_system_d3d9_ready",
                         "sdk_version=" + std::to_string(sdk_version));
    IDirect3D9* d3d = g_real_direct3d_create9(sdk_version);
    if (d3d) patch_direct3d9(d3d);
    return d3d;
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) DisableThreadLibraryCalls(instance);
    if (reason == DLL_PROCESS_DETACH && g_system_d3d9) FreeLibrary(g_system_d3d9);
    return TRUE;
}

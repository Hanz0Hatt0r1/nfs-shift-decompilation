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
#include <cstdio>
#include <cctype>
#include <iterator>
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

constexpr std::size_t IDIRECT3DDEVICE9_VTABLE_COUNT = 119;
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
std::string g_d3d9_backend_source;
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

struct PatchedVtableSlot {
    void* original = nullptr;
    void* hook = nullptr;
};

std::unordered_map<
    void**,
    std::unordered_map<std::size_t, PatchedVtableSlot>>
    g_vtable_slot_patches;

std::atomic<unsigned long long> g_event_index{0};
std::atomic<unsigned long long> g_frame{0};
std::atomic<bool> g_proxy_entry_reported{false};
std::atomic<unsigned long long> g_perf_event_calls{0};
std::atomic<unsigned long long> g_present_calls{0};

std::once_flag g_crash_diag_once;
PVOID g_crash_handler = nullptr;
HANDLE g_crash_log = INVALID_HANDLE_VALUE;
std::string g_crash_log_path;
std::atomic<bool> g_crash_recorded{false};
std::uintptr_t g_main_image_base = 0;
std::size_t g_main_image_size = 0;
std::uintptr_t g_proxy_image_base = 0;
std::size_t g_proxy_image_size = 0;

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
        std::transform(text.begin(), text.end(), text.begin(), [](unsigned char ch) {
            return static_cast<char>(std::tolower(ch));
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

bool crash_diagnostics_enabled() {
    const char* value = std::getenv("SHIFT_D3D9_CRASH_DIAGNOSTICS");
    if (!value || !*value) return true;
    return std::string(value) != "0" &&
           std::string(value) != "false" &&
           std::string(value) != "off";
}

std::size_t image_size(HMODULE module) {
    if (!module) return 0;
    const auto base = reinterpret_cast<const unsigned char*>(module);
    const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(base);
    if (dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew <= 0) return 0;
    const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS*>(
        base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) return 0;
    return static_cast<std::size_t>(nt->OptionalHeader.SizeOfImage);
}

bool readable_stack_range(
    const void* address,
    std::size_t requested,
    std::size_t& available) {
    available = 0;
    if (!address || requested == 0) return false;
    MEMORY_BASIC_INFORMATION mbi{};
    if (!VirtualQuery(address, &mbi, sizeof(mbi))) return false;
    if (mbi.State != MEM_COMMIT) return false;
    if (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) return false;
    const std::uintptr_t start =
        reinterpret_cast<std::uintptr_t>(address);
    const std::uintptr_t end =
        reinterpret_cast<std::uintptr_t>(mbi.BaseAddress) +
        static_cast<std::uintptr_t>(mbi.RegionSize);
    if (start >= end) return false;
    available = std::min<std::size_t>(
        requested, static_cast<std::size_t>(end - start));
    return available > 0;
}

LONG CALLBACK shift_crash_exception_handler(
    EXCEPTION_POINTERS* pointers) {
#if defined(_M_IX86) || defined(__i386__)
    if (!pointers || !pointers->ExceptionRecord || !pointers->ContextRecord) {
        return EXCEPTION_CONTINUE_SEARCH;
    }

    const EXCEPTION_RECORD* record = pointers->ExceptionRecord;
    CONTEXT* context = pointers->ContextRecord;
    if (record->ExceptionCode != EXCEPTION_ACCESS_VIOLATION) {
        return EXCEPTION_CONTINUE_SEARCH;
    }

    const std::uintptr_t exception_address =
        reinterpret_cast<std::uintptr_t>(record->ExceptionAddress);
    if (!g_main_image_base || !g_main_image_size ||
        exception_address < g_main_image_base ||
        exception_address >= g_main_image_base + g_main_image_size) {
        return EXCEPTION_CONTINUE_SEARCH;
    }

    // Log only the first game-code AV. This avoids turning expected SEH probes
    // into a high-volume trace while preserving the first likely crash cause.
    bool expected = false;
    if (!g_crash_recorded.compare_exchange_strong(expected, true)) {
        return EXCEPTION_CONTINUE_SEARCH;
    }

    unsigned long access_type = 0xffffffffUL;
    std::uintptr_t access_address = 0;
    if (record->NumberParameters >= 2) {
        access_type = static_cast<unsigned long>(
            record->ExceptionInformation[0]);
        access_address = static_cast<std::uintptr_t>(
            record->ExceptionInformation[1]);
    }

    char buffer[8192] = {};
    std::size_t used = 0;
    auto append = [&](const char* format, auto... args) {
        if (used >= sizeof(buffer)) return;
        const int written = std::snprintf(
            buffer + used,
            sizeof(buffer) - used,
            format,
            args...);
        if (written <= 0) return;
        const std::size_t amount =
            static_cast<std::size_t>(written);
        used += std::min(
            amount,
            sizeof(buffer) - used - 1);
    };

    append(
        "{\"format\":\"SHIFT.D3D9ProxyCrash/1\","
        "\"process_id\":%lu,\"thread_id\":%lu,"
        "\"frame\":%llu,"
        "\"exception_code\":\"0x%08lx\","
        "\"exception_address\":\"0x%08lx\","
        "\"exception_rva\":\"0x%08lx\","
        "\"access_type\":%lu,"
        "\"access_address\":\"0x%08lx\","
        "\"registers\":{"
        "\"eip\":\"0x%08lx\",\"eax\":\"0x%08lx\","
        "\"ebx\":\"0x%08lx\",\"ecx\":\"0x%08lx\","
        "\"edx\":\"0x%08lx\",\"esi\":\"0x%08lx\","
        "\"edi\":\"0x%08lx\",\"ebp\":\"0x%08lx\","
        "\"esp\":\"0x%08lx\"},"
        "\"main_image\":{\"base\":\"0x%08lx\",\"size\":%lu},"
        "\"proxy_image\":{\"base\":\"0x%08lx\",\"size\":%lu},"
        "\"stack_words\":[",
        GetCurrentProcessId(),
        GetCurrentThreadId(),
        g_frame.load(),
        static_cast<unsigned long>(record->ExceptionCode),
        static_cast<unsigned long>(exception_address),
        static_cast<unsigned long>(exception_address - g_main_image_base),
        access_type,
        static_cast<unsigned long>(access_address),
        static_cast<unsigned long>(context->Eip),
        static_cast<unsigned long>(context->Eax),
        static_cast<unsigned long>(context->Ebx),
        static_cast<unsigned long>(context->Ecx),
        static_cast<unsigned long>(context->Edx),
        static_cast<unsigned long>(context->Esi),
        static_cast<unsigned long>(context->Edi),
        static_cast<unsigned long>(context->Ebp),
        static_cast<unsigned long>(context->Esp),
        static_cast<unsigned long>(g_main_image_base),
        static_cast<unsigned long>(g_main_image_size),
        static_cast<unsigned long>(g_proxy_image_base),
        static_cast<unsigned long>(g_proxy_image_size));

    DWORD stack_words[32] = {};
    std::size_t readable = 0;
    std::size_t stack_count = 0;
    if (readable_stack_range(
            reinterpret_cast<const void*>(
                static_cast<std::uintptr_t>(context->Esp)),
            sizeof(stack_words),
            readable)) {
        stack_count = std::min<std::size_t>(
            sizeof(stack_words) / sizeof(stack_words[0]),
            readable / sizeof(stack_words[0]));
        if (stack_count) {
            std::memcpy(
                stack_words,
                reinterpret_cast<const void*>(
                    static_cast<std::uintptr_t>(context->Esp)),
                stack_count * sizeof(stack_words[0]));
        }
    }

    for (std::size_t index = 0; index < stack_count; ++index) {
        if (index) append(",");
        append("\"0x%08lx\"", static_cast<unsigned long>(stack_words[index]));
    }
    append("]}\r\n");

    if (g_crash_log != INVALID_HANDLE_VALUE && used) {
        DWORD written = 0;
        WriteFile(
            g_crash_log,
            buffer,
            static_cast<DWORD>(std::min<std::size_t>(
                used, std::numeric_limits<DWORD>::max())),
            &written,
            nullptr);
        FlushFileBuffers(g_crash_log);
    }
    OutputDebugStringA(buffer);
#endif
    return EXCEPTION_CONTINUE_SEARCH;
}

std::string default_crash_log_path() {
    const char* explicit_path = std::getenv("SHIFT_D3D9_CRASH_LOG");
    if (explicit_path && *explicit_path) return explicit_path;

    const char* capture_path = std::getenv("SHIFT_D3D9_CAPTURE");
    if (capture_path && *capture_path) {
        std::string value(capture_path);
        const std::size_t separator = value.find_last_of("\\/");
        if (separator != std::string::npos) {
            return value.substr(0, separator + 1) +
                   "shift_d3d9_crash.jsonl";
        }
    }
    return "shift_d3d9_crash.jsonl";
}

void ensure_crash_diagnostics() {
    if (!crash_diagnostics_enabled()) return;
    std::call_once(g_crash_diag_once, [] {
        HMODULE main_module = GetModuleHandleA(nullptr);
        g_main_image_base =
            reinterpret_cast<std::uintptr_t>(main_module);
        g_main_image_size = image_size(main_module);
        g_proxy_image_base =
            reinterpret_cast<std::uintptr_t>(g_proxy_module);
        g_proxy_image_size = image_size(g_proxy_module);

        g_crash_log_path = default_crash_log_path();
        g_crash_log = CreateFileA(
            g_crash_log_path.c_str(),
            FILE_APPEND_DATA,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
            nullptr,
            OPEN_ALWAYS,
            FILE_ATTRIBUTE_NORMAL,
            nullptr);

        if (g_crash_log == INVALID_HANDLE_VALUE) {
            char temp_path[MAX_PATH] = {};
            const DWORD length = GetTempPathA(MAX_PATH, temp_path);
            if (length > 0 && length < MAX_PATH) {
                g_crash_log_path.assign(temp_path, length);
                if (!g_crash_log_path.empty() &&
                    g_crash_log_path.back() != '\\' &&
                    g_crash_log_path.back() != '/') {
                    g_crash_log_path.push_back('\\');
                }
                g_crash_log_path += "shift_d3d9_crash.jsonl";
                g_crash_log = CreateFileA(
                    g_crash_log_path.c_str(),
                    FILE_APPEND_DATA,
                    FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                    nullptr,
                    OPEN_ALWAYS,
                    FILE_ATTRIBUTE_NORMAL,
                    nullptr);
            }
        }

        g_crash_handler = AddVectoredExceptionHandler(
            0, &shift_crash_exception_handler);
    });
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

void patch_object_vtable(
    void* object,
    std::size_t count,
    std::size_t slot,
    void* hook,
    void** original_out);

struct BufferLockState {
    std::string kind;
    UINT offset = 0;
    UINT requested_size = 0;
    UINT buffer_length = 0;
    DWORD flags = 0;
    void* bits = nullptr;
    bool full_surface = false;
    bool active = false;
};

std::mutex g_buffer_lock_state_mutex;
std::unordered_map<void*, BufferLockState> g_vertex_buffer_lock_states;
std::unordered_map<void*, BufferLockState> g_index_buffer_lock_states;
std::atomic<unsigned long long> g_buffer_payload_sequence{0};

bool buffer_payload_capture_enabled() {
    return env_enabled("SHIFT_D3D9_CAPTURE_BUFFER_PAYLOADS");
}

std::string buffer_payload_dir() {
    const char* directory = std::getenv("SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR");
    std::string value = (directory && *directory) ? directory : ".";
    if (!value.empty() && value.back() != '\\' && value.back() != '/') value.push_back('\\');
    return value;
}

std::string buffer_payload_path(
    const char* kind,
    const void* buffer,
    UINT offset,
    UINT sequence) {
    std::ostringstream path;
    path << buffer_payload_dir()
         << "shift_d3d9_buffer_payload_"
         << kind << "_"
         << CaptureWriter::ptr(buffer).substr(1, CaptureWriter::ptr(buffer).size() - 2)
         << "_o" << offset
         << "_" << sequence
         << ".bin";
    return path.str();
}

void emit_buffer_payload(
    const void* buffer,
    const BufferLockState& state,
    const std::string& path,
    const std::vector<unsigned char>& payload,
    const char* status) {
    std::ostringstream f;
    f << "\"buffer_ptr\":" << CaptureWriter::ptr(buffer)
      << ",\"resource_type_name\":" << CaptureWriter::quote(state.kind)
      << ",\"offset\":" << state.offset
      << ",\"requested_size\":" << state.requested_size
      << ",\"buffer_length\":" << state.buffer_length
      << ",\"captured_byte_size\":" << payload.size()
      << ",\"flags\":" << state.flags
      << ",\"snapshot_status\":" << CaptureWriter::quote(status)
      << ",\"payload_path\":" << CaptureWriter::quote(path);
    writer().write_event("buffer_payload", f.str());
}

bool should_capture_full_buffer(UINT offset, UINT size, UINT length) {
    return buffer_payload_capture_enabled()
        && offset == 0
        && (size == 0 || size == length)
        && length > 0;
}

void capture_buffer_payload(
    const void* buffer,
    const BufferLockState& state,
    const std::string& path,
    std::size_t byte_size) {
    if (!state.bits || !byte_size) return;
    std::vector<unsigned char> payload(
        static_cast<const unsigned char*>(state.bits),
        static_cast<const unsigned char*>(state.bits) + byte_size);
    std::ofstream output(path, std::ios::binary);
    if (!output.is_open()) {
        emit_buffer_payload(buffer, state, path, payload, "capture-failed");
        return;
    }
    output.write(
        reinterpret_cast<const char*>(payload.data()),
        static_cast<std::streamsize>(payload.size()));
    if (output.good()) {
        emit_buffer_payload(buffer, state, path, payload, "captured");
    } else {
        emit_buffer_payload(buffer, state, path, payload, "capture-failed");
    }
}

HRESULT STDMETHODCALLTYPE hook_vertex_buffer_lock(
    IDirect3DVertexBuffer9* self,
    UINT offset,
    UINT size,
    void** bits,
    DWORD flags) {
    const auto original = original_method_for<VertexBufferLockFn>(
        self, SLOT_BUFFER_LOCK, g_real_vertex_buffer_lock);
    const HRESULT hr = original
        ? original(self, offset, size, bits, flags)
        : E_FAIL;
    if (SUCCEEDED(hr) && bits && *bits) {
        D3DVERTEXBUFFER_DESC desc{};
        const bool have_desc = SUCCEEDED(self->GetDesc(&desc));
        BufferLockState state{};
        state.kind = "vertex_buffer";
        state.offset = offset;
        state.requested_size = size;
        state.buffer_length = have_desc ? desc.Size : size;
        state.flags = flags;
        state.bits = *bits;
        state.full_surface = have_desc
            && should_capture_full_buffer(offset, size, desc.Size);
        state.active = state.full_surface;
        if (state.active) {
            std::lock_guard<std::mutex> lock(g_buffer_lock_state_mutex);
            g_vertex_buffer_lock_states[self] = state;
        }
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_vertex_buffer_unlock(IDirect3DVertexBuffer9* self) {
    BufferLockState state{};
    bool captured = false;
    {
        std::lock_guard<std::mutex> lock(g_buffer_lock_state_mutex);
        const auto it = g_vertex_buffer_lock_states.find(self);
        if (it != g_vertex_buffer_lock_states.end()) {
            state = it->second;
            g_vertex_buffer_lock_states.erase(it);
            captured = state.active && state.bits;
        }
    }

    std::vector<unsigned char> payload;
    std::string path;
    if (captured) {
        const std::size_t byte_size = state.buffer_length;
        if (byte_size > 0) {
            payload.assign(
                static_cast<const unsigned char*>(state.bits),
                static_cast<const unsigned char*>(state.bits) + byte_size);
            const UINT sequence = static_cast<UINT>(g_buffer_payload_sequence.fetch_add(1));
            path = buffer_payload_path("vertex", self, state.offset, sequence);
        }
    }

    const auto original = original_method_for<VertexBufferUnlockFn>(
        self, SLOT_BUFFER_UNLOCK, g_real_vertex_buffer_unlock);
    const HRESULT hr = original ? original(self) : E_FAIL;
    if (captured && SUCCEEDED(hr) && !payload.empty()) {
        std::ofstream output(path, std::ios::binary);
        if (output.is_open()) {
            output.write(reinterpret_cast<const char*>(payload.data()), static_cast<std::streamsize>(payload.size()));
            emit_buffer_payload(
                self, state, path, payload,
                output.good() ? "captured" : "capture-failed");
        } else {
            emit_buffer_payload(self, state, path, payload, "capture-failed");
        }
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_index_buffer_lock(
    IDirect3DIndexBuffer9* self,
    UINT offset,
    UINT size,
    void** bits,
    DWORD flags) {
    const auto original = original_method_for<IndexBufferLockFn>(
        self, SLOT_BUFFER_LOCK, g_real_index_buffer_lock);
    const HRESULT hr = original
        ? original(self, offset, size, bits, flags)
        : E_FAIL;
    if (SUCCEEDED(hr) && bits && *bits) {
        D3DINDEXBUFFER_DESC desc{};
        const bool have_desc = SUCCEEDED(self->GetDesc(&desc));
        BufferLockState state{};
        state.kind = "index_buffer";
        state.offset = offset;
        state.requested_size = size;
        state.buffer_length = have_desc ? desc.Size : size;
        state.flags = flags;
        state.bits = *bits;
        state.full_surface = have_desc
            && should_capture_full_buffer(offset, size, desc.Size);
        state.active = state.full_surface;
        if (state.active) {
            std::lock_guard<std::mutex> lock(g_buffer_lock_state_mutex);
            g_index_buffer_lock_states[self] = state;
        }
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_index_buffer_unlock(IDirect3DIndexBuffer9* self) {
    BufferLockState state{};
    bool captured = false;
    {
        std::lock_guard<std::mutex> lock(g_buffer_lock_state_mutex);
        const auto it = g_index_buffer_lock_states.find(self);
        if (it != g_index_buffer_lock_states.end()) {
            state = it->second;
            g_index_buffer_lock_states.erase(it);
            captured = state.active && state.bits;
        }
    }

    std::vector<unsigned char> payload;
    std::string path;
    if (captured) {
        const std::size_t byte_size = state.buffer_length;
        if (byte_size > 0) {
            payload.assign(
                static_cast<const unsigned char*>(state.bits),
                static_cast<const unsigned char*>(state.bits) + byte_size);
            const UINT sequence = static_cast<UINT>(g_buffer_payload_sequence.fetch_add(1));
            path = buffer_payload_path("index", self, state.offset, sequence);
        }
    }

    const auto original = original_method_for<IndexBufferUnlockFn>(
        self, SLOT_BUFFER_UNLOCK, g_real_index_buffer_unlock);
    const HRESULT hr = original ? original(self) : E_FAIL;
    if (captured && SUCCEEDED(hr) && !payload.empty()) {
        std::ofstream output(path, std::ios::binary);
        if (output.is_open()) {
            output.write(reinterpret_cast<const char*>(payload.data()), static_cast<std::streamsize>(payload.size()));
            emit_buffer_payload(
                self, state, path, payload,
                output.good() ? "captured" : "capture-failed");
        } else {
            emit_buffer_payload(self, state, path, payload, "capture-failed");
        }
    }
    return hr;
}

void patch_vertex_buffer_object(IDirect3DVertexBuffer9* buffer) {
    if (!buffer) return;
    patch_object_vtable(
        buffer,
        BUFFER_VTABLE_COUNT,
        SLOT_BUFFER_LOCK,
        reinterpret_cast<void*>(&hook_vertex_buffer_lock),
        reinterpret_cast<void**>(&g_real_vertex_buffer_lock));
    patch_object_vtable(
        buffer,
        BUFFER_VTABLE_COUNT,
        SLOT_BUFFER_UNLOCK,
        reinterpret_cast<void*>(&hook_vertex_buffer_unlock),
        reinterpret_cast<void**>(&g_real_vertex_buffer_unlock));
}

void patch_index_buffer_object(IDirect3DIndexBuffer9* buffer) {
    if (!buffer) return;
    patch_object_vtable(
        buffer,
        BUFFER_VTABLE_COUNT,
        SLOT_BUFFER_LOCK,
        reinterpret_cast<void*>(&hook_index_buffer_lock),
        reinterpret_cast<void**>(&g_real_index_buffer_lock));
    patch_object_vtable(
        buffer,
        BUFFER_VTABLE_COUNT,
        SLOT_BUFFER_UNLOCK,
        reinterpret_cast<void*>(&hook_index_buffer_unlock),
        reinterpret_cast<void**>(&g_real_index_buffer_unlock));
}

struct TextureLockState {
    UINT level = 0;
    D3DLOCKED_RECT locked{};
    D3DSURFACE_DESC desc{};
    bool capture = false;
};

std::mutex g_texture_lock_state_mutex;
std::unordered_map<void*, std::unordered_map<UINT, TextureLockState>> g_texture_lock_states;
std::atomic<unsigned long long> g_texture_payload_sequence{0};

struct CubeTextureLockState {
    D3DCUBEMAP_FACES face = D3DCUBEMAP_FACE_POSITIVE_X;
    UINT level = 0;
    D3DLOCKED_RECT locked{};
    D3DSURFACE_DESC desc{};
    bool capture = false;
};

std::mutex g_cube_texture_lock_state_mutex;
std::unordered_map<void*, std::unordered_map<std::uint64_t, CubeTextureLockState>> g_cube_texture_lock_states;

bool texture_payload_capture_enabled() {
    return env_enabled("SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOADS");
}

std::string texture_payload_dir() {
    const char* directory = std::getenv("SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOAD_DIR");
    std::string value = (directory && *directory) ? directory : ".";
    if (!value.empty() && value.back() != '\\' && value.back() != '/') value.push_back('\\');
    return value;
}

std::size_t texture_payload_byte_size(const D3DSURFACE_DESC& desc, LONG pitch) {
    if (pitch <= 0) return 0;
    if (desc.Format == D3DFMT_DXT1 ||
        desc.Format == D3DFMT_DXT3 ||
        desc.Format == D3DFMT_DXT5) {
        const std::size_t block_rows = std::max<UINT>(1, (desc.Height + 3) / 4);
        return static_cast<std::size_t>(pitch) * block_rows;
    }
    return static_cast<std::size_t>(pitch) * desc.Height;
}

std::string texture_payload_path(IDirect3DTexture9* texture, UINT level) {
    std::ostringstream path;
    path << texture_payload_dir()
         << "shift_d3d9_texture_payload_"
         << CaptureWriter::ptr(texture).substr(1, CaptureWriter::ptr(texture).size() - 2)
         << "_l" << level
         << "_" << g_texture_payload_sequence.fetch_add(1)
         << ".bin";
    return path.str();
}

void emit_texture_payload(
    IDirect3DTexture9* texture,
    const TextureLockState& state,
    const std::string& path,
    std::size_t byte_size,
    const char* status) {
    std::ostringstream f;
    f << "\"texture_ptr\":" << CaptureWriter::ptr(texture)
      << ",\"resource_type_name\":\"texture2d\""
      << ",\"level\":" << state.level
      << ",\"width\":" << state.desc.Width
      << ",\"height\":" << state.desc.Height
      << ",\"pitch\":" << state.locked.Pitch
      << ",\"format\":" << static_cast<unsigned>(state.desc.Format)
      << ",\"pool\":" << static_cast<unsigned>(state.desc.Pool)
      << ",\"byte_size\":" << byte_size
      << ",\"snapshot_status\":" << CaptureWriter::quote(status)
      << ",\"payload_path\":" << CaptureWriter::quote(path);
    writer().write_event("texture_payload", f.str());
}

std::uint64_t cube_lock_key(D3DCUBEMAP_FACES face, UINT level) {
    return (static_cast<std::uint64_t>(static_cast<unsigned>(face)) << 32) |
           static_cast<std::uint64_t>(level);
}

std::string cube_texture_payload_path(
    IDirect3DCubeTexture9* texture,
    D3DCUBEMAP_FACES face,
    UINT level) {
    std::ostringstream path;
    path << texture_payload_dir()
         << "shift_d3d9_cube_payload_"
         << CaptureWriter::ptr(texture).substr(1, CaptureWriter::ptr(texture).size() - 2)
         << "_" << cube_face_name(face)
         << "_l" << level
         << "_" << g_texture_payload_sequence.fetch_add(1)
         << ".bin";
    return path.str();
}

void emit_cube_texture_payload(
    IDirect3DCubeTexture9* texture,
    const CubeTextureLockState& state,
    const std::string& path,
    std::size_t byte_size,
    const char* status) {
    std::ostringstream f;
    f << "\"texture_ptr\":" << CaptureWriter::ptr(texture)
      << ",\"resource_type_name\":\"cube_texture\""
      << ",\"face\":" << static_cast<unsigned>(state.face)
      << ",\"face_name\":" << CaptureWriter::quote(cube_face_name(state.face))
      << ",\"level\":" << state.level
      << ",\"width\":" << state.desc.Width
      << ",\"height\":" << state.desc.Height
      << ",\"pitch\":" << state.locked.Pitch
      << ",\"format\":" << static_cast<unsigned>(state.desc.Format)
      << ",\"pool\":" << static_cast<unsigned>(state.desc.Pool)
      << ",\"byte_size\":" << byte_size
      << ",\"snapshot_status\":" << CaptureWriter::quote(status)
      << ",\"payload_path\":" << CaptureWriter::quote(path);
    writer().write_event("texture_payload", f.str());
}

HRESULT STDMETHODCALLTYPE hook_cube_texture_lock_rect(
    IDirect3DCubeTexture9* self,
    D3DCUBEMAP_FACES face,
    UINT level,
    D3DLOCKED_RECT* locked,
    const RECT* rect,
    DWORD flags) {
    const auto original = original_method_for<CubeTextureLockRectFn>(
        self, SLOT_TEXTURE_LOCK_RECT, g_real_cube_texture_lock_rect);
    const HRESULT hr = original
        ? original(self, face, level, locked, rect, flags)
        : E_FAIL;
    if (SUCCEEDED(hr) && locked && texture_payload_capture_enabled() &&
        !rect && !(flags & D3DLOCK_READONLY)) {
        CubeTextureLockState state{};
        state.face = face;
        state.level = level;
        state.locked = *locked;
        state.capture = SUCCEEDED(self->GetLevelDesc(level, &state.desc));
        if (state.capture && state.locked.pBits) {
            std::lock_guard<std::mutex> lock(g_cube_texture_lock_state_mutex);
            g_cube_texture_lock_states[self][cube_lock_key(face, level)] = state;
        }
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_cube_texture_unlock_rect(
    IDirect3DCubeTexture9* self,
    D3DCUBEMAP_FACES face,
    UINT level) {
    CubeTextureLockState state{};
    bool captured = false;
    {
        std::lock_guard<std::mutex> lock(g_cube_texture_lock_state_mutex);
        const auto it = g_cube_texture_lock_states.find(self);
        if (it != g_cube_texture_lock_states.end()) {
            const auto level_it = it->second.find(cube_lock_key(face, level));
            if (level_it != it->second.end()) {
                state = level_it->second;
                it->second.erase(level_it);
                if (it->second.empty()) {
                    g_cube_texture_lock_states.erase(it);
                }
                captured = state.capture && state.locked.pBits;
            }
        }
    }

    std::vector<unsigned char> payload;
    std::string path;
    if (captured) {
        const std::size_t byte_size = texture_payload_byte_size(state.desc, state.locked.Pitch);
        if (byte_size > 0) {
            payload.assign(
                static_cast<const unsigned char*>(state.locked.pBits),
                static_cast<const unsigned char*>(state.locked.pBits) + byte_size);
            path = cube_texture_payload_path(self, face, level);
        }
    }

    const auto original = original_method_for<CubeTextureUnlockRectFn>(
        self, SLOT_TEXTURE_UNLOCK_RECT, g_real_cube_texture_unlock_rect);
    const HRESULT hr = original ? original(self, face, level) : E_FAIL;

    if (captured && SUCCEEDED(hr) && !payload.empty()) {
        std::ofstream output(path, std::ios::binary);
        if (output.is_open()) {
            output.write(reinterpret_cast<const char*>(payload.data()), static_cast<std::streamsize>(payload.size()));
            if (output.good()) {
                emit_cube_texture_payload(self, state, path, payload.size(), "captured");
                return hr;
            }
        }
        emit_cube_texture_payload(self, state, path, payload.size(), "capture-failed");
    }
    return hr;
}

void patch_cube_texture_object(IDirect3DCubeTexture9* texture) {
    if (!texture) return;
    patch_object_vtable(
        texture,
        CUBE_TEXTURE_VTABLE_COUNT,
        SLOT_TEXTURE_LOCK_RECT,
        reinterpret_cast<void*>(&hook_cube_texture_lock_rect),
        reinterpret_cast<void**>(&g_real_cube_texture_lock_rect));
    patch_object_vtable(
        texture,
        CUBE_TEXTURE_VTABLE_COUNT,
        SLOT_TEXTURE_UNLOCK_RECT,
        reinterpret_cast<void*>(&hook_cube_texture_unlock_rect),
        reinterpret_cast<void**>(&g_real_cube_texture_unlock_rect));
}

HRESULT STDMETHODCALLTYPE hook_texture_lock_rect(
    IDirect3DTexture9* self,
    UINT level,
    D3DLOCKED_RECT* locked,
    const RECT* rect,
    DWORD flags) {
    const auto original = original_method_for<TextureLockRectFn>(
        self, SLOT_TEXTURE_LOCK_RECT, g_real_texture_lock_rect);
    const HRESULT hr = original
        ? original(self, level, locked, rect, flags)
        : E_FAIL;
    if (SUCCEEDED(hr) && locked && texture_payload_capture_enabled() &&
        !rect && !(flags & D3DLOCK_READONLY)) {
        TextureLockState state{};
        state.level = level;
        state.locked = *locked;
        IDirect3DSurface9* surface = nullptr;
        if (SUCCEEDED(self->GetSurfaceLevel(level, &surface))) {
            state.capture = SUCCEEDED(surface->GetDesc(&state.desc));
            surface->Release();
        }
        std::lock_guard<std::mutex> lock(g_texture_lock_state_mutex);
        if (state.capture && state.locked.pBits) {
            g_texture_lock_states[self][level] = state;
        }
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_texture_unlock_rect(
    IDirect3DTexture9* self,
    UINT level) {
    TextureLockState state{};
    bool captured = false;
    {
        std::lock_guard<std::mutex> lock(g_texture_lock_state_mutex);
        const auto it = g_texture_lock_states.find(self);
        if (it != g_texture_lock_states.end()) {
            const auto level_it = it->second.find(level);
            if (level_it != it->second.end()) {
                state = level_it->second;
                it->second.erase(level_it);
                if (it->second.empty()) {
                    g_texture_lock_states.erase(it);
                }
                captured = state.capture && state.locked.pBits;
            }
        }
    }

    std::vector<unsigned char> payload;
    std::string path;
    if (captured) {
        const std::size_t byte_size = texture_payload_byte_size(state.desc, state.locked.Pitch);
        if (byte_size > 0) {
            payload.assign(
                static_cast<const unsigned char*>(state.locked.pBits),
                static_cast<const unsigned char*>(state.locked.pBits) + byte_size);
            path = texture_payload_path(self, level);
        }
    }

    const auto original = original_method_for<TextureUnlockRectFn>(
        self, SLOT_TEXTURE_UNLOCK_RECT, g_real_texture_unlock_rect);
    const HRESULT hr = original ? original(self, level) : E_FAIL;

    if (captured && SUCCEEDED(hr) && !payload.empty()) {
        std::ofstream output(path, std::ios::binary);
        if (output.is_open()) {
            output.write(reinterpret_cast<const char*>(payload.data()), static_cast<std::streamsize>(payload.size()));
            if (output.good()) {
                emit_texture_payload(self, state, path, payload.size(), "captured");
                return hr;
            }
        }
        emit_texture_payload(self, state, path, payload.size(), "capture-failed");
    }
    return hr;
}

void patch_texture_object(IDirect3DTexture9* texture) {
    if (!texture) return;
    patch_object_vtable(
        texture,
        TEXTURE_VTABLE_COUNT,
        SLOT_TEXTURE_LOCK_RECT,
        reinterpret_cast<void*>(&hook_texture_lock_rect),
        reinterpret_cast<void**>(&g_real_texture_lock_rect));
    patch_object_vtable(
        texture,
        TEXTURE_VTABLE_COUNT,
        SLOT_TEXTURE_UNLOCK_RECT,
        reinterpret_cast<void*>(&hook_texture_unlock_rect),
        reinterpret_cast<void**>(&g_real_texture_unlock_rect));
}

struct VtablePatch {
    std::size_t slot = 0;
    void* hook = nullptr;
    void** original_out = nullptr;
};

template <typename T>
T original_method_for(void* object, std::size_t slot, T fallback) {
    if (!object) return fallback;
    void** vtable = *reinterpret_cast<void***>(object);
    if (!vtable) return fallback;

    std::lock_guard<std::mutex> lock(g_hook_mutex);
    const auto table_it = g_vtable_slot_patches.find(vtable);
    if (table_it == g_vtable_slot_patches.end()) return fallback;
    const auto slot_it = table_it->second.find(slot);
    if (slot_it == table_it->second.end() || !slot_it->second.original) {
        return fallback;
    }
    return reinterpret_cast<T>(slot_it->second.original);
}

bool patch_object_vtable_batch(
    void* object,
    std::size_t count,
    const std::vector<VtablePatch>& patches,
    const char* label) {

    if (!object || patches.empty()) return false;
    auto*** object_vtable = reinterpret_cast<void***>(object);
    void** vtable = *object_vtable;
    if (!vtable) {
        std::ostringstream fields;
        fields << "\"label\":" << CaptureWriter::quote(label ? label : "unknown")
               << ",\"object_ptr\":" << CaptureWriter::ptr(object)
               << ",\"reason\":\"null-vtable\"";
        writer().write_event("vtable_patch_failed", fields.str());
        return false;
    }

    for (const auto& patch : patches) {
        if (patch.slot >= count || !patch.hook) {
            std::ostringstream fields;
            fields << "\"label\":" << CaptureWriter::quote(label ? label : "unknown")
                   << ",\"object_ptr\":" << CaptureWriter::ptr(object)
                   << ",\"vtable_ptr\":" << CaptureWriter::ptr(vtable)
                   << ",\"slot\":" << patch.slot
                   << ",\"reason\":\"invalid-slot-or-hook\"";
            writer().write_event("vtable_patch_failed", fields.str());
            return false;
        }
    }

    std::lock_guard<std::mutex> lock(g_hook_mutex);
    std::size_t newly_patched = 0;

    for (const auto& patch : patches) {
        auto& table_patches = g_vtable_slot_patches[vtable];
        const auto known = table_patches.find(patch.slot);
        void* current = vtable[patch.slot];

        if (known != table_patches.end()) {
            if (current != known->second.hook || known->second.hook != patch.hook) {
                std::ostringstream fields;
                fields << "\"label\":" << CaptureWriter::quote(label ? label : "unknown")
                       << ",\"object_ptr\":" << CaptureWriter::ptr(object)
                       << ",\"vtable_ptr\":" << CaptureWriter::ptr(vtable)
                       << ",\"slot\":" << patch.slot
                       << ",\"current_ptr\":" << CaptureWriter::ptr(current)
                       << ",\"expected_hook_ptr\":" << CaptureWriter::ptr(known->second.hook)
                       << ",\"requested_hook_ptr\":" << CaptureWriter::ptr(patch.hook)
                       << ",\"reason\":\"patched-slot-modified\"";
                writer().write_event("vtable_patch_failed", fields.str());
                return false;
            }
            if (patch.original_out) *patch.original_out = known->second.original;
            continue;
        }

        if (current == patch.hook) {
            std::ostringstream fields;
            fields << "\"label\":" << CaptureWriter::quote(label ? label : "unknown")
                   << ",\"object_ptr\":" << CaptureWriter::ptr(object)
                   << ",\"vtable_ptr\":" << CaptureWriter::ptr(vtable)
                   << ",\"slot\":" << patch.slot
                   << ",\"reason\":\"hook-present-without-original\"";
            writer().write_event("vtable_patch_failed", fields.str());
            return false;
        }

        DWORD old_protect = 0;
        if (!VirtualProtect(
                &vtable[patch.slot],
                sizeof(void*),
                PAGE_EXECUTE_READWRITE,
                &old_protect)) {
            std::ostringstream fields;
            fields << "\"label\":" << CaptureWriter::quote(label ? label : "unknown")
                   << ",\"object_ptr\":" << CaptureWriter::ptr(object)
                   << ",\"vtable_ptr\":" << CaptureWriter::ptr(vtable)
                   << ",\"slot\":" << patch.slot
                   << ",\"win32_error\":" << GetLastError()
                   << ",\"reason\":\"virtual-protect-failed\"";
            writer().write_event("vtable_patch_failed", fields.str());
            return false;
        }

        vtable[patch.slot] = patch.hook;

        DWORD ignored = 0;
        VirtualProtect(
            &vtable[patch.slot],
            sizeof(void*),
            old_protect,
            &ignored);
        FlushInstructionCache(
            GetCurrentProcess(),
            &vtable[patch.slot],
            sizeof(void*));

        table_patches.emplace(
            patch.slot,
            PatchedVtableSlot{current, patch.hook});
        if (patch.original_out) *patch.original_out = current;
        ++newly_patched;

        if (env_enabled("SHIFT_D3D9_CAPTURE_VTABLE_LOG")) {
            std::ostringstream fields;
            fields << "\"label\":" << CaptureWriter::quote(label ? label : "unknown")
                   << ",\"object_ptr\":" << CaptureWriter::ptr(object)
                   << ",\"vtable_ptr\":" << CaptureWriter::ptr(vtable)
                   << ",\"slot\":" << patch.slot
                   << ",\"original_ptr\":" << CaptureWriter::ptr(current)
                   << ",\"hook_ptr\":" << CaptureWriter::ptr(patch.hook)
                   << ",\"strategy\":\"inplace\"";
            writer().write_event("vtable_slot_patched", fields.str());
        }
    }

    if (env_enabled("SHIFT_D3D9_CAPTURE_VTABLE_LOG")) {
        std::ostringstream fields;
        fields << "\"label\":" << CaptureWriter::quote(label ? label : "unknown")
               << ",\"object_ptr\":" << CaptureWriter::ptr(object)
               << ",\"vtable_ptr\":" << CaptureWriter::ptr(vtable)
               << ",\"interface_slot_count\":" << count
               << ",\"patch_count\":" << patches.size()
               << ",\"newly_patched_count\":" << newly_patched
               << ",\"strategy\":\"inplace\"";
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
    const auto original = original_method_for<CreateDeviceFn>(
        self, 16, g_real_create_device);
    const HRESULT hr = original
        ? original(self, adapter, type, window, behavior_flags, params, out_device)
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
    const auto original = original_method_for<TestCooperativeLevelFn>(
        self, SLOT_TEST_COOPERATIVE_LEVEL, g_real_test_cooperative_level);
    const HRESULT hr = original ? original(self) : E_FAIL;
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
    const auto original = original_method_for<ResetFn>(
        self, SLOT_RESET, g_real_reset);
    const HRESULT hr = original ? original(self, params) : E_FAIL;
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
    const auto original = original_method_for<BeginSceneFn>(
        self, SLOT_BEGIN_SCENE, g_real_begin_scene);
    const HRESULT hr = original ? original(self) : E_FAIL;
    if (FAILED(hr)) {
        std::ostringstream fields;
        fields << "\"device_ptr\":" << CaptureWriter::ptr(self)
               << ",\"hresult\":" << hresult_hex(hr);
        writer().write_event("begin_scene_failed", fields.str());
    }
    return hr;
}

HRESULT STDMETHODCALLTYPE hook_end_scene(IDirect3DDevice9* self) {
    const auto original = original_method_for<EndSceneFn>(
        self, SLOT_END_SCENE, g_real_end_scene);
    const HRESULT hr = original ? original(self) : E_FAIL;
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
    const auto original = original_method_for<ClearFn>(
        self, SLOT_CLEAR, g_real_clear);
    const HRESULT hr = original
        ? original(self, count, rects, flags, color, depth, stencil)
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

    const auto original = original_method_for<PresentFn>(
        self, SLOT_PRESENT, g_real_present);
    const HRESULT hr = original
        ? original(self, src, dst, override_window, dirty_region)
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
    const auto original = original_method_for<CreateVertexBufferFn>(
        self, SLOT_CREATE_VERTEX_BUFFER, g_real_create_vertex_buffer);
    const HRESULT hr = original
        ? original(self, length, usage, fvf, pool, out_buffer, shared_handle)
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
    const auto original = original_method_for<CreateIndexBufferFn>(
        self, SLOT_CREATE_INDEX_BUFFER, g_real_create_index_buffer);
    const HRESULT hr = original
        ? original(self, length, usage, format, pool, out_buffer, shared_handle)
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
    const auto original = original_method_for<CreateTextureFn>(
        self, SLOT_CREATE_TEXTURE, g_real_create_texture);
    const HRESULT hr = original
        ? original(self, width, height, levels, usage, format, pool, out_texture, shared_handle)
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
    const auto original = original_method_for<CreateCubeTextureFn>(
        self, SLOT_CREATE_CUBE_TEXTURE, g_real_create_cube_texture);
    const HRESULT hr = original
        ? original(self, edge_length, levels, usage, format, pool, out_texture, shared_handle)
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
    const auto original = original_method_for<CreateVertexDeclarationFn>(
        self, SLOT_CREATE_VERTEX_DECLARATION, g_real_create_vertex_declaration);
    const HRESULT hr = original ? original(self, declaration, out_decl) : E_FAIL;
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
    const auto original = original_method_for<SetVertexDeclarationFn>(
        self, SLOT_SET_VERTEX_DECLARATION, g_real_set_vertex_declaration);
    const HRESULT hr = original ? original(self, decl) : E_FAIL;
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
    const auto original = original_method_for<SetStreamSourceFn>(
        self, SLOT_SET_STREAM_SOURCE, g_real_set_stream_source);
    const HRESULT hr = original ? original(self, stream, buffer, offset, stride) : E_FAIL;
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
    const auto original = original_method_for<SetIndicesFn>(
        self, SLOT_SET_INDICES, g_real_set_indices);
    const HRESULT hr = original ? original(self, buffer) : E_FAIL;
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
    const auto original = original_method_for<SetTextureFn>(
        self, SLOT_SET_TEXTURE, g_real_set_texture);
    const HRESULT hr = original ? original(self, stage, texture) : E_FAIL;
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
    const auto original = original_method_for<CreateVertexShaderFn>(
        self, SLOT_CREATE_VERTEX_SHADER, g_real_create_vertex_shader);
    const HRESULT hr = original ? original(self, function, out_shader) : E_FAIL;
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
    const auto original = original_method_for<SetVertexShaderFn>(
        self, SLOT_SET_VERTEX_SHADER, g_real_set_vertex_shader);
    const HRESULT hr = original ? original(self, shader) : E_FAIL;
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
    const auto original = original_method_for<SetVertexShaderConstantFFn>(
        self, SLOT_SET_VERTEX_SHADER_CONSTANT_F, g_real_set_vertex_shader_constant_f);
    const HRESULT hr = original
        ? original(self, start_register, data, vector4f_count)
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
    const auto original = original_method_for<CreatePixelShaderFn>(
        self, SLOT_CREATE_PIXEL_SHADER, g_real_create_pixel_shader);
    const HRESULT hr = original ? original(self, function, out_shader) : E_FAIL;
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
    const auto original = original_method_for<SetPixelShaderFn>(
        self, SLOT_SET_PIXEL_SHADER, g_real_set_pixel_shader);
    const HRESULT hr = original ? original(self, shader) : E_FAIL;
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
    const auto original = original_method_for<SetPixelShaderConstantFFn>(
        self, SLOT_SET_PIXEL_SHADER_CONSTANT_F, g_real_set_pixel_shader_constant_f);
    const HRESULT hr = original
        ? original(self, start_register, data, vector4f_count)
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
    const auto original = original_method_for<DrawIndexedPrimitiveFn>(
        self, SLOT_DRAW_INDEXED_PRIMITIVE, g_real_draw_indexed_primitive);
    const HRESULT hr = original
        ? original(
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
    if (!device || capture_mode() == CaptureMode::Passthrough) return;

    std::vector<VtablePatch> patches = {
        {SLOT_TEST_COOPERATIVE_LEVEL,
         reinterpret_cast<void*>(&hook_test_cooperative_level),
         reinterpret_cast<void**>(&g_real_test_cooperative_level)},
        {SLOT_RESET, reinterpret_cast<void*>(&hook_reset),
         reinterpret_cast<void**>(&g_real_reset)},
        {SLOT_PRESENT, reinterpret_cast<void*>(&hook_present),
         reinterpret_cast<void**>(&g_real_present)},
        {SLOT_BEGIN_SCENE, reinterpret_cast<void*>(&hook_begin_scene),
         reinterpret_cast<void**>(&g_real_begin_scene)},
        {SLOT_END_SCENE, reinterpret_cast<void*>(&hook_end_scene),
         reinterpret_cast<void**>(&g_real_end_scene)},
        {SLOT_CLEAR, reinterpret_cast<void*>(&hook_clear),
         reinterpret_cast<void**>(&g_real_clear)},
    };

    if (capture_mode() == CaptureMode::Capture) {
        const VtablePatch capture_patches[] = {
            {SLOT_CREATE_TEXTURE, reinterpret_cast<void*>(&hook_create_texture),
             reinterpret_cast<void**>(&g_real_create_texture)},
            {SLOT_CREATE_CUBE_TEXTURE, reinterpret_cast<void*>(&hook_create_cube_texture),
             reinterpret_cast<void**>(&g_real_create_cube_texture)},
            {SLOT_CREATE_VERTEX_BUFFER, reinterpret_cast<void*>(&hook_create_vertex_buffer),
             reinterpret_cast<void**>(&g_real_create_vertex_buffer)},
            {SLOT_CREATE_INDEX_BUFFER, reinterpret_cast<void*>(&hook_create_index_buffer),
             reinterpret_cast<void**>(&g_real_create_index_buffer)},
            {SLOT_CREATE_VERTEX_DECLARATION, reinterpret_cast<void*>(&hook_create_vertex_declaration),
             reinterpret_cast<void**>(&g_real_create_vertex_declaration)},
            {SLOT_SET_VERTEX_DECLARATION, reinterpret_cast<void*>(&hook_set_vertex_declaration),
             reinterpret_cast<void**>(&g_real_set_vertex_declaration)},
            {SLOT_SET_STREAM_SOURCE, reinterpret_cast<void*>(&hook_set_stream_source),
             reinterpret_cast<void**>(&g_real_set_stream_source)},
            {SLOT_SET_INDICES, reinterpret_cast<void*>(&hook_set_indices),
             reinterpret_cast<void**>(&g_real_set_indices)},
            {SLOT_SET_TEXTURE, reinterpret_cast<void*>(&hook_set_texture),
             reinterpret_cast<void**>(&g_real_set_texture)},
            {SLOT_CREATE_VERTEX_SHADER, reinterpret_cast<void*>(&hook_create_vertex_shader),
             reinterpret_cast<void**>(&g_real_create_vertex_shader)},
            {SLOT_SET_VERTEX_SHADER, reinterpret_cast<void*>(&hook_set_vertex_shader),
             reinterpret_cast<void**>(&g_real_set_vertex_shader)},
            {SLOT_SET_VERTEX_SHADER_CONSTANT_F,
             reinterpret_cast<void*>(&hook_set_vertex_shader_constant_f),
             reinterpret_cast<void**>(&g_real_set_vertex_shader_constant_f)},
            {SLOT_CREATE_PIXEL_SHADER, reinterpret_cast<void*>(&hook_create_pixel_shader),
             reinterpret_cast<void**>(&g_real_create_pixel_shader)},
            {SLOT_SET_PIXEL_SHADER, reinterpret_cast<void*>(&hook_set_pixel_shader),
             reinterpret_cast<void**>(&g_real_set_pixel_shader)},
            {SLOT_SET_PIXEL_SHADER_CONSTANT_F,
             reinterpret_cast<void*>(&hook_set_pixel_shader_constant_f),
             reinterpret_cast<void**>(&g_real_set_pixel_shader_constant_f)},
            {SLOT_DRAW_INDEXED_PRIMITIVE,
             reinterpret_cast<void*>(&hook_draw_indexed_primitive),
             reinterpret_cast<void**>(&g_real_draw_indexed_primitive)},
        };
        patches.insert(
            patches.end(),
            std::begin(capture_patches),
            std::end(capture_patches));
    }

    void** vtable = *reinterpret_cast<void***>(device);
    const bool installed = patch_object_vtable_batch(
        device, IDIRECT3DDEVICE9_VTABLE_COUNT, patches, "IDirect3DDevice9");
    std::ostringstream fields;
    fields << "\"device_ptr\":" << CaptureWriter::ptr(device)
           << ",\"vtable_ptr\":" << CaptureWriter::ptr(vtable)
           << ",\"mode\":" << CaptureWriter::quote(capture_mode_name())
           << ",\"installed\":" << (installed ? "true" : "false")
           << ",\"strategy\":\"inplace\""
           << ",\"hook_count\":" << patches.size();
    writer().write_event("device_hooks", fields.str());
}

void patch_direct3d9(IDirect3D9* d3d) {
    if (!d3d || capture_mode() == CaptureMode::Passthrough) return;

    void** vtable = *reinterpret_cast<void***>(d3d);
    if (!vtable) {
        writer().write_event("d3d9_hook_failed", "\"reason\":\"null-vtable\"");
        return;
    }

    const bool installed = patch_object_vtable_batch(
        d3d,
        IDIRECT3D9_VTABLE_COUNT,
        {{16, reinterpret_cast<void*>(&hook_create_device),
          reinterpret_cast<void**>(&g_real_create_device)}},
        "IDirect3D9");

    std::ostringstream fields;
    fields << "\"d3d9_ptr\":" << CaptureWriter::ptr(d3d)
           << ",\"vtable_ptr\":" << CaptureWriter::ptr(vtable)
           << ",\"mode\":" << CaptureWriter::quote(capture_mode_name())
           << ",\"installed\":" << (installed ? "true" : "false")
           << ",\"strategy\":\"inplace\"";
    writer().write_event("d3d9_hooks", fields.str());
}

std::string module_path_a(HMODULE module) {
    char path[MAX_PATH] = {};
    const DWORD length = GetModuleFileNameA(module, path, MAX_PATH);
    if (!length || length >= MAX_PATH) return {};
    return std::string(path, length);
}

template <typename T>
T resolve_system_proc(const char* name) {
    return reinterpret_cast<T>(
        g_system_d3d9 ? GetProcAddress(g_system_d3d9, name) : nullptr);
}

std::string absolute_path_a(const std::string& input) {
    if (input.empty()) return {};
    char path[MAX_PATH] = {};
    const DWORD length = GetFullPathNameA(
        input.c_str(), MAX_PATH, path, nullptr);
    if (!length || length >= MAX_PATH) return input;
    return std::string(path, length);
}

bool same_path_ci(const std::string& a, const std::string& b) {
    if (a.empty() || b.empty()) return false;
    const std::string lhs = absolute_path_a(a);
    const std::string rhs = absolute_path_a(b);
    return _stricmp(lhs.c_str(), rhs.c_str()) == 0;
}

bool regular_file_exists_a(const std::string& path) {
    if (path.empty()) return false;
    const DWORD attributes = GetFileAttributesA(path.c_str());
    return attributes != INVALID_FILE_ATTRIBUTES &&
           !(attributes & FILE_ATTRIBUTE_DIRECTORY);
}

struct D3D9BackendChoice {
    std::string path;
    std::string source;
};

D3D9BackendChoice choose_d3d9_backend() {
    const char* explicit_backend = std::getenv("SHIFT_D3D9_BACKEND");
    if (explicit_backend && *explicit_backend) {
        return {absolute_path_a(explicit_backend), "environment"};
    }

    const std::string proxy_path = module_path_a(g_proxy_module);
    const std::size_t separator = proxy_path.find_last_of("\\/");
    if (separator != std::string::npos) {
        const std::string sidecar =
            proxy_path.substr(0, separator + 1) + "d3d9.shift_backend.dll";
        if (regular_file_exists_a(sidecar)) {
            return {absolute_path_a(sidecar), "sidecar"};
        }
    }

    char system_dir[MAX_PATH] = {};
    const UINT length = GetSystemDirectoryA(system_dir, MAX_PATH);
    if (!length || length >= MAX_PATH) {
        return {{}, "system"};
    }
    std::string system_path(system_dir, length);
    if (!system_path.empty() &&
        system_path.back() != '\\' &&
        system_path.back() != '/') {
        system_path.push_back('\\');
    }
    system_path += "d3d9.dll";
    return {absolute_path_a(system_path), "system"};
}

bool ensure_system_d3d9() {
    std::call_once(g_system_d3d9_once, [] {
        const D3D9BackendChoice backend = choose_d3d9_backend();
        g_system_d3d9_path = backend.path;
        g_d3d9_backend_source = backend.source;

        {
            std::ostringstream fields;
            fields << "\"source\":" << CaptureWriter::quote(g_d3d9_backend_source)
                   << ",\"path\":" << CaptureWriter::quote(g_system_d3d9_path)
                   << ",\"proxy_path\":" << CaptureWriter::quote(
                          module_path_a(g_proxy_module));
            writer().write_event("proxy_d3d9_backend_selected", fields.str());
        }

        if (g_system_d3d9_path.empty()) {
            writer().write_event(
                "proxy_system_d3d9_load_failed",
                "\"reason\":\"backend-path-unresolved\",\"source\":" +
                    CaptureWriter::quote(g_d3d9_backend_source) +
                    ",\"win32_error\":" + std::to_string(GetLastError()));
            return;
        }

        const std::string proxy_path = module_path_a(g_proxy_module);
        if (same_path_ci(g_system_d3d9_path, proxy_path)) {
            std::ostringstream fields;
            fields << "\"reason\":\"backend-resolves-to-proxy\""
                   << ",\"source\":" << CaptureWriter::quote(g_d3d9_backend_source)
                   << ",\"path\":" << CaptureWriter::quote(g_system_d3d9_path);
            writer().write_event("proxy_system_d3d9_load_failed", fields.str());
            return;
        }

        SetLastError(ERROR_SUCCESS);
        g_system_d3d9 = LoadLibraryA(g_system_d3d9_path.c_str());
        if (!g_system_d3d9) {
            std::ostringstream fields;
            fields << "\"path\":" << CaptureWriter::quote(g_system_d3d9_path)
                   << ",\"source\":" << CaptureWriter::quote(g_d3d9_backend_source)
                   << ",\"win32_error\":" << GetLastError();
            writer().write_event("proxy_system_d3d9_load_failed", fields.str());
            return;
        }

        g_real_direct3d_create9 =
            resolve_system_proc<Direct3DCreate9Fn>("Direct3DCreate9");
        g_real_direct3d_create9_ex =
            resolve_system_proc<Direct3DCreate9ExFn>("Direct3DCreate9Ex");
        g_real_d3dperf_begin_event =
            resolve_system_proc<D3DPERFBeginEventFn>("D3DPERF_BeginEvent");
        g_real_d3dperf_end_event =
            resolve_system_proc<D3DPERFEndEventFn>("D3DPERF_EndEvent");
        g_real_d3dperf_get_status =
            resolve_system_proc<D3DPERFGetStatusFn>("D3DPERF_GetStatus");
        g_real_d3dperf_query_repeat_frame =
            resolve_system_proc<D3DPERFQueryRepeatFrameFn>("D3DPERF_QueryRepeatFrame");
        g_real_d3dperf_set_marker =
            resolve_system_proc<D3DPERFSetMarkerFn>("D3DPERF_SetMarker");
        g_real_d3dperf_set_options =
            resolve_system_proc<D3DPERFSetOptionsFn>("D3DPERF_SetOptions");
        g_real_d3dperf_set_region =
            resolve_system_proc<D3DPERFSetRegionFn>("D3DPERF_SetRegion");
        g_real_debug_set_level =
            resolve_system_proc<DebugSetLevelFn>("DebugSetLevel");
        g_real_debug_set_mute =
            resolve_system_proc<DebugSetMuteFn>("DebugSetMute");

        g_system_d3d9_ready = g_real_direct3d_create9 != nullptr;

        std::ostringstream fields;
        fields << "\"path\":" << CaptureWriter::quote(g_system_d3d9_path)
               << ",\"source\":" << CaptureWriter::quote(g_d3d9_backend_source)
               << ",\"module_ptr\":" << CaptureWriter::ptr(g_system_d3d9)
               << ",\"direct3dcreate9\":" << (g_real_direct3d_create9 ? "true" : "false")
               << ",\"direct3dcreate9ex\":" << (g_real_direct3d_create9_ex ? "true" : "false")
               << ",\"perf_begin\":" << (g_real_d3dperf_begin_event ? "true" : "false")
               << ",\"perf_end\":" << (g_real_d3dperf_end_event ? "true" : "false");
        writer().write_event(
            g_system_d3d9_ready ? "proxy_system_d3d9_ready"
                                : "proxy_system_d3d9_missing_required_export",
            fields.str());
    });
    return g_system_d3d9_ready;
}

} // namespace

extern "C" IDirect3D9* WINAPI Direct3DCreate9(UINT sdk_version) {
    ensure_crash_diagnostics();
    bool expected = false;
    if (g_proxy_entry_reported.compare_exchange_strong(expected, true)) {
        std::ostringstream fields;
        fields << "\"sdk_version\":" << sdk_version
               << ",\"mode\":" << CaptureWriter::quote(capture_mode_name())
               << ",\"proxy_path\":" << CaptureWriter::quote(module_path_a(g_proxy_module))
               << ",\"executable_path\":" << CaptureWriter::quote(module_path_a(nullptr));
        writer().write_event("proxy_direct3dcreate9", fields.str());
    }

    if (!ensure_system_d3d9()) return nullptr;

    IDirect3D9* d3d = g_real_direct3d_create9(sdk_version);
    {
        std::ostringstream fields;
        fields << "\"sdk_version\":" << sdk_version
               << ",\"d3d9_ptr\":" << CaptureWriter::ptr(d3d)
               << ",\"success\":" << (d3d ? "true" : "false");
        writer().write_event("direct3dcreate9_result", fields.str());
    }
    if (d3d && capture_mode() != CaptureMode::Passthrough) patch_direct3d9(d3d);
    return d3d;
}

extern "C" HRESULT WINAPI Direct3DCreate9Ex(
    UINT sdk_version,
    IDirect3D9Ex** out_d3d) {
    ensure_crash_diagnostics();
    if (out_d3d) *out_d3d = nullptr;
    if (!ensure_system_d3d9() || !g_real_direct3d_create9_ex) {
        return E_NOINTERFACE;
    }

    const HRESULT hr = g_real_direct3d_create9_ex(sdk_version, out_d3d);
    std::ostringstream fields;
    fields << "\"sdk_version\":" << sdk_version
           << ",\"hresult\":" << hresult_hex(hr)
           << ",\"d3d9ex_ptr\":" << CaptureWriter::ptr(
                  out_d3d ? *out_d3d : nullptr);
    writer().write_event("direct3dcreate9ex_result", fields.str());

    if (SUCCEEDED(hr) && out_d3d && *out_d3d &&
        capture_mode() != CaptureMode::Passthrough) {
        patch_direct3d9(static_cast<IDirect3D9*>(*out_d3d));
    }
    return hr;
}

extern "C" int WINAPI D3DPERF_BeginEvent(D3DCOLOR color, LPCWSTR name) {
    if (!ensure_system_d3d9() || !g_real_d3dperf_begin_event) return -1;
    const int result = g_real_d3dperf_begin_event(color, name);
    const auto index = g_perf_event_calls.fetch_add(1);
    if (index < 8) {
        std::ostringstream fields;
        fields << "\"call\":" << index
               << ",\"color\":" << color
               << ",\"result\":" << result;
        writer().write_event("d3dperf_begin_event", fields.str());
    }
    return result;
}

extern "C" int WINAPI D3DPERF_EndEvent() {
    if (!ensure_system_d3d9() || !g_real_d3dperf_end_event) return -1;
    return g_real_d3dperf_end_event();
}

extern "C" DWORD WINAPI D3DPERF_GetStatus() {
    return (ensure_system_d3d9() && g_real_d3dperf_get_status)
        ? g_real_d3dperf_get_status()
        : 0;
}

extern "C" BOOL WINAPI D3DPERF_QueryRepeatFrame() {
    return (ensure_system_d3d9() && g_real_d3dperf_query_repeat_frame)
        ? g_real_d3dperf_query_repeat_frame()
        : FALSE;
}

extern "C" void WINAPI D3DPERF_SetMarker(D3DCOLOR color, LPCWSTR name) {
    if (ensure_system_d3d9() && g_real_d3dperf_set_marker) {
        g_real_d3dperf_set_marker(color, name);
    }
}

extern "C" void WINAPI D3DPERF_SetOptions(DWORD options) {
    if (ensure_system_d3d9() && g_real_d3dperf_set_options) {
        g_real_d3dperf_set_options(options);
    }
}

extern "C" void WINAPI D3DPERF_SetRegion(D3DCOLOR color, LPCWSTR name) {
    if (ensure_system_d3d9() && g_real_d3dperf_set_region) {
        g_real_d3dperf_set_region(color, name);
    }
}

extern "C" void WINAPI DebugSetLevel(DWORD level) {
    if (ensure_system_d3d9() && g_real_debug_set_level) {
        g_real_debug_set_level(level);
    }
}

extern "C" void WINAPI DebugSetMute() {
    if (ensure_system_d3d9() && g_real_debug_set_mute) {
        g_real_debug_set_mute();
    }
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        g_proxy_module = instance;
        DisableThreadLibraryCalls(instance);
    }
    return TRUE;
}

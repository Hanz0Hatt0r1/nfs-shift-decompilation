#include "shift_recompiled_pcode_module.hpp"
#include "shift_d3dx9_effect_binary.hpp"
#include "shift_d3dx9_retail_effects.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <sys/syscall.h>
#include <unistd.h>
#include <vector>

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

class StderrCapture {
public:
    StderrCapture() : file_(std::tmpfile()), saved_fd_(dup(STDERR_FILENO)) {
        require(file_ != nullptr && saved_fd_ >= 0,
                "could not create stderr capture fixture");
        std::fflush(stderr);
        require(dup2(fileno(file_), STDERR_FILENO) >= 0,
                "could not redirect stderr for trace fixture");
    }

    ~StderrCapture() {
        std::fflush(stderr);
        if (saved_fd_ >= 0) {
            (void)dup2(saved_fd_, STDERR_FILENO);
            close(saved_fd_);
        }
        if (file_) std::fclose(file_);
    }

    std::string text() {
        std::fflush(stderr);
        std::rewind(file_);
        std::string result;
        char buffer[512];
        size_t count = 0;
        while ((count = std::fread(buffer, 1, sizeof(buffer), file_)) != 0) {
            result.append(buffer, count);
        }
        return result;
    }

private:
    std::FILE* file_ = nullptr;
    int saved_fd_ = -1;
};

void write_u16(std::vector<uint8_t>& bytes, size_t offset, uint16_t value) {
    bytes.at(offset) = static_cast<uint8_t>(value);
    bytes.at(offset + 1) = static_cast<uint8_t>(value >> 8);
}

void write_u32(std::vector<uint8_t>& bytes, size_t offset, uint32_t value) {
    for (size_t i = 0; i < 4; ++i) {
        bytes.at(offset + i) = static_cast<uint8_t>(value >> (i * 8));
    }
}

void write_guest_u32(shift::runtime::RecompiledPcodeModule& module,
                     const char* space, uint64_t offset, uint32_t value) {
    const std::array<uint8_t, 4> bytes = {
        static_cast<uint8_t>(value), static_cast<uint8_t>(value >> 8),
        static_cast<uint8_t>(value >> 16),
        static_cast<uint8_t>(value >> 24)};
    require(module.write_guest(space, offset, bytes.size(), bytes.data()),
            "could not write guest word");
}

void write_guest_bytes(shift::runtime::RecompiledPcodeModule& module,
                       uint32_t address, const uint8_t* data, size_t size) {
    for (size_t offset = 0; offset < size; offset += 16) {
        const size_t chunk = std::min<size_t>(16, size - offset);
        require(module.write_guest("ram", static_cast<uint64_t>(address) + offset,
                                   chunk, data + offset),
                "could not write guest byte range");
    }
}

struct D3d9BackendFixture {
    bool called = false;
    uint32_t focus_window = 0;
    uint32_t behavior_flags = 0;
    uint32_t clear_calls = 0;
    uint32_t clear_flags = 0;
    uint32_t clear_color = 0;
    uint32_t clear_depth_bits = 0;
    uint32_t clear_stencil = 0;
    uint32_t clear_rect_count = 0;
    uint32_t present_calls = 0;
    bool vertex_buffer_create_called = false;
    bool vertex_buffer_update_called = false;
    bool vertex_buffer_release_called = false;
    uint32_t vertex_buffer_address = 0;
    uint32_t vertex_buffer_device = 0;
    uint32_t vertex_buffer_size = 0;
    uint32_t vertex_buffer_usage = 0;
    uint32_t vertex_buffer_fvf = 0;
    uint32_t vertex_buffer_pool = 0;
    uint32_t vertex_buffer_update_offset = 0;
    size_t vertex_buffer_update_size = 0;
    std::array<uint8_t, 64> vertex_buffer_update_data{};
    bool index_buffer_create_called = false;
    bool index_buffer_update_called = false;
    bool index_buffer_release_called = false;
    uint32_t index_buffer_address = 0;
    uint32_t index_buffer_device = 0;
    uint32_t index_buffer_size = 0;
    uint32_t index_buffer_usage = 0;
    uint32_t index_buffer_format = 0;
    uint32_t index_buffer_pool = 0;
    uint32_t index_buffer_update_offset = 0;
    size_t index_buffer_update_size = 0;
    std::array<uint8_t, 64> index_buffer_update_data{};
    shift::runtime::RecompiledGuestD3d9PresentationParameters parameters{};
};

bool create_d3d9_fixture_device(
    void* context, uint32_t focus_window, uint32_t behavior_flags,
    shift::runtime::RecompiledGuestD3d9PresentationParameters& parameters,
    std::string&) {
    auto* fixture = static_cast<D3d9BackendFixture*>(context);
    if (!fixture) return false;
    fixture->called = true;
    fixture->focus_window = focus_window;
    fixture->behavior_flags = behavior_flags;
    fixture->parameters = parameters;
    return true;
}

bool clear_d3d9_fixture(void* context, uint32_t flags, uint32_t color,
                        uint32_t depth_bits, uint32_t stencil,
                        uint32_t rect_count, std::string&) {
    auto* fixture = static_cast<D3d9BackendFixture*>(context);
    if (!fixture) return false;
    ++fixture->clear_calls;
    fixture->clear_flags = flags;
    fixture->clear_color = color;
    fixture->clear_depth_bits = depth_bits;
    fixture->clear_stencil = stencil;
    fixture->clear_rect_count = rect_count;
    return true;
}

bool present_d3d9_fixture(void* context, std::string&) {
    auto* fixture = static_cast<D3d9BackendFixture*>(context);
    if (!fixture) return false;
    ++fixture->present_calls;
    return true;
}

bool create_d3d9_fixture_vertex_buffer(
    void* context, uint32_t guest_buffer, uint32_t guest_device,
    uint32_t size, uint32_t usage, uint32_t fvf, uint32_t pool,
    std::string& error) {
    auto* fixture = static_cast<D3d9BackendFixture*>(context);
    if (!fixture || size > fixture->vertex_buffer_update_data.size()) {
        error = "fixture vertex buffer is too large";
        return false;
    }
    fixture->vertex_buffer_create_called = true;
    fixture->vertex_buffer_address = guest_buffer;
    fixture->vertex_buffer_device = guest_device;
    fixture->vertex_buffer_size = size;
    fixture->vertex_buffer_usage = usage;
    fixture->vertex_buffer_fvf = fvf;
    fixture->vertex_buffer_pool = pool;
    return true;
}

bool update_d3d9_fixture_vertex_buffer(
    void* context, uint32_t guest_buffer, uint32_t offset,
    const uint8_t* data, size_t size, std::string& error) {
    auto* fixture = static_cast<D3d9BackendFixture*>(context);
    if (!fixture || guest_buffer != fixture->vertex_buffer_address || !data ||
        offset > fixture->vertex_buffer_size ||
        size > fixture->vertex_buffer_size - offset ||
        size > fixture->vertex_buffer_update_data.size()) {
        error = "fixture vertex buffer update is out of range";
        return false;
    }
    fixture->vertex_buffer_update_called = true;
    fixture->vertex_buffer_update_offset = offset;
    fixture->vertex_buffer_update_size = size;
    std::copy_n(data, size, fixture->vertex_buffer_update_data.begin());
    return true;
}

void release_d3d9_fixture_vertex_buffer(void* context,
                                        uint32_t guest_buffer) {
    auto* fixture = static_cast<D3d9BackendFixture*>(context);
    if (fixture && fixture->vertex_buffer_address == guest_buffer)
        fixture->vertex_buffer_release_called = true;
}

bool create_d3d9_fixture_index_buffer(
    void* context, uint32_t guest_buffer, uint32_t guest_device,
    uint32_t size, uint32_t usage, uint32_t format, uint32_t pool,
    std::string& error) {
    auto* fixture = static_cast<D3d9BackendFixture*>(context);
    if (!fixture || size > fixture->index_buffer_update_data.size()) {
        error = "fixture index buffer is too large";
        return false;
    }
    fixture->index_buffer_create_called = true;
    fixture->index_buffer_address = guest_buffer;
    fixture->index_buffer_device = guest_device;
    fixture->index_buffer_size = size;
    fixture->index_buffer_usage = usage;
    fixture->index_buffer_format = format;
    fixture->index_buffer_pool = pool;
    return true;
}

bool update_d3d9_fixture_index_buffer(
    void* context, uint32_t guest_buffer, uint32_t offset,
    const uint8_t* data, size_t size, std::string& error) {
    auto* fixture = static_cast<D3d9BackendFixture*>(context);
    if (!fixture || guest_buffer != fixture->index_buffer_address || !data ||
        offset > fixture->index_buffer_size ||
        size > fixture->index_buffer_size - offset ||
        size > fixture->index_buffer_update_data.size()) {
        error = "fixture index buffer update is out of range";
        return false;
    }
    fixture->index_buffer_update_called = true;
    fixture->index_buffer_update_offset = offset;
    fixture->index_buffer_update_size = size;
    std::copy_n(data, size, fixture->index_buffer_update_data.begin());
    return true;
}

void release_d3d9_fixture_index_buffer(void* context,
                                       uint32_t guest_buffer) {
    auto* fixture = static_cast<D3d9BackendFixture*>(context);
    if (fixture && fixture->index_buffer_address == guest_buffer)
        fixture->index_buffer_release_called = true;
}

uint32_t read_guest_u32(shift::runtime::RecompiledPcodeModule& module,
                        const char* space, uint64_t offset) {
    std::array<uint8_t, 4> bytes{};
    require(module.read_guest(space, offset, bytes.size(), bytes.data()),
            "could not read guest word");
    return static_cast<uint32_t>(bytes[0]) |
           (static_cast<uint32_t>(bytes[1]) << 8) |
           (static_cast<uint32_t>(bytes[2]) << 16) |
           (static_cast<uint32_t>(bytes[3]) << 24);
}

uint16_t read_guest_u16(shift::runtime::RecompiledPcodeModule& module,
                        const char* space, uint64_t offset) {
    std::array<uint8_t, 2> bytes{};
    require(module.read_guest(space, offset, bytes.size(), bytes.data()),
            "could not read guest halfword");
    return static_cast<uint16_t>(bytes[0]) |
           (static_cast<uint16_t>(bytes[1]) << 8);
}

uint64_t read_guest_u64(shift::runtime::RecompiledPcodeModule& module,
                        const char* space, uint64_t offset) {
    std::array<uint8_t, 8> bytes{};
    require(module.read_guest(space, offset, bytes.size(), bytes.data()),
            "could not read guest double word");
    uint64_t value = 0;
    for (size_t index = 0; index < bytes.size(); ++index)
        value |= static_cast<uint64_t>(bytes[index]) << (index * 8);
    return value;
}

int call_import(shift::runtime::RecompiledPcodeModule& module,
                uint32_t address, const std::vector<uint32_t>& arguments) {
    constexpr uint32_t stack_pointer = 0x00032000;
    write_guest_u32(module, "ram", stack_pointer, 0x00401234);
    for (size_t index = 0; index < arguments.size(); ++index)
        write_guest_u32(module, "ram", stack_pointer + 4 + index * 4,
                        arguments[index]);
    write_guest_u32(module, "register", 0x10, stack_pointer);
    return module.call(address);
}

uint32_t invoke_import(shift::runtime::RecompiledPcodeModule& module,
                       uint32_t address,
                       const std::vector<uint32_t>& arguments) {
    constexpr uint32_t stack_pointer = 0x00032000;
    const int result = call_import(module, address, arguments);
    require(result == 0,
            "guest import dispatch failed at " +
                std::to_string(address) + " returned " +
                std::to_string(result) + ": " + module.last_error());
    const uint32_t expected_esp = static_cast<uint32_t>(
        stack_pointer + 4 + arguments.size() * 4);
    const uint32_t actual_esp = read_guest_u32(module, "register", 0x10);
    require(actual_esp == expected_esp,
            "PE import " + std::to_string(address) +
                " applied incorrect stdcall cleanup: ESP=" +
                std::to_string(actual_esp) + " expected=" +
                std::to_string(expected_esp));
    return read_guest_u32(module, "register", 0);
}

void write_pe32_fixture(const std::string& path,
                        bool raise_exception_import = false,
                        bool time_get_time_import = false,
                        bool unknown_first_import = false,
                        bool read_file_ex_import = false,
                        bool create_directory_import = false,
                        bool write_file_import = false,
                        bool get_version_ex_w_import = false,
                        bool set_file_pointer_import = false,
                        bool stack_walk64_import = false) {
    constexpr size_t file_size = 0x1300;
    constexpr size_t pe_offset = 0x80;
    constexpr size_t optional_offset = pe_offset + 24;
    constexpr size_t section_offset = optional_offset + 0xe0;
    constexpr size_t import_section_offset = section_offset + 40;
    std::vector<uint8_t> bytes(file_size, 0);
    bytes[0] = 'M';
    bytes[1] = 'Z';
    write_u32(bytes, 0x3c, pe_offset);
    bytes[pe_offset] = 'P';
    bytes[pe_offset + 1] = 'E';
    write_u16(bytes, pe_offset + 4, 0x014c);
    write_u16(bytes, pe_offset + 6, 2);
    write_u16(bytes, pe_offset + 20, 0xe0);

    write_u16(bytes, optional_offset, 0x010b);
    write_u32(bytes, optional_offset + 16, 0x1020);
    write_u32(bytes, optional_offset + 28, 0x00400000);
    write_u32(bytes, optional_offset + 32, 0x1000);
    write_u32(bytes, optional_offset + 36, 0x200);
    write_u32(bytes, optional_offset + 56, 0x3000);
    write_u32(bytes, optional_offset + 60, 0x200);
    write_u32(bytes, optional_offset + 92, 16);
    write_u32(bytes, optional_offset + 104, 0x2000);
    write_u32(bytes, optional_offset + 108, 100);

    bytes[section_offset] = '.';
    bytes[section_offset + 1] = 't';
    bytes[section_offset + 2] = 'e';
    bytes[section_offset + 3] = 'x';
    bytes[section_offset + 4] = 't';
    write_u32(bytes, section_offset + 8, 0x300);
    write_u32(bytes, section_offset + 12, 0x1000);
    write_u32(bytes, section_offset + 16, 0x200);
    write_u32(bytes, section_offset + 20, 0x200);
    bytes[import_section_offset] = '.';
    bytes[import_section_offset + 1] = 'i';
    bytes[import_section_offset + 2] = 'd';
    bytes[import_section_offset + 3] = 'a';
    bytes[import_section_offset + 4] = 't';
    bytes[import_section_offset + 5] = 'a';
    write_u32(bytes, import_section_offset + 8, 0xf00);
    write_u32(bytes, import_section_offset + 12, 0x2000);
    write_u32(bytes, import_section_offset + 16, 0xf00);
    write_u32(bytes, import_section_offset + 20, 0x400);
    std::fill(bytes.begin() + 0x200, bytes.begin() + 0x400, 0x90);
    bytes[0x200] = 'P';
    bytes[0x201] = '3';
    bytes[0x202] = '2';
    bytes[0x203] = '!';
    bytes[0x300] = 0xff;
    bytes[0x301] = 0x15;
    write_u32(bytes, 0x302, 0x00402c3c);
    bytes[0x306] = 0xc2;
    bytes[0x307] = 0x04;
    bytes[0x308] = 0x00;
    bytes[0x320] = 0xff;
    bytes[0x321] = 0x25;
    write_u32(bytes, 0x322, 0x00402c10);

    write_u32(bytes, 0x400, 0x2064);
    write_u32(bytes, 0x40c, 0x2de0);
    write_u32(bytes, 0x410, 0x2c00);
    write_u32(bytes, 0x414, 0x21a0);
    write_u32(bytes, 0x420, 0x2a60);
    write_u32(bytes, 0x424, 0x2d20);
    write_u32(bytes, 0x428, 0x21c0);
    write_u32(bytes, 0x434, 0x2dd0);
    write_u32(bytes, 0x438, 0x2d40);
    write_u32(bytes, 0x43c, 0x2d58);
    write_u32(bytes, 0x448, 0x2de0);
    write_u32(bytes, 0x44c, 0x2d30);
    const auto write_import_name = [&](size_t offset, const char* name) {
        write_u16(bytes, offset, 0);
        std::copy_n(name, std::char_traits<char>::length(name) + 1,
                    bytes.begin() + offset + 2);
    };
    const std::array<uint32_t, 72> import_thunks = {
        0x2200, 0x8000007b, 0x2240, 0x2260, 0x2280, 0x22a0, 0x22c0,
        0x22e0, 0x2300, 0x2320, 0x2340, 0x2360, 0x2380, 0x23a0,
        0x23c0, 0x23e0, 0x2400, 0x2420, 0x2440, 0x2460, 0x24a0,
        0x24c0, 0x24e0, 0x2500, 0x2520, 0x2540, 0x2560, 0x2580,
        0x25a0, 0x25c0, 0x25e0, 0x2600, 0x2640, 0x2680, 0x26a0,
        0x26c0, 0x2700, 0x2720, 0x2740, 0x2760, 0x2780, 0x27a0,
        0x27c0, 0x27e0, 0x2800, 0x2820, 0x2840, 0x2860, 0x2880,
        0x28a0, 0x28c0, 0x28e0, 0x2900, 0x2920, 0x2940, 0x2960, 0x2980,
        0x29a0, 0x29c0, 0x29e0, 0x2a00, 0x2a20, 0x2a40, 0x2ad0,
        0x2af0, 0x2b10, 0x2b30, 0x2b50, 0x2b70, 0x2b90, 0x2bb0,
        0x2bd0};
    for (size_t index = 0; index < import_thunks.size(); ++index) {
        write_u32(bytes, 0x464 + index * sizeof(uint32_t), import_thunks[index]);
        write_u32(bytes, 0x1000 + index * sizeof(uint32_t), import_thunks[index]);
    }
    write_u32(bytes, 0x5a0, 0x2a80);
    write_u32(bytes, 0x5a4, 0x2aa0);
    write_u32(bytes, 0x5a8, 0x2ac0);
    write_u32(bytes, 0x5c0, 0x2da0);
    write_u32(bytes, 0x5c4, 0x2dc0);
    write_u32(bytes, 0x1130, 0x2d88);
    write_u32(bytes, 0x1134, 0x2ded);
    write_u32(bytes, 0x1138, 0x2d68);
    write_u32(bytes, 0x1158, 0x2d88);
    write_u32(bytes, 0x115c, 0x2ded);
    write_u32(bytes, 0x1160, 0x2e18);
    write_u32(bytes, 0x1164, 0x2e00);
    write_u32(bytes, 0x113c, 0x2e00);
    std::copy_n("KERNEL32.dll", 12, bytes.begin() + 0x11e0);
    std::copy_n("WINMM.dll", 10, bytes.begin() + 0x11d0);
    write_u32(bytes, 0x1120, 0x2a80);
    write_u32(bytes, 0x1124, 0x2aa0);
    write_u32(bytes, 0x1128, 0x2ac0);
    write_import_name(
        0x600, unknown_first_import
                   ? "UnknownApi"
                   : (raise_exception_import ? "RaiseException" : "Sleep"));
    write_import_name(0x640, "GetSystemTimeAsFileTime");
    write_import_name(0x660, "GetCurrentProcessId");
    write_import_name(0x680, create_directory_import ? "CreateDirectoryA"
                                                     : "GetCurrentThreadId");
    write_import_name(0x6a0, "GetTickCount");
    write_import_name(0x6c0, "QueryPerformanceCounter");
    write_import_name(0x6e0, "QueryPerformanceFrequency");
    write_import_name(0x700, "GetStartupInfoA");
    write_import_name(0x720, "GetProcessHeap");
    write_import_name(0x740, "HeapAlloc");
    write_import_name(0x760, get_version_ex_w_import ? "GetVersionExW"
                                                     : "GetVersionExA");
    write_import_name(0x780, "HeapFree");
    write_import_name(0x7a0, "HeapCreate");
    write_import_name(0x7c0, "GetProcAddress");
    write_import_name(0x7e0, "TlsAlloc");
    write_import_name(0x800, "TlsGetValue");
    write_import_name(0x820, "TlsSetValue");
    write_import_name(0x840, "TlsFree");
    write_import_name(0x860, "InitializeCriticalSectionAndSpinCount");
    write_import_name(0x8a0, "InterlockedIncrement");
    write_import_name(0x8c0, "EnterCriticalSection");
    write_import_name(0x8e0, "LeaveCriticalSection");
    write_import_name(0x900, "TryEnterCriticalSection");
    write_import_name(0x920, "DeleteCriticalSection");
    write_import_name(0x940, "InitializeCriticalSection");
    write_import_name(0x960, "SetCriticalSectionSpinCount");
    write_import_name(0x980, "GetStdHandle");
    write_import_name(0x9a0, "GetFileType");
    write_import_name(0x9c0, "SetHandleCount");
    write_import_name(0x9e0, "GetCommandLineA");
    write_import_name(0xa00, "GetEnvironmentStringsW");
    write_import_name(0xa40, "FreeEnvironmentStringsW");
    write_import_name(0xa80, "GetEnvironmentStrings");
    write_import_name(0xaa0, "FreeEnvironmentStringsA");
    write_import_name(0xac0, "WideCharToMultiByte");
    write_import_name(0xb00, "GetLastError");
    write_import_name(0xb20, "SetLastError");
    write_import_name(0xb40, "GetACP");
    write_import_name(0xb60, "IsValidCodePage");
    write_import_name(0xb80, "GetCPInfo");
    write_import_name(0xba0, "GetStringTypeW");
    write_import_name(0xbc0, "MultiByteToWideChar");
    write_import_name(0xbe0, "LCMapStringW");
    write_import_name(0xc00, "InterlockedDecrement");
    write_import_name(0xc20, "GetModuleFileNameA");
    write_import_name(0xc40, "SetUnhandledExceptionFilter");
    write_import_name(0xc60, "HeapSize");
    write_import_name(0xc80, "CreateMutexA");
    write_import_name(0xca0, "WaitForSingleObject");
    write_import_name(0xcc0, "ReleaseMutex");
    write_import_name(0xce0, "GetEnvironmentVariableA");
    write_import_name(0xd00, "SetEnvironmentVariableA");
    write_import_name(0xd20, "CloseHandle");
    write_import_name(0xd40, "GetCurrentProcess");
    write_import_name(0xd60, "GetPriorityClass");
    write_import_name(0xd80, "GetCurrentThread");
    write_import_name(0xda0, "GetThreadPriority");
    write_import_name(0xdc0, "SetPriorityClass");
    write_import_name(0xde0, "SetThreadPriority");
    write_import_name(0xe00, "CreateFileA");
    write_import_name(0xe20, set_file_pointer_import ? "SetFilePointer"
                                                     : "GetFileSize");
    write_import_name(0xe40, write_file_import
                                 ? "WriteFile"
                                 : read_file_ex_import ? "ReadFileEx" : "ReadFile");
    std::copy_n("imagehlp.dll", 13, bytes.begin() + 0xe60);
    write_import_name(0xe80, "SymSetOptions");
    write_import_name(0xea0, "SymInitialize");
    write_import_name(0xec0,
                      stack_walk64_import ? "StackWalk64" : "SymCleanup");
    write_import_name(0xed0, "CreateEventW");
    write_import_name(0xef0, "CreateEventA");
    write_import_name(0xf10, "SetEvent");
    write_import_name(0xf30, "ResetEvent");
    write_import_name(0xf50, "WaitForSingleObjectEx");
    write_import_name(0xf70, "InterlockedCompareExchange");
    write_import_name(0xf90, "VirtualAlloc");
    write_import_name(0xfb0, "VirtualFree");
    write_import_name(0x11a0, "timeBeginPeriod");
    write_import_name(0x11c0, time_get_time_import
                                   ? "timeGetTime"
                                   : "timeEndPeriod");
    write_import_name(0x1188, "ConvertThreadToFiber");
    write_import_name(0x11ed, "IsThreadAFiber");
    write_import_name(0x1200, "GlobalMemoryStatus");
    write_import_name(0x1218, "GetLocalTime");
    write_import_name(0xfd0, "HeapReAlloc");

    std::ofstream file(path, std::ios::binary | std::ios::trunc);
    require(static_cast<bool>(file), "could not create PE32 fixture");
    file.write(reinterpret_cast<const char*>(bytes.data()),
               static_cast<std::streamsize>(bytes.size()));
    require(static_cast<bool>(file), "could not write PE32 fixture");
}

void write_wsa_startup_pe32_fixture(const std::string& path) {
    constexpr size_t file_size = 0x800;
    constexpr size_t pe_offset = 0x80;
    constexpr size_t optional_offset = pe_offset + 24;
    constexpr size_t section_offset = optional_offset + 0xe0;
    constexpr size_t idata_section_offset = section_offset + 40;
    std::vector<uint8_t> bytes(file_size, 0);
    bytes[0] = 'M';
    bytes[1] = 'Z';
    write_u32(bytes, 0x3c, pe_offset);
    bytes[pe_offset] = 'P';
    bytes[pe_offset + 1] = 'E';
    write_u16(bytes, pe_offset + 4, 0x014c);
    write_u16(bytes, pe_offset + 6, 2);
    write_u16(bytes, pe_offset + 20, 0xe0);
    write_u16(bytes, optional_offset, 0x010b);
    write_u32(bytes, optional_offset + 16, 0x1020);
    write_u32(bytes, optional_offset + 28, 0x00400000);
    write_u32(bytes, optional_offset + 32, 0x1000);
    write_u32(bytes, optional_offset + 36, 0x200);
    write_u32(bytes, optional_offset + 56, 0x3000);
    write_u32(bytes, optional_offset + 60, 0x200);
    write_u32(bytes, optional_offset + 92, 16);
    write_u32(bytes, optional_offset + 104, 0x2000);
    write_u32(bytes, optional_offset + 108, 0x3c);

    std::copy_n(".text", 5, bytes.begin() + section_offset);
    write_u32(bytes, section_offset + 8, 0x300);
    write_u32(bytes, section_offset + 12, 0x1000);
    write_u32(bytes, section_offset + 16, 0x200);
    write_u32(bytes, section_offset + 20, 0x200);
    std::copy_n(".idata", 6, bytes.begin() + idata_section_offset);
    write_u32(bytes, idata_section_offset + 8, 0x400);
    write_u32(bytes, idata_section_offset + 12, 0x2000);
    write_u32(bytes, idata_section_offset + 16, 0x400);
    write_u32(bytes, idata_section_offset + 20, 0x400);
    std::copy_n("P32!", 4, bytes.begin() + 0x200);

    write_u32(bytes, 0x400, 0x2040);
    write_u32(bytes, 0x40c, 0x2060);
    write_u32(bytes, 0x410, 0x2080);
    write_u32(bytes, 0x414, 0x20c0);
    write_u32(bytes, 0x420, 0x20e0);
    write_u32(bytes, 0x424, 0x2100);
    write_u32(bytes, 0x440, 0x80000073);
    write_u32(bytes, 0x444, 0x80000074);
    write_u32(bytes, 0x448, 0x20a0);
    write_u32(bytes, 0x480, 0x80000073);
    write_u32(bytes, 0x484, 0x80000074);
    write_u32(bytes, 0x488, 0x20a0);
    std::copy_n("WS2_32.dll", 11, bytes.begin() + 0x460);
    write_u16(bytes, 0x4a0, 0);
    std::copy_n("WSAWaitForMultipleEvents", 25, bytes.begin() + 0x4a2);
    write_u32(bytes, 0x4c0, 0x2140);
    write_u32(bytes, 0x500, 0x2140);
    std::copy_n("KERNEL32.dll", 13, bytes.begin() + 0x4e0);
    write_u16(bytes, 0x540, 0);
    std::copy_n("CreateEventW", 13, bytes.begin() + 0x542);

    std::ofstream file(path, std::ios::binary | std::ios::trunc);
    require(static_cast<bool>(file), "could not create Winsock PE32 fixture");
    file.write(reinterpret_cast<const char*>(bytes.data()),
               static_cast<std::streamsize>(bytes.size()));
    require(static_cast<bool>(file), "could not write Winsock PE32 fixture");
}

void write_system_parameters_info_pe32_fixture(
    const std::string& path, bool find_window_w_import = false,
    bool reg_open_key_ex_w_import = false,
    bool register_device_notification_w_import = false,
    bool unregister_device_notification_import = false,
    bool direct_input8_create_import = false) {
    if (static_cast<unsigned>(find_window_w_import) +
            static_cast<unsigned>(reg_open_key_ex_w_import) +
            static_cast<unsigned>(register_device_notification_w_import) +
            static_cast<unsigned>(unregister_device_notification_import) +
            static_cast<unsigned>(direct_input8_create_import) > 1)
        throw std::invalid_argument("fixture imports must be mutually exclusive");
    constexpr size_t file_size = 0x800;
    constexpr size_t pe_offset = 0x80;
    constexpr size_t optional_offset = pe_offset + 24;
    constexpr size_t section_offset = optional_offset + 0xe0;
    constexpr size_t import_section_offset = section_offset + 40;
    std::vector<uint8_t> bytes(file_size, 0);
    bytes[0] = 'M';
    bytes[1] = 'Z';
    write_u32(bytes, 0x3c, pe_offset);
    bytes[pe_offset] = 'P';
    bytes[pe_offset + 1] = 'E';
    write_u16(bytes, pe_offset + 4, 0x014c);
    write_u16(bytes, pe_offset + 6, 2);
    write_u16(bytes, pe_offset + 20, 0xe0);
    write_u16(bytes, optional_offset, 0x010b);
    write_u32(bytes, optional_offset + 16, 0x1020);
    write_u32(bytes, optional_offset + 28, 0x00400000);
    write_u32(bytes, optional_offset + 32, 0x1000);
    write_u32(bytes, optional_offset + 36, 0x200);
    write_u32(bytes, optional_offset + 56, 0x3000);
    write_u32(bytes, optional_offset + 60, 0x200);
    write_u32(bytes, optional_offset + 92, 16);
    write_u32(bytes, optional_offset + 104, 0x2000);
    write_u32(bytes, optional_offset + 108, 60);

    bytes[section_offset] = '.';
    bytes[section_offset + 1] = 't';
    bytes[section_offset + 2] = 'e';
    bytes[section_offset + 3] = 'x';
    bytes[section_offset + 4] = 't';
    write_u32(bytes, section_offset + 8, 0x300);
    write_u32(bytes, section_offset + 12, 0x1000);
    write_u32(bytes, section_offset + 16, 0x200);
    write_u32(bytes, section_offset + 20, 0x200);
    bytes[import_section_offset] = '.';
    bytes[import_section_offset + 1] = 'i';
    bytes[import_section_offset + 2] = 'd';
    bytes[import_section_offset + 3] = 'a';
    bytes[import_section_offset + 4] = 't';
    bytes[import_section_offset + 5] = 'a';
    write_u32(bytes, import_section_offset + 8, 0x400);
    write_u32(bytes, import_section_offset + 12, 0x2000);
    write_u32(bytes, import_section_offset + 16, 0x400);
    write_u32(bytes, import_section_offset + 20, 0x400);

    write_u32(bytes, 0x400, 0x2200);
    write_u32(bytes, 0x40c, 0x2080);
    write_u32(bytes, 0x410, 0x2060);
    write_u32(bytes, 0x600, 0x2090);
    write_u32(bytes, 0x604, 0x20b0);
    write_u32(bytes, 0x608, 0x20d0);
    write_u32(bytes, 0x60c, 0x20f0);
    write_u32(bytes, 0x610, 0x2170);
    write_u32(bytes, 0x614, 0x21a0);
    write_u32(bytes, 0x618, 0x21d0);
    write_u32(bytes, 0x61c, 0x21e0);
    write_u32(bytes, 0x460, 0x2090);
    write_u32(bytes, 0x464, 0x20b0);
    write_u32(bytes, 0x468, 0x20d0);
    write_u32(bytes, 0x46c, 0x20f0);
    write_u32(bytes, 0x470, 0x2170);
    write_u32(bytes, 0x474, 0x21a0);
    write_u32(bytes, 0x478, 0x21d0);
    write_u32(bytes, 0x47c, 0x21e0);
    write_u32(bytes, 0x414, 0x2100);
    write_u32(bytes, 0x420, 0x2140);
    write_u32(bytes, 0x424, 0x2120);
    write_u32(bytes, 0x500, 0x2150);
    write_u32(bytes, 0x520, 0x2150);
    const char* first_import_module =
        reg_open_key_ex_w_import
            ? "ADVAPI32.dll"
            : direct_input8_create_import ? "DINPUT8.dll" : "USER32.dll";
    std::copy_n(first_import_module,
                std::char_traits<char>::length(first_import_module) + 1,
                bytes.begin() + 0x480);
    const char* first_import =
        reg_open_key_ex_w_import
            ? "RegOpenKeyExW"
            : find_window_w_import
                  ? "FindWindowW"
                  : register_device_notification_w_import
                        ? "RegisterDeviceNotificationW"
                  : unregister_device_notification_import
                        ? "UnregisterDeviceNotification"
                        : direct_input8_create_import
                              ? "DirectInput8Create"
                              : "SystemParametersInfoA";
    std::copy_n(first_import,
                std::char_traits<char>::length(first_import) + 1,
                bytes.begin() + 0x492);
    std::copy_n("PeekMessageW", 13, bytes.begin() + 0x4b2);
    std::copy_n("GetDesktopWindow", 17, bytes.begin() + 0x4d2);
    std::copy_n("LoadIconW", 10, bytes.begin() + 0x4f2);
    std::copy_n("GDI32.dll", 10, bytes.begin() + 0x540);
    std::copy_n("GetStockObject", 15, bytes.begin() + 0x552);
    std::copy_n("RegisterClassExW", 17, bytes.begin() + 0x572);
    std::copy_n("CreateWindowExW", 16, bytes.begin() + 0x5a2);
    std::copy_n("ClipCursor", 11, bytes.begin() + 0x5d2);
    std::copy_n("ShowWindow", 11, bytes.begin() + 0x5e2);

    std::ofstream file(path, std::ios::binary | std::ios::trunc);
    require(static_cast<bool>(file),
            "could not create SystemParametersInfoA PE32 fixture");
    file.write(reinterpret_cast<const char*>(bytes.data()),
               static_cast<std::streamsize>(bytes.size()));
    require(static_cast<bool>(file),
            "could not write SystemParametersInfoA PE32 fixture");
}

void write_d3d9_pe32_fixture(const std::string& path) {
    constexpr size_t file_size = 0x800;
    constexpr size_t pe_offset = 0x80;
    constexpr size_t optional_offset = pe_offset + 24;
    constexpr size_t section_offset = optional_offset + 0xe0;
    constexpr size_t import_section_offset = section_offset + 40;
    std::vector<uint8_t> bytes(file_size, 0);
    bytes[0] = 'M';
    bytes[1] = 'Z';
    write_u32(bytes, 0x3c, pe_offset);
    bytes[pe_offset] = 'P';
    bytes[pe_offset + 1] = 'E';
    write_u16(bytes, pe_offset + 4, 0x014c);
    write_u16(bytes, pe_offset + 6, 2);
    write_u16(bytes, pe_offset + 20, 0xe0);
    write_u16(bytes, optional_offset, 0x010b);
    write_u32(bytes, optional_offset + 16, 0x1020);
    write_u32(bytes, optional_offset + 28, 0x00400000);
    write_u32(bytes, optional_offset + 32, 0x1000);
    write_u32(bytes, optional_offset + 36, 0x200);
    write_u32(bytes, optional_offset + 56, 0x3000);
    write_u32(bytes, optional_offset + 60, 0x200);
    write_u32(bytes, optional_offset + 92, 16);
    write_u32(bytes, optional_offset + 104, 0x2000);
    write_u32(bytes, optional_offset + 108, 80);

    bytes[section_offset] = '.';
    bytes[section_offset + 1] = 't';
    bytes[section_offset + 2] = 'e';
    bytes[section_offset + 3] = 'x';
    bytes[section_offset + 4] = 't';
    write_u32(bytes, section_offset + 8, 0x300);
    write_u32(bytes, section_offset + 12, 0x1000);
    write_u32(bytes, section_offset + 16, 0x200);
    write_u32(bytes, section_offset + 20, 0x200);
    bytes[import_section_offset] = '.';
    bytes[import_section_offset + 1] = 'i';
    bytes[import_section_offset + 2] = 'd';
    bytes[import_section_offset + 3] = 'a';
    bytes[import_section_offset + 4] = 't';
    bytes[import_section_offset + 5] = 'a';
    write_u32(bytes, import_section_offset + 8, 0x400);
    write_u32(bytes, import_section_offset + 12, 0x2000);
    write_u32(bytes, import_section_offset + 16, 0x400);
    write_u32(bytes, import_section_offset + 20, 0x400);

    write_u32(bytes, 0x400, 0x2200);
    write_u32(bytes, 0x40c, 0x2080);
    write_u32(bytes, 0x410, 0x2060);
    write_u32(bytes, 0x414, 0x2100);
    write_u32(bytes, 0x420, 0x2120);
    write_u32(bytes, 0x424, 0x2180);
    for (size_t index = 0; index < 3; ++index) {
        const uint32_t name_rva =
            static_cast<uint32_t>(0x2090 + index * 0x20);
        write_u32(bytes, 0x600 + index * 4, name_rva);
        write_u32(bytes, 0x460 + index * 4, name_rva);
    }
    std::copy_n("d3d9.dll", 9, bytes.begin() + 0x480);
    const std::array<const char*, 3> import_names = {
        "Direct3DCreate9", "D3DPERF_EndEvent", "D3DPERF_BeginEvent"};
    for (size_t index = 0; index < import_names.size(); ++index) {
        const size_t offset = 0x490 + index * 0x20;
        std::copy_n(import_names[index],
                    std::char_traits<char>::length(import_names[index]) + 1,
                    bytes.begin() + offset + 2);
    }
    write_u32(bytes, 0x500, 0x2130);
    write_u32(bytes, 0x504, 0x2160);
    write_u32(bytes, 0x580, 0x2130);
    write_u32(bytes, 0x584, 0x2160);
    std::copy_n("SHELL32.dll", 12, bytes.begin() + 0x520);
    const char folder_path_name[] = "SHGetFolderPathA";
    std::copy_n(folder_path_name, sizeof(folder_path_name),
                bytes.begin() + 0x532);
    const char create_directory_name[] = "SHCreateDirectoryExA";
    std::copy_n(create_directory_name, sizeof(create_directory_name),
                bytes.begin() + 0x562);
    write_u32(bytes, 0x428, 0x2240);
    write_u32(bytes, 0x434, 0x2280);
    write_u32(bytes, 0x438, 0x2260);
    write_u32(bytes, 0x640, 0x22a0);
    write_u32(bytes, 0x644, 0x2300);
    write_u32(bytes, 0x648, 0x2360);
    write_u32(bytes, 0x64c, 0x23a0);
    write_u32(bytes, 0x650, 0x23c6);
    write_u32(bytes, 0x654, 0x2330);
    write_u32(bytes, 0x660, 0x22a0);
    write_u32(bytes, 0x664, 0x2300);
    write_u32(bytes, 0x668, 0x2360);
    write_u32(bytes, 0x66c, 0x23a0);
    write_u32(bytes, 0x670, 0x23c6);
    write_u32(bytes, 0x674, 0x2330);
    std::copy_n("d3dx9_41.dll", 13, bytes.begin() + 0x680);
    const char create_effect_name[] = "D3DXCreateEffect";
    std::copy_n(create_effect_name, sizeof(create_effect_name),
                bytes.begin() + 0x6a2);
    const char effect_compiler_name[] =
        "D3DXCreateEffectCompilerFromFileA";
    std::copy_n(effect_compiler_name, sizeof(effect_compiler_name),
                bytes.begin() + 0x702);
    const char create_line_name[] = "D3DXCreateLine";
    std::copy_n(create_line_name, sizeof(create_line_name),
                bytes.begin() + 0x762);
    const char create_buffer_name[] = "D3DXCreateBuffer";
    std::copy_n(create_buffer_name, sizeof(create_buffer_name),
                bytes.begin() + 0x732);
    const char image_info_name[] = "D3DXGetImageInfoFromFileInMemory";
    std::copy_n(image_info_name, sizeof(image_info_name),
                bytes.begin() + 0x7a2);
    const char create_texture_from_memory_name[] =
        "D3DXCreateTextureFromFileInMemoryEx";
    std::copy_n(create_texture_from_memory_name,
                sizeof(create_texture_from_memory_name),
                bytes.begin() + 0x7c8);

    std::ofstream file(path, std::ios::binary | std::ios::trunc);
    require(static_cast<bool>(file), "could not create D3D9 PE32 fixture");
    file.write(reinterpret_cast<const char*>(bytes.data()),
               static_cast<std::streamsize>(bytes.size()));
    require(static_cast<bool>(file), "could not write D3D9 PE32 fixture");
}

std::vector<uint8_t> make_d3dx9_shader_effect(bool include_pixel_shader = false) {
    std::vector<uint8_t> bytes(8, 0);
    const auto append_u32 = [&bytes](uint32_t value) {
        const size_t offset = bytes.size();
        bytes.resize(offset + 4);
        write_u32(bytes, offset, value);
    };
    const auto patch_u32 = [&bytes](size_t offset, uint32_t value) {
        write_u32(bytes, offset, value);
    };
    const auto append_name = [&bytes, &append_u32](const char* name) {
        const size_t length = std::char_traits<char>::length(name) + 1;
        const uint32_t offset = static_cast<uint32_t>(bytes.size());
        append_u32(static_cast<uint32_t>(length));
        bytes.insert(bytes.end(), name, name + length);
        return offset;
    };

    const uint32_t table_offset = static_cast<uint32_t>(bytes.size());
    append_u32(include_pixel_shader ? 2 : 0);  // Parameters.
    append_u32(1);  // Techniques.
    append_u32(include_pixel_shader ? 3 : 1);  // Shader variables.
    append_u32(include_pixel_shader ? 3 : 1);  // Objects.
    size_t parameter_type_offset_field = 0;
    size_t parameter_value_offset_field = 0;
    size_t texture_parameter_type_offset_field = 0;
    size_t texture_parameter_value_offset_field = 0;
    if (include_pixel_shader) {
        parameter_type_offset_field = bytes.size();
        append_u32(0);
        parameter_value_offset_field = bytes.size();
        append_u32(0);
        append_u32(0);  // Parameter flags.
        append_u32(0);  // Parameter annotations.
        texture_parameter_type_offset_field = bytes.size();
        append_u32(0);
        texture_parameter_value_offset_field = bytes.size();
        append_u32(0);
        append_u32(0);  // Parameter flags.
        append_u32(0);  // Parameter annotations.
    }
    const size_t technique_name_field = bytes.size();
    append_u32(0);
    append_u32(include_pixel_shader ? 3 : 0);  // Technique annotations.
    append_u32(1);  // Passes.
    size_t technique_annotation_type_field = 0;
    size_t technique_annotation_value_field = 0;
    size_t integer_annotation_type_field = 0;
    size_t integer_annotation_value_field = 0;
    size_t string_annotation_type_field = 0;
    size_t string_annotation_value_field = 0;
    if (include_pixel_shader) {
        technique_annotation_type_field = bytes.size();
        append_u32(0);
        technique_annotation_value_field = bytes.size();
        append_u32(0);
        integer_annotation_type_field = bytes.size();
        append_u32(0);
        integer_annotation_value_field = bytes.size();
        append_u32(0);
        string_annotation_type_field = bytes.size();
        append_u32(0);
        string_annotation_value_field = bytes.size();
        append_u32(0);
    }
    const size_t pass_name_field = bytes.size();
    append_u32(0);
    append_u32(0);  // Pass annotations.
    append_u32(include_pixel_shader ? 2 : 1);  // States.
    append_u32(146);  // Vertex-shader state.
    append_u32(0);    // State index.
    const size_t vertex_type_offset_field = bytes.size();
    append_u32(0);
    const size_t vertex_value_offset_field = bytes.size();
    append_u32(0);
    size_t pixel_type_offset_field = 0;
    size_t pixel_value_offset_field = 0;
    if (include_pixel_shader) {
        append_u32(147);  // Pixel-shader state.
        append_u32(0);    // State index.
        pixel_type_offset_field = bytes.size();
        append_u32(0);
        pixel_value_offset_field = bytes.size();
        append_u32(0);
    }
    append_u32(include_pixel_shader ? 1 : 0);  // String objects.
    append_u32(include_pixel_shader ? 2 : 1);  // Resources.
    if (include_pixel_shader) {
        append_u32(2);  // String annotation object id.
        constexpr char test_string[] = "road";
        append_u32(sizeof(test_string));
        bytes.insert(bytes.end(), test_string, test_string + sizeof(test_string));
        while ((bytes.size() & 3) != 0) bytes.push_back(0);
    }
    append_u32(0);  // Technique index.
    append_u32(0);  // Pass index.
    append_u32(UINT32_MAX);
    append_u32(0);  // State index.
    append_u32(0);  // Constant resource.
    const std::array<uint8_t, 8> vertex_shader = {
        0, 3, 0xfe, 0xff, 0xff, 0xff, 0, 0};
    append_u32(static_cast<uint32_t>(vertex_shader.size()));
    bytes.insert(bytes.end(), vertex_shader.begin(), vertex_shader.end());
    if (include_pixel_shader) {
        append_u32(0);  // Technique index.
        append_u32(0);  // Pass index.
        append_u32(UINT32_MAX);
        append_u32(1);  // State index.
        append_u32(0);  // Constant resource.
        const std::array<uint8_t, 8> pixel_shader = {
            0, 3, 0xff, 0xff, 0xff, 0xff, 0, 0};
        append_u32(static_cast<uint32_t>(pixel_shader.size()));
        bytes.insert(bytes.end(), pixel_shader.begin(), pixel_shader.end());
    }

    const uint32_t vertex_type_offset = static_cast<uint32_t>(bytes.size());
    append_u32(16);  // D3DXPT_VERTEXSHADER.
    append_u32(4);   // D3DXPC_OBJECT.
    const size_t vertex_type_name_field = bytes.size();
    append_u32(0);
    const size_t vertex_semantic_field = bytes.size();
    append_u32(0);
    append_u32(0);  // Array elements.
    const uint32_t vertex_value_offset = static_cast<uint32_t>(bytes.size());
    append_u32(0);  // Object id.

    uint32_t pixel_type_offset = 0;
    size_t pixel_type_name_field = 0;
    size_t pixel_semantic_field = 0;
    uint32_t pixel_value_offset = 0;
    if (include_pixel_shader) {
        pixel_type_offset = static_cast<uint32_t>(bytes.size());
        append_u32(15);  // D3DXPT_PIXELSHADER.
        append_u32(4);   // D3DXPC_OBJECT.
        pixel_type_name_field = bytes.size();
        append_u32(0);
        pixel_semantic_field = bytes.size();
        append_u32(0);
        append_u32(0);  // Array elements.
        pixel_value_offset = static_cast<uint32_t>(bytes.size());
        append_u32(1);  // Object id.
    }

    uint32_t annotation_type_offset = 0;
    size_t annotation_type_name_field = 0;
    size_t annotation_semantic_field = 0;
    uint32_t annotation_value_offset = 0;
    uint32_t integer_annotation_type_offset = 0;
    size_t integer_annotation_type_name_field = 0;
    size_t integer_annotation_semantic_field = 0;
    uint32_t integer_annotation_value_offset = 0;
    uint32_t string_annotation_type_offset = 0;
    size_t string_annotation_type_name_field = 0;
    size_t string_annotation_semantic_field = 0;
    uint32_t string_annotation_value_offset = 0;
    if (include_pixel_shader) {
        annotation_type_offset = static_cast<uint32_t>(bytes.size());
        append_u32(1);  // D3DXPT_BOOL.
        append_u32(0);  // D3DXPC_SCALAR.
        annotation_type_name_field = bytes.size();
        append_u32(0);
        annotation_semantic_field = bytes.size();
        append_u32(0);
        append_u32(0);  // Array elements.
        append_u32(1);  // Scalar rows.
        append_u32(1);  // Scalar columns.
        annotation_value_offset = static_cast<uint32_t>(bytes.size());
        append_u32(0);  // supportsSpecialisedLighting is false.

        integer_annotation_type_offset = static_cast<uint32_t>(bytes.size());
        append_u32(2);  // D3DXPT_INT.
        append_u32(0);  // D3DXPC_SCALAR.
        integer_annotation_type_name_field = bytes.size();
        append_u32(0);
        integer_annotation_semantic_field = bytes.size();
        append_u32(0);
        append_u32(0);  // Array elements.
        append_u32(1);  // Scalar rows.
        append_u32(1);  // Scalar columns.
        integer_annotation_value_offset = static_cast<uint32_t>(bytes.size());
        append_u32(1);  // testIntegerAnnotation is true.

        string_annotation_type_offset = static_cast<uint32_t>(bytes.size());
        append_u32(4);  // D3DXPT_STRING.
        append_u32(4);  // D3DXPC_OBJECT.
        string_annotation_type_name_field = bytes.size();
        append_u32(0);
        string_annotation_semantic_field = bytes.size();
        append_u32(0);
        append_u32(0);  // Array elements.
        string_annotation_value_offset =
            static_cast<uint32_t>(bytes.size());
        append_u32(2);  // String object id.
    }

    uint32_t parameter_type_offset = 0;
    size_t parameter_type_name_field = 0;
    size_t parameter_semantic_field = 0;
    uint32_t parameter_value_offset = 0;
    if (include_pixel_shader) {
        parameter_type_offset = static_cast<uint32_t>(bytes.size());
        append_u32(3);  // D3DXPT_FLOAT.
        append_u32(0);  // D3DXPC_SCALAR.
        parameter_type_name_field = bytes.size();
        append_u32(0);
        parameter_semantic_field = bytes.size();
        append_u32(0);
        append_u32(0);  // Array elements.
        append_u32(1);  // Scalar rows.
        append_u32(1);  // Scalar columns.
        parameter_value_offset = static_cast<uint32_t>(bytes.size());
        append_u32(0x3f800000);  // 1.0f.
    }

    uint32_t texture_parameter_type_offset = 0;
    size_t texture_parameter_type_name_field = 0;
    size_t texture_parameter_semantic_field = 0;
    uint32_t texture_parameter_value_offset = 0;
    if (include_pixel_shader) {
        texture_parameter_type_offset = static_cast<uint32_t>(bytes.size());
        append_u32(5);  // D3DXPT_TEXTURE.
        append_u32(4);  // D3DXPC_OBJECT.
        texture_parameter_type_name_field = bytes.size();
        append_u32(0);
        texture_parameter_semantic_field = bytes.size();
        append_u32(0);
        append_u32(0);  // Array elements.
        texture_parameter_value_offset =
            static_cast<uint32_t>(bytes.size());
        append_u32(0);  // Initial object id.
    }

    const uint32_t technique_name = append_name("ShadowGen");
    const uint32_t pass_name = append_name("Pass0");
    const uint32_t vertex_type_name = append_name("VertexShader");
    const uint32_t pixel_type_name =
        include_pixel_shader ? append_name("PixelShader") : 0;
    const uint32_t empty_name = append_name("");
    const uint32_t annotation_type_name =
        include_pixel_shader ? append_name("supportsSpecialisedLighting") : 0;
    const uint32_t integer_annotation_type_name =
        include_pixel_shader ? append_name("testIntegerAnnotation") : 0;
    const uint32_t string_annotation_type_name =
        include_pixel_shader ? append_name("testStringAnnotation") : 0;
    const uint32_t parameter_type_name =
        include_pixel_shader ? append_name("ShadowParameter") : 0;
    const uint32_t parameter_semantic_name =
        include_pixel_shader ? append_name("World") : 0;
    const uint32_t texture_parameter_type_name =
        include_pixel_shader ? append_name("TextureParameter") : 0;
    patch_u32(0, 0xfeff0901);
    patch_u32(4, table_offset - 8);
    patch_u32(technique_name_field, technique_name - 8);
    if (include_pixel_shader) {
        patch_u32(parameter_type_offset_field, parameter_type_offset - 8);
        patch_u32(parameter_value_offset_field, parameter_value_offset - 8);
        patch_u32(parameter_type_name_field, parameter_type_name - 8);
        patch_u32(parameter_semantic_field, parameter_semantic_name - 8);
        patch_u32(texture_parameter_type_offset_field,
                  texture_parameter_type_offset - 8);
        patch_u32(texture_parameter_value_offset_field,
                  texture_parameter_value_offset - 8);
        patch_u32(texture_parameter_type_name_field,
                  texture_parameter_type_name - 8);
        patch_u32(texture_parameter_semantic_field, empty_name - 8);
        patch_u32(technique_annotation_type_field,
                  annotation_type_offset - 8);
        patch_u32(technique_annotation_value_field,
                  annotation_value_offset - 8);
        patch_u32(integer_annotation_type_field,
                  integer_annotation_type_offset - 8);
        patch_u32(integer_annotation_value_field,
                  integer_annotation_value_offset - 8);
        patch_u32(string_annotation_type_field,
                  string_annotation_type_offset - 8);
        patch_u32(string_annotation_value_field,
                  string_annotation_value_offset - 8);
        patch_u32(annotation_type_name_field, annotation_type_name - 8);
        patch_u32(annotation_semantic_field, empty_name - 8);
        patch_u32(integer_annotation_type_name_field,
                  integer_annotation_type_name - 8);
        patch_u32(integer_annotation_semantic_field, empty_name - 8);
        patch_u32(string_annotation_type_name_field,
                  string_annotation_type_name - 8);
        patch_u32(string_annotation_semantic_field, empty_name - 8);
    }
    patch_u32(pass_name_field, pass_name - 8);
    patch_u32(vertex_type_offset_field, vertex_type_offset - 8);
    patch_u32(vertex_value_offset_field, vertex_value_offset - 8);
    patch_u32(vertex_type_name_field, vertex_type_name - 8);
    patch_u32(vertex_semantic_field, empty_name - 8);
    if (include_pixel_shader) {
        patch_u32(pixel_type_offset_field, pixel_type_offset - 8);
        patch_u32(pixel_value_offset_field, pixel_value_offset - 8);
        patch_u32(pixel_type_name_field, pixel_type_name - 8);
        patch_u32(pixel_semantic_field, empty_name - 8);
    }
    return bytes;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 11) {
        std::cerr << "usage: shift_runtime_recompiled_pcode_module_check "
                     "MODULE SUPPLEMENT OVERRIDE PE32_FIXTURE_OUT "
                     "RAISE_EXCEPTION_PE32_OUT TIME_GET_TIME_PE32_OUT "
                     "SYSTEM_PARAMETERS_INFO_PE32_OUT D3D9_PE32_OUT "
                     "FRONTIER_MODULE BLOCK_TEST_MODULE\n";
        return 2;
    }
    try {
        const std::string read_file_ex_fixture_path =
            (std::filesystem::temp_directory_path() /
             ("shift-runtime-readfileex-" + std::to_string(getpid()) +
              ".exe"))
                .string();
        const std::string create_directory_fixture_path =
            (std::filesystem::temp_directory_path() /
             ("shift-runtime-createdirectory-" + std::to_string(getpid()) +
              ".exe"))
                .string();
        const std::string write_file_fixture_path =
            (std::filesystem::temp_directory_path() /
             ("shift-runtime-writefile-" + std::to_string(getpid()) +
              ".exe"))
                .string();
        const std::string set_file_pointer_fixture_path =
            (std::filesystem::temp_directory_path() /
             ("shift-runtime-setfilepointer-" + std::to_string(getpid()) +
              ".exe"))
                .string();
        const std::string get_version_ex_w_fixture_path =
            (std::filesystem::temp_directory_path() /
             ("shift-runtime-getversionexw-" + std::to_string(getpid()) +
              ".exe"))
                .string();
        const std::string find_window_w_fixture_path =
            (std::filesystem::temp_directory_path() /
             ("shift-runtime-findwindoww-" + std::to_string(getpid()) +
              ".exe"))
                .string();
        const std::string reg_open_key_ex_w_fixture_path =
            (std::filesystem::temp_directory_path() /
             ("shift-runtime-regopenkeyexw-" + std::to_string(getpid()) +
              ".exe"))
                .string();
        const std::string register_device_notification_w_fixture_path =
            (std::filesystem::temp_directory_path() /
             ("shift-runtime-registerdevicenotificationw-" +
              std::to_string(getpid()) + ".exe"))
                .string();
        const std::string unregister_device_notification_fixture_path =
            (std::filesystem::temp_directory_path() /
             ("shift-runtime-unregisterdevicenotification-" +
              std::to_string(getpid()) + ".exe"))
                .string();
        const std::string direct_input8_create_fixture_path =
            (std::filesystem::temp_directory_path() /
             ("shift-runtime-directinput8create-" + std::to_string(getpid()) +
              ".exe"))
                .string();
        const std::string wsa_startup_fixture_path =
            (std::filesystem::temp_directory_path() /
             ("shift-runtime-wsastartup-" + std::to_string(getpid()) +
              ".exe"))
                .string();
        const std::string stack_walk64_fixture_path =
            (std::filesystem::temp_directory_path() /
             ("shift-runtime-stackwalk64-" + std::to_string(getpid()) +
              ".exe"))
                .string();
        write_pe32_fixture(argv[4]);
        write_pe32_fixture(argv[5], true);
        write_pe32_fixture(argv[6], false, true);
        write_pe32_fixture(read_file_ex_fixture_path, false, false, false,
                           true);
        write_pe32_fixture(create_directory_fixture_path, false, false,
                           false, false, true);
        write_pe32_fixture(write_file_fixture_path, false, false, false,
                           false, false, true);
        write_pe32_fixture(get_version_ex_w_fixture_path, false, false, false,
                           false, false, false, true);
        write_pe32_fixture(set_file_pointer_fixture_path, false, false, false,
                           false, false, false, false, true);
        write_pe32_fixture(stack_walk64_fixture_path, false, false, false,
                           false, false, false, false, false, true);
        write_system_parameters_info_pe32_fixture(argv[7]);
        write_system_parameters_info_pe32_fixture(find_window_w_fixture_path,
                                                   true);
        write_system_parameters_info_pe32_fixture(
            reg_open_key_ex_w_fixture_path, false, true);
        write_system_parameters_info_pe32_fixture(
            register_device_notification_w_fixture_path, false, false, true);
        write_system_parameters_info_pe32_fixture(
            unregister_device_notification_fixture_path, false, false, false,
            true);
        write_system_parameters_info_pe32_fixture(
            direct_input8_create_fixture_path, false, false, false, false,
            true);
        write_wsa_startup_pe32_fixture(wsa_startup_fixture_path);
        write_d3d9_pe32_fixture(argv[8]);
        shift::runtime::RecompiledPcodeModule duplicate_module(argv[1]);
        require(duplicate_module.load_supplemental_module(argv[2]),
                "duplicate-check P-code supplement could not be loaded: " +
                    duplicate_module.last_error());
        require(duplicate_module.call(0x00685700) != 0 &&
                    duplicate_module.last_error().find(
                        "duplicate P-code export rvi_00685700") !=
                        std::string::npos,
                "duplicate P-code exports were not rejected without an override");

        require(setenv("SHIFT_TRACE_GUEST_PROVENANCE", "0x00020000", 1) == 0,
                "could not enable guest write provenance fixture");
        {
            shift::runtime::RecompiledPcodeModule provenance_module(argv[1]);
            require(provenance_module.call(0x00401000) == 0,
                    "guest write provenance setup call failed: " +
                        provenance_module.last_error());
            require(provenance_module.call(0x00402000) != 0,
                    "guest write provenance failure fixture unexpectedly passed");
            const std::string provenance_error = provenance_module.last_error();
            require(provenance_error.find("guest write provenance=[") !=
                        std::string::npos &&
                    provenance_error.find("0x00020000") != std::string::npos &&
                    provenance_error.find("last_writer=0x00685700") !=
                        std::string::npos &&
                    provenance_error.find("word_value=0x00aa99d0") !=
                        std::string::npos,
                    "guest write provenance did not identify the last writer: " +
                        provenance_error);
        }
        require(unsetenv("SHIFT_TRACE_GUEST_PROVENANCE") == 0,
                "could not disable guest write provenance fixture");

        require(setenv("SHIFT_TRACE_GUEST_CALLER", "0x00403100", 1) == 0,
                "could not enable guest caller trace fixture");
        require(setenv("SHIFT_TRACE_GUEST_CALLER_SLOTS",
                       "0x10,0x20,0xffffffff", 1) == 0,
                "could not configure guest caller slot trace fixture");
        require(setenv("SHIFT_TRACE_GUEST_PROVENANCE", "0x00023010", 1) == 0,
                "could not enable caller slot writer provenance fixture");
        {
            shift::runtime::RecompiledPcodeModule call_trace_module(argv[1]);
            constexpr uint32_t receiver = 0x00023000;
            write_guest_u32(call_trace_module, "register", 4, receiver);
            write_guest_u32(call_trace_module, "register", 0x1c,
                            0x13579bdf);
            write_guest_u32(call_trace_module, "register", 0x18,
                            0x2468ace0);
            write_guest_u32(call_trace_module, "ram", receiver + 0x10,
                            0x12345678);
            write_guest_u32(call_trace_module, "ram", receiver + 0x20,
                            0x90abcdef);
            require(call_trace_module.call(0x00403100) == 0,
                    "guest caller trace fixture call failed: " +
                        call_trace_module.last_error());
            const auto snapshot = call_trace_module.guest_scheduler_snapshot();
            require(snapshot.guest_call_trace.size() == 1,
                    "guest caller trace did not capture its nested call");
            const auto& trace_event = snapshot.guest_call_trace.front();
            require(snapshot.guest_call_trace_enabled &&
                        !snapshot.guest_call_trace_truncated &&
                        snapshot.guest_call_trace_caller == 0x00403100 &&
                        snapshot.guest_call_trace_slot_offsets ==
                            std::vector<uint32_t>{0x10, 0x20, 0xffffffff} &&
                        trace_event.caller == 0x00403100 &&
                        trace_event.function == 0x00685700 &&
                        trace_event.ecx_entry == 0x00023000 &&
                        trace_event.caller_ecx == receiver &&
                        trace_event.eax_entry == 0x78563412 &&
                        trace_event.completed &&
                        trace_event.has_eax_return &&
                        trace_event.eax_return == 0x78563412 &&
                        trace_event.edi_entry == 0x13579bdf &&
                        trace_event.has_edi_return &&
                        trace_event.edi_return == 0x13579bdf &&
                        trace_event.esi_entry == 0x2468ace0 &&
                        trace_event.has_esi_return &&
                        trace_event.esi_return == 0x2468ace0 &&
                        trace_event.has_ebp_return &&
                        trace_event.has_esp_return &&
                        trace_event.caller_slots.size() == 3 &&
                        trace_event.caller_slots[0].offset == 0x10 &&
                        trace_event.caller_slots[0].has_value &&
                        trace_event.caller_slots[0].value == 0x12345678 &&
                        trace_event.caller_slots[0].has_last_writer &&
                        trace_event.caller_slots[0].last_writer.function ==
                            0x00403100 &&
                        trace_event.caller_slots[0].last_writer.write_address ==
                            0x00023010 &&
                        trace_event.caller_slots[0].last_writer.write_size == 4 &&
                        trace_event.caller_slots[0].last_writer.word_value ==
                            0x12345678 &&
                        trace_event.caller_slots[1].offset == 0x20 &&
                        trace_event.caller_slots[1].has_value &&
                        trace_event.caller_slots[1].value == 0x90abcdef &&
                        trace_event.caller_slots[2].offset == 0xffffffff &&
                        !trace_event.caller_slots[2].has_value,
                    "guest caller trace did not capture its nested P-code call");
        }
        require(unsetenv("SHIFT_TRACE_GUEST_CALLER_SLOTS") == 0,
                "could not disable guest caller slot trace fixture");
        require(unsetenv("SHIFT_TRACE_GUEST_PROVENANCE") == 0,
                "could not disable caller slot writer provenance fixture");
        require(unsetenv("SHIFT_TRACE_GUEST_CALLER") == 0,
                "could not disable guest caller trace fixture");

        require(setenv("SHIFT_TRACE_GUEST_CALL_TARGETS", "0x00685700", 1) ==
                    0,
                "could not enable guest call target trace fixture");
        require(setenv("SHIFT_TRACE_GUEST_CALL_TARGET_SLOTS",
                       "0x10,0x20,0xffffffff", 1) == 0,
                "could not configure guest call target slot trace fixture");
        require(setenv("SHIFT_TRACE_GUEST_PROVENANCE", "0x00023010", 1) ==
                    0,
                "could not enable target slot writer provenance fixture");
        require(setenv("SHIFT_TRACE_GUEST_CALL_LIVE_LOG", "1", 1) == 0,
                "could not enable live guest call trace fixture");
        std::string live_trace;
        {
            StderrCapture capture;
            shift::runtime::RecompiledPcodeModule target_trace_module(argv[1]);
            constexpr uint32_t receiver = 0x00023000;
            write_guest_u32(target_trace_module, "ram", receiver + 0x20,
                            0x50607080);
            require(target_trace_module.call(0x00403100) == 0,
                    "guest call target trace fixture call failed: " +
                        target_trace_module.last_error());
            const auto snapshot =
                target_trace_module.guest_scheduler_snapshot();
            require(snapshot.guest_call_trace_enabled &&
                        snapshot.guest_call_trace_caller == 0 &&
                        snapshot.guest_call_trace_targets ==
                            std::vector<uint32_t>{0x00685700} &&
                        snapshot.guest_call_trace_target_slot_offsets ==
                            std::vector<uint32_t>{0x10, 0x20, 0xffffffff} &&
                        snapshot.guest_call_trace.size() == 1 &&
                        snapshot.guest_call_trace.front().caller ==
                            0x00403100 &&
                        snapshot.guest_call_trace.front().function ==
                            0x00685700 &&
                        snapshot.guest_call_trace.front().target_resolved &&
                        snapshot.guest_call_trace.front().ecx_entry ==
                            receiver &&
                        snapshot.guest_call_trace.front().completed &&
                        snapshot.guest_call_trace.front().has_eax_return &&
                        snapshot.guest_call_trace.front().eax_return ==
                            0x78563412 &&
                        snapshot.guest_call_trace.front().target_slots.size() ==
                            3 &&
                        snapshot.guest_call_trace.front().target_slots[0]
                                .offset == 0x10 &&
                        snapshot.guest_call_trace.front().target_slots[0]
                                .has_value &&
                        snapshot.guest_call_trace.front().target_slots[0]
                                .value == 0x12345678 &&
                        snapshot.guest_call_trace.front().target_slots[0]
                                .has_last_writer &&
                        snapshot.guest_call_trace.front().target_slots[0]
                                .last_writer.function == 0x00403100 &&
                        snapshot.guest_call_trace.front().target_slots[0]
                                .last_writer.write_address == 0x00023010 &&
                        snapshot.guest_call_trace.front().target_slots[1]
                                .offset == 0x20 &&
                        snapshot.guest_call_trace.front().target_slots[1]
                                .has_value &&
                        snapshot.guest_call_trace.front().target_slots[1]
                                .value == 0x50607080 &&
                        snapshot.guest_call_trace.front().target_slots[2]
                                .offset == 0xffffffff &&
                        !snapshot.guest_call_trace.front().target_slots[2]
                             .has_value,
                    "guest call target trace did not capture a call from an "
                    "unselected caller and its entry receiver slots");
            live_trace = capture.text();
        }
        require(live_trace.find(
                    "shift_guest_call_trace_entry:") !=
                    std::string::npos &&
                    live_trace.find("caller=0x00403100 target=0x00685700") !=
                        std::string::npos &&
                    live_trace.find("shift_guest_call_trace_return:") !=
                    std::string::npos &&
                    live_trace.find("eax=0x78563412") != std::string::npos &&
                    live_trace.find("writer=0x00403100") != std::string::npos,
                "live guest call trace did not persist entry and return events: " +
                    live_trace);
        require(unsetenv("SHIFT_TRACE_GUEST_CALL_LIVE_LOG") == 0,
                "could not disable live guest call trace fixture");
        require(setenv("SHIFT_TRACE_GUEST_CALL_STACK_SLOTS",
                       "0x4,0x8,0xffffffff", 1) == 0,
                "could not configure guest call stack slot trace fixture");
        {
            shift::runtime::RecompiledPcodeModule stack_trace_module(argv[1]);
            require(stack_trace_module.call(0x00406100) == 0,
                    "guest call stack trace fixture call failed: " +
                        stack_trace_module.last_error());
            const auto snapshot =
                stack_trace_module.guest_scheduler_snapshot();
            require(snapshot.guest_call_trace_stack_slot_offsets ==
                        std::vector<uint32_t>{0x4, 0x8, 0xffffffff} &&
                        snapshot.guest_call_trace.size() == 1 &&
                        snapshot.guest_call_trace.front().caller ==
                            0x00406100 &&
                        snapshot.guest_call_trace.front().stack_slots.size() ==
                            3 &&
                        snapshot.guest_call_trace.front().stack_slots[0]
                                .offset == 0x4 &&
                        snapshot.guest_call_trace.front().stack_slots[0]
                                .has_value &&
                        snapshot.guest_call_trace.front().stack_slots[0]
                                .value == 0x11223344 &&
                        snapshot.guest_call_trace.front().stack_slots[1]
                                .offset == 0x8 &&
                        snapshot.guest_call_trace.front().stack_slots[1]
                                .has_value &&
                        snapshot.guest_call_trace.front().stack_slots[1]
                                .value == 0x55667788 &&
                        snapshot.guest_call_trace.front().stack_slots[2]
                                .offset == 0xffffffff &&
                        !snapshot.guest_call_trace.front().stack_slots[2]
                             .has_value,
                    "guest call trace did not capture target stack arguments");
        }
        require(unsetenv("SHIFT_TRACE_GUEST_CALL_STACK_SLOTS") == 0,
                "could not disable guest call stack slot trace fixture");
        require(unsetenv("SHIFT_TRACE_GUEST_PROVENANCE") == 0,
                "could not disable target slot writer provenance fixture");
        require(unsetenv("SHIFT_TRACE_GUEST_CALL_TARGET_SLOTS") == 0,
                "could not disable guest call target slot trace fixture");
        require(unsetenv("SHIFT_TRACE_GUEST_CALL_TARGETS") == 0,
                "could not disable guest call target trace fixture");

        require(setenv("SHIFT_TRACE_GUEST_CALL_IMPORTS",
                       "KERNEL32.dll!Sleep", 1) == 0,
                "could not enable guest import trace fixture");
        require(setenv("SHIFT_TRACE_GUEST_CALL_STACK_SLOTS", "0x4", 1) == 0,
                "could not configure guest import stack trace fixture");
        require(setenv("SHIFT_TRACE_GUEST_CALL_TARGET_SLOTS", "0x0", 1) == 0,
                "could not configure guest import target trace fixture");
        require(setenv("SHIFT_TRACE_GUEST_CALL_LIVE_LOG", "1", 1) == 0,
                "could not enable guest import live trace fixture");
        std::string import_live_trace;
        {
            StderrCapture capture;
            shift::runtime::RecompiledPcodeModule import_trace_module(argv[1]);
            (void)import_trace_module.load_pe32_image(argv[4]);
            require(import_trace_module.call(0x00405000) == 0,
                    "guest import trace fixture call failed: " +
                        import_trace_module.last_error());
            const auto snapshot =
                import_trace_module.guest_scheduler_snapshot();
            require(snapshot.guest_call_trace_enabled &&
                        snapshot.guest_call_trace_imports ==
                            std::vector<std::string>{"KERNEL32.dll!Sleep"} &&
                        snapshot.guest_call_trace.size() == 1 &&
                        snapshot.guest_call_trace.front().caller ==
                            0x00405000 &&
                        snapshot.guest_call_trace.front().is_import &&
                        snapshot.guest_call_trace.front().import_name ==
                            "KERNEL32.dll!Sleep" &&
                        snapshot.guest_call_trace.front().has_return_address &&
                        snapshot.guest_call_trace.front().return_address ==
                            0x00405005 &&
                        snapshot.guest_call_trace.front().completed &&
                        snapshot.guest_call_trace.front()
                                .completion_dispatch_count >=
                            snapshot.guest_call_trace.front().dispatch_count &&
                        snapshot.guest_call_trace.front().has_eax_return &&
                        snapshot.guest_call_trace.front().eax_return == 0 &&
                        snapshot.guest_call_trace.front().target_slots.empty() &&
                        snapshot.guest_call_trace.front().stack_slots.size() ==
                            1 &&
                        snapshot.guest_call_trace.front().stack_slots.front()
                                .offset == 0x4 &&
                        snapshot.guest_call_trace.front().stack_slots.front()
                                .has_value &&
                        snapshot.guest_call_trace.front().stack_slots.front()
                                .value == 1,
                    "guest call trace did not capture selected import and its stack argument");
            import_live_trace = capture.text();
        }
        require(import_live_trace.find(
                    "import=KERNEL32.dll!Sleep") != std::string::npos,
                "live guest call trace omitted the imported API name: " +
                    import_live_trace);
        require(unsetenv("SHIFT_TRACE_GUEST_CALL_LIVE_LOG") == 0,
                "could not disable guest import live trace fixture");
        require(unsetenv("SHIFT_TRACE_GUEST_CALL_STACK_SLOTS") == 0,
                "could not disable guest import stack trace fixture");
        require(unsetenv("SHIFT_TRACE_GUEST_CALL_TARGET_SLOTS") == 0,
                "could not disable guest import target trace fixture");
        require(unsetenv("SHIFT_TRACE_GUEST_CALL_IMPORTS") == 0,
                "could not disable guest import trace fixture");

        require(setenv("SHIFT_TRACE_GUEST_CALL_TARGETS", "0x00685700", 1) ==
                    0,
                "could not enable guest string argument trace fixture");
        require(setenv("SHIFT_TRACE_GUEST_CALL_STRING_SLOTS", "0x4", 1) == 0,
                "could not configure guest string argument trace fixture");
        require(setenv("SHIFT_TRACE_GUEST_CALL_LIVE_LOG", "1", 1) == 0,
                "could not enable guest string live trace fixture");
        {
            StderrCapture capture;
            shift::runtime::RecompiledPcodeModule string_trace_module(argv[1]);
            constexpr uint32_t string_address = 0x11223344;
            const std::string expected_string = "C:\\cars\\engine.bin";
            const std::string terminated_string = expected_string + '\0';
            write_guest_bytes(
                string_trace_module, string_address,
                reinterpret_cast<const uint8_t*>(terminated_string.data()),
                terminated_string.size());
            require(string_trace_module.call(0x00406100) == 0,
                    "guest string argument trace fixture call failed: " +
                        string_trace_module.last_error());
            const auto snapshot =
                string_trace_module.guest_scheduler_snapshot();
            require(snapshot.guest_call_trace_string_slot_offsets ==
                        std::vector<uint32_t>{0x4} &&
                        snapshot.guest_call_trace.size() == 1 &&
                        snapshot.guest_call_trace.front().string_slots.size() ==
                            1 &&
                        snapshot.guest_call_trace.front().string_slots.front()
                                .offset == 0x4 &&
                        snapshot.guest_call_trace.front().string_slots.front()
                                .has_address &&
                        snapshot.guest_call_trace.front().string_slots.front()
                                .address == string_address &&
                        snapshot.guest_call_trace.front().string_slots.front()
                                .has_value &&
                        snapshot.guest_call_trace.front().string_slots.front()
                                .value == expected_string &&
                        snapshot.guest_call_trace.front().string_slots.front()
                                .terminated &&
                        !snapshot.guest_call_trace.front().string_slots.front()
                             .truncated,
                    "guest call trace did not capture the bounded string argument");
            require(capture.text().find(
                        "string+0x4=\"C:\\\\cars\\\\engine.bin\"") !=
                        std::string::npos,
                    "live guest call trace omitted its captured string argument");
        }
        require(unsetenv("SHIFT_TRACE_GUEST_CALL_LIVE_LOG") == 0,
                "could not disable guest string live trace fixture");
        require(unsetenv("SHIFT_TRACE_GUEST_CALL_STRING_SLOTS") == 0,
                "could not disable guest string argument trace fixture");
        require(unsetenv("SHIFT_TRACE_GUEST_CALL_TARGETS") == 0,
                "could not disable guest string argument target fixture");
        require(setenv("SHIFT_TRACE_GUEST_CALLER", "0x00402100", 1) == 0,
                "could not enable failed guest string trace fixture");
        require(setenv("SHIFT_TRACE_GUEST_CALL_STRING_SLOTS", "0x4", 1) == 0,
                "could not configure failed guest string trace slots");
        {
            shift::runtime::RecompiledPcodeModule failed_string_trace_module(
                argv[1]);
            constexpr uint32_t string_address = 0x00035000;
            constexpr uint32_t stack_argument_address = 0x00033024;
            constexpr char expected_error_string[] = "effect-source-fixture";
            write_guest_u32(failed_string_trace_module, "ram",
                            stack_argument_address, string_address);
            write_guest_bytes(
                failed_string_trace_module, string_address,
                reinterpret_cast<const uint8_t*>(expected_error_string),
                sizeof(expected_error_string));
            require(failed_string_trace_module.call(0x00402100) != 0 &&
                        failed_string_trace_module.last_error().find(
                            "strings={0x4@0x00035000=effect-source-fixture}") !=
                            std::string::npos,
                    "failed guest call omitted its captured string argument: " +
                        failed_string_trace_module.last_error());
        }
        require(unsetenv("SHIFT_TRACE_GUEST_CALLER") == 0,
                "could not disable failed guest string trace fixture");
        require(unsetenv("SHIFT_TRACE_GUEST_CALL_STRING_SLOTS") == 0,
                "could not disable failed guest string trace slots");

        {
            shift::runtime::RecompiledPcodeModule crc_loop_module(argv[1]);
            require(crc_loop_module.load_override_module(argv[9]),
                    "0x0066caf0 CRC loop supplement could not be loaded: " +
                        crc_loop_module.last_error());
            constexpr uint32_t bytes = 0x00038000;
            constexpr uint32_t stack = 0x00033000;
            constexpr uint32_t return_address = 0x00406605;
            constexpr uint32_t saved_esi = 0x0badf00d;
            constexpr uint32_t saved_ebp = 0x55667788;
            constexpr uint32_t crc_table_word = 0x00af5250;
            constexpr uint32_t crc_table_value = 0x00fedcba;
            const uint8_t input = 0xa6;
            require(crc_loop_module.write_guest("ram", bytes, 1, &input),
                    "could not seed 0x0066caf0 CRC input");
            write_guest_u32(crc_loop_module, "ram", crc_table_word,
                            crc_table_value);
            write_guest_u32(crc_loop_module, "register", 0, 0x12345678);
            write_guest_u32(crc_loop_module, "register", 4, bytes);
            write_guest_u32(crc_loop_module, "register", 8, 0);
            write_guest_u32(crc_loop_module, "register", 0x10, stack);
            write_guest_u32(crc_loop_module, "register", 0x14, 0xdeadbeef);
            write_guest_u32(crc_loop_module, "register", 0x18, 1);
            write_guest_u32(crc_loop_module, "ram", stack, saved_esi);
            write_guest_u32(crc_loop_module, "ram", stack + 4, saved_ebp);
            write_guest_u32(crc_loop_module, "ram", stack + 8,
                            return_address);
            write_guest_u32(crc_loop_module, "ram", stack + 12, 0);
            require(crc_loop_module.call(0x0066caf0) == 0,
                    "0x0066caf0 CRC loop supplement failed: " +
                        crc_loop_module.last_error());
            require(read_guest_u32(crc_loop_module, "register", 0) ==
                            (((0x12345678u >> 8) ^ crc_table_value)) &&
                        read_guest_u32(crc_loop_module, "register", 4) ==
                            bytes + 1 &&
                        read_guest_u32(crc_loop_module, "register", 8) == 0xde &&
                        read_guest_u32(crc_loop_module, "register", 0x10) ==
                            stack + 16 &&
                        read_guest_u32(crc_loop_module, "register", 0x14) ==
                            saved_ebp &&
                        read_guest_u32(crc_loop_module, "register", 0x18) ==
                            saved_esi &&
                        read_guest_u32(crc_loop_module, "register", 0x284) ==
                            return_address,
                    "0x0066caf0 did not complete its CRC step and stdcall "
                    "epilogue with the expected register/stack state");
        }

        {
            shift::runtime::RecompiledPcodeModule xmem_module(argv[1]);
            require(xmem_module.load_override_module(argv[9]),
                    "0x0066f680 XMem override could not be loaded: " +
                        xmem_module.last_error());
            constexpr uint32_t stack = 0x00033000;
            constexpr uint32_t context = 0x12345678;
            constexpr uint32_t input = 0x00100000;
            constexpr uint32_t output = 0x00200000;
            constexpr uint32_t output_size_ptr = 0x00052000;
            constexpr uint32_t return_address = 0x00406905;
            std::vector<uint8_t> expected(0x8000);
            for (size_t index = 0; index < expected.size(); ++index)
                expected[index] = static_cast<uint8_t>(index * 37 + 11);
            std::vector<uint8_t> packed = {
                0x80, 0x10, 0x08, 0x30, 0x00, 0x00, 1, 0, 0, 0,
                1,    0,    0,    0,    1,    0,    0,    0};
            packed.insert(packed.end(), expected.begin(), expected.end());
            write_guest_bytes(xmem_module, input, packed.data(), packed.size());
            write_guest_u32(xmem_module, "ram", stack, return_address);
            write_guest_u32(xmem_module, "ram", stack + 4, context);
            write_guest_u32(xmem_module, "ram", stack + 8, output);
            write_guest_u32(xmem_module, "ram", stack + 12,
                            output_size_ptr);
            write_guest_u32(xmem_module, "ram", stack + 16, input);
            write_guest_u32(xmem_module, "ram", stack + 20,
                            static_cast<uint32_t>(packed.size()));
            write_guest_u32(xmem_module, "register", 0x00, output);
            write_guest_u32(xmem_module, "register", 0x04, context);
            write_guest_u32(xmem_module, "register", 0x08, 0x89abcdef);
            write_guest_u32(xmem_module, "register", 0x10, stack);
            write_guest_u32(xmem_module, "register", 0x18, 0x10293847);
            write_guest_u32(xmem_module, "register", 0x1c, 0x56473829);
            write_guest_u32(xmem_module, "register", 0x20, 0x76543210);
            write_guest_u32(xmem_module, "register", 0x24, 0x44332211);
            require(xmem_module.call(0x0066f680) == 0,
                    "0x0066f680 XMem override failed: " +
                        xmem_module.last_error());
            std::vector<uint8_t> decoded(expected.size());
            for (size_t offset = 0; offset < decoded.size(); offset += 16) {
                const size_t chunk =
                    std::min<size_t>(16, decoded.size() - offset);
                require(xmem_module.read_guest(
                            "ram", output + offset, chunk,
                            decoded.data() + offset),
                        "could not read synthetic XMem output");
            }
            require(decoded == expected &&
                        read_guest_u32(xmem_module, "ram", output_size_ptr) ==
                            expected.size() &&
                        read_guest_u32(xmem_module, "register", 0x00) == 0 &&
                        read_guest_u32(xmem_module, "register", 0x04) ==
                            context &&
                        read_guest_u32(xmem_module, "register", 0x08) ==
                            0x89abcdef &&
                        read_guest_u32(xmem_module, "register", 0x10) ==
                            stack + 4 &&
                        read_guest_u32(xmem_module, "register", 0x18) ==
                            0x10293847 &&
                        read_guest_u32(xmem_module, "register", 0x1c) ==
                            0x56473829 &&
                        read_guest_u32(xmem_module, "register", 0x20) ==
                            0x76543210 &&
                        read_guest_u32(xmem_module, "register", 0x24) ==
                            0x44332211 &&
                        read_guest_u32(xmem_module, "register", 0x284) ==
                            return_address,
                    "0x0066f680 did not decode XMem or preserve its cdecl "
                    "register/return state");
        }

        {
            shift::runtime::RecompiledPcodeModule bulk_fill_module(argv[1]);
            require(bulk_fill_module.load_override_module(argv[9]),
                    "0x0090e50d bulk-fill override could not be loaded: " +
                        bulk_fill_module.last_error());
            constexpr uint32_t stack = 0x00033000;
            constexpr uint32_t destination = 0x00050003;
            constexpr uint32_t size = 0x00020000;
            constexpr uint32_t return_address = 0x00401234;
            constexpr uint32_t before = destination - 1;
            constexpr uint32_t after = destination + size;
            const uint8_t sentinel = 0x7c;
            require(bulk_fill_module.write_guest("ram", before, 1, &sentinel) &&
                        bulk_fill_module.write_guest("ram", after, 1, &sentinel),
                    "could not seed bulk-fill boundary sentinels");
            write_guest_u32(bulk_fill_module, "ram", stack, return_address);
            write_guest_u32(bulk_fill_module, "ram", stack + 4, destination);
            write_guest_u32(bulk_fill_module, "ram", stack + 8, 0x123456a5);
            write_guest_u32(bulk_fill_module, "ram", stack + 12, size);
            write_guest_u32(bulk_fill_module, "register", 0x10, stack);
            write_guest_u32(bulk_fill_module, "register", 0x14, 0x11223344);
            write_guest_u32(bulk_fill_module, "register", 0x1c, 0x55667788);
            require(bulk_fill_module.call(0x0090e50d) == 0,
                    "0x0090e50d bulk-fill override failed: " +
                        bulk_fill_module.last_error());
            uint8_t first = 0;
            uint8_t middle = 0;
            uint8_t last = 0;
            uint8_t before_value = 0;
            uint8_t after_value = 0;
            require(bulk_fill_module.read_guest("ram", destination, 1, &first) &&
                        bulk_fill_module.read_guest("ram", destination + size / 2,
                                                    1, &middle) &&
                        bulk_fill_module.read_guest("ram", destination + size - 1,
                                                    1, &last) &&
                        bulk_fill_module.read_guest("ram", before, 1,
                                                    &before_value) &&
                        bulk_fill_module.read_guest("ram", after, 1,
                                                    &after_value) &&
                        first == 0xa5 && middle == 0xa5 && last == 0xa5 &&
                        before_value == sentinel && after_value == sentinel &&
                        read_guest_u32(bulk_fill_module, "register", 0) ==
                            destination &&
                        read_guest_u32(bulk_fill_module, "register", 0x10) ==
                            stack + 4 &&
                        read_guest_u32(bulk_fill_module, "register", 0x14) ==
                            0x11223344 &&
                        read_guest_u32(bulk_fill_module, "register", 0x1c) ==
                            0x55667788 &&
                        read_guest_u32(bulk_fill_module, "register", 0x284) ==
                            return_address,
                    "0x0090e50d changed bytes outside the fill or returned "
                    "incorrect register/stack state");

            constexpr uint32_t zero_stack = stack + 0x20;
            constexpr uint32_t zero_destination = destination + size + 0x10;
            write_guest_u32(bulk_fill_module, "ram", zero_stack,
                            return_address + 1);
            write_guest_u32(bulk_fill_module, "ram", zero_stack + 4,
                            zero_destination);
            write_guest_u32(bulk_fill_module, "ram", zero_stack + 8, 0x100);
            write_guest_u32(bulk_fill_module, "ram", zero_stack + 12, 0);
            write_guest_u32(bulk_fill_module, "register", 0x10, zero_stack);
            require(bulk_fill_module.call(0x0090e50d) == 0 &&
                        read_guest_u32(bulk_fill_module, "register", 0) ==
                            zero_destination &&
                        read_guest_u32(bulk_fill_module, "register", 0x10) ==
                            zero_stack + 4 &&
                        read_guest_u32(bulk_fill_module, "register", 0x284) ==
                            return_address + 1,
                    "0x0090e50d rejected a zero-length fill or returned "
                    "incorrect state");
        }

        {
            shift::runtime::RecompiledPcodeModule ui_cleanup_module(argv[1]);
            require(ui_cleanup_module.load_override_module(argv[9]),
                    "0x00509689 Ghidra supplement could not be loaded: " +
                        ui_cleanup_module.last_error());
            constexpr uint32_t stack = 0x00035000;
            constexpr uint32_t ebp = stack + 12;
            constexpr uint32_t receiver = 0x00027000;
            constexpr uint32_t return_address = 0x00406705;
            constexpr uint32_t saved_ebx = 0x01024000;
            constexpr uint32_t saved_esi = 0x22222222;
            constexpr uint32_t saved_edi = 0x11111111;
            write_guest_u32(ui_cleanup_module, "register", 4, 0x33333333);
            write_guest_u32(ui_cleanup_module, "register", 0x0c, receiver);
            write_guest_u32(ui_cleanup_module, "register", 0x10, stack);
            write_guest_u32(ui_cleanup_module, "register", 0x14, ebp);
            write_guest_u32(ui_cleanup_module, "register", 0x18, 0x44444444);
            write_guest_u32(ui_cleanup_module, "register", 0x1c, 0x55555555);
            write_guest_u32(ui_cleanup_module, "ram", receiver + 0xad, 0);
            write_guest_u32(ui_cleanup_module, "ram", receiver + 0x2d, 0);
            write_guest_u32(ui_cleanup_module, "ram", stack, saved_edi);
            write_guest_u32(ui_cleanup_module, "ram", stack + 4, saved_esi);
            write_guest_u32(ui_cleanup_module, "ram", stack + 8, saved_ebx);
            write_guest_u32(ui_cleanup_module, "ram", ebp, 0x00033000);
            write_guest_u32(ui_cleanup_module, "ram", ebp + 4,
                            return_address);
            write_guest_u32(ui_cleanup_module, "ram", ebp + 8, 0);
            require(ui_cleanup_module.call(0x00509689) == 0,
                    "0x00509689 cleanup block failed: " +
                        ui_cleanup_module.last_error());
            require(read_guest_u32(ui_cleanup_module, "register", 0) == 0 &&
                        read_guest_u32(ui_cleanup_module, "register", 4) ==
                            0x33333333 &&
                        read_guest_u32(ui_cleanup_module, "register", 0x10) ==
                            ebp + 8 &&
                        read_guest_u32(ui_cleanup_module, "register", 0x14) ==
                            0x00033000 &&
                        read_guest_u32(ui_cleanup_module, "register", 0x18) ==
                            saved_esi &&
                        read_guest_u32(ui_cleanup_module, "register", 0x1c) ==
                            saved_edi &&
                        read_guest_u32(ui_cleanup_module, "register", 0x284) ==
                            return_address &&
                    read_guest_u32(ui_cleanup_module, "ram", receiver + 0x2d) ==
                            1,
                    "0x00509689 did not apply the readiness-byte store and "
                    "restore its caller frame: eax=" +
                        std::to_string(read_guest_u32(ui_cleanup_module,
                                                      "register", 0)) +
                        " ecx=" +
                        std::to_string(read_guest_u32(ui_cleanup_module,
                                                      "register", 4)) +
                        " esp=" +
                        std::to_string(read_guest_u32(ui_cleanup_module,
                                                      "register", 0x10)) +
                        " ebp=" +
                        std::to_string(read_guest_u32(ui_cleanup_module,
                                                      "register", 0x14)) +
                        " esi=" +
                        std::to_string(read_guest_u32(ui_cleanup_module,
                                                      "register", 0x18)) +
                        " edi=" +
                        std::to_string(read_guest_u32(ui_cleanup_module,
                                                      "register", 0x1c)) +
                        " eip=" +
                        std::to_string(read_guest_u32(ui_cleanup_module,
                                                      "register", 0x284)) +
                        " state=" +
                        std::to_string(read_guest_u32(ui_cleanup_module,
                                                      "ram", receiver + 0x2d)));
        }

        {
            shift::runtime::RecompiledPcodeModule tail_alias_module(argv[1]);
            require(tail_alias_module.load_override_module(argv[9]),
                    "0x00509e60 tail alias could not be loaded: " +
                        tail_alias_module.last_error());
            constexpr uint32_t receiver = 0x00038000;
            constexpr uint32_t stack = 0x00035000;
            constexpr uint32_t return_address = 0x00406805;
            const uint8_t pending = 1;
            const uint32_t operation = 0x12345678;
            require(tail_alias_module.write_guest("ram", receiver + 4, 1,
                                                  &pending),
                    "could not seed 0x00509e60 request state");
            write_guest_u32(tail_alias_module, "ram", receiver + 0x24,
                            operation);
            write_guest_u32(tail_alias_module, "register", 4, receiver);
            write_guest_u32(tail_alias_module, "register", 8, 0x11223344);
            write_guest_u32(tail_alias_module, "register", 0x10, stack);
            write_guest_u32(tail_alias_module, "ram", stack, return_address);
            require(tail_alias_module.call(0x00509e60) == 0,
                    "0x00509e60 tail alias failed: " +
                        tail_alias_module.last_error());
            require(read_guest_u32(tail_alias_module, "register", 4) ==
                            receiver &&
                        read_guest_u32(tail_alias_module, "register", 8) ==
                            0x11223344 &&
                        read_guest_u32(tail_alias_module, "register", 0x10) ==
                            stack &&
                        read_guest_u32(tail_alias_module, "ram", receiver + 4) ==
                            0 &&
                        read_guest_u32(tail_alias_module, "ram", receiver + 0x24) ==
                            0 &&
                        read_guest_u32(tail_alias_module, "ram", receiver + 0x2c) ==
                            4,
                    "0x00509e60 did not tail-dispatch to 0x00509e40 with "
                    "guest state intact");
        }

        {
            shift::runtime::RecompiledPcodeModule state_machine_block_module(
                argv[10]);
            constexpr uint32_t stack = 0x00036000;
            constexpr uint32_t state = 0x27e31d68;
            write_guest_u32(state_machine_block_module, "register", 4,
                            0xaaaaaaaa);
            write_guest_u32(state_machine_block_module, "register", 0x10,
                            stack);
            write_guest_u32(state_machine_block_module, "register", 0x18,
                            state);
            write_guest_u32(state_machine_block_module, "ram", stack,
                            0x00406905);
            require(state_machine_block_module.call(0x0050967d) == 0,
                    "0x0050967d Ghidra block failed: " +
                        state_machine_block_module.last_error());
            std::array<uint8_t, 12> recorded_state{};
            require(state_machine_block_module.read_guest(
                        "ram", 0x00020150, recorded_state.size(),
                        recorded_state.data()),
                    "could not read 0x0050967d branch target state");
            const auto recorded_u32 = [&](size_t offset) {
                return static_cast<uint32_t>(recorded_state[offset]) |
                       (static_cast<uint32_t>(recorded_state[offset + 1]) << 8) |
                       (static_cast<uint32_t>(recorded_state[offset + 2]) << 16) |
                       (static_cast<uint32_t>(recorded_state[offset + 3]) << 24);
            };
            require(read_guest_u32(state_machine_block_module, "register", 4) ==
                            state &&
                        read_guest_u32(state_machine_block_module, "register",
                                       0x10) == stack &&
                        recorded_u32(0) == state &&
                        recorded_u32(4) == state &&
                        recorded_u32(8) == stack,
                    "0x0050967d did not copy ESI to ECX, return from its call, "
                    "and tail-dispatch 0x0050958c with the original stack");

            constexpr uint32_t frame_pointer = 0x00037020;
            constexpr uint32_t active_stack = frame_pointer - 0x18;
            constexpr uint32_t saved_edi = 0x11112222;
            constexpr uint32_t saved_esi = 0x33334444;
            constexpr uint32_t saved_ebx = 0x55556666;
            constexpr uint32_t saved_ebp = 0x77778888;
            write_guest_u32(state_machine_block_module, "register", 0x10,
                            active_stack);
            write_guest_u32(state_machine_block_module, "register", 0x14,
                            frame_pointer);
            write_guest_u32(state_machine_block_module, "register", 0x18,
                            0x9999aaaa);
            write_guest_u32(state_machine_block_module, "register", 0x1c,
                            0xbbbbcccc);
            write_guest_u32(state_machine_block_module, "register", 0x0c,
                            0xddddeeee);
            write_guest_u32(state_machine_block_module, "ram",
                            frame_pointer - 0x18, saved_edi);
            write_guest_u32(state_machine_block_module, "ram",
                            frame_pointer - 0x14, saved_esi);
            write_guest_u32(state_machine_block_module, "ram",
                            frame_pointer - 0x10, saved_ebx);
            write_guest_u32(state_machine_block_module, "ram", frame_pointer,
                            saved_ebp);
            require(state_machine_block_module.call(0x0050967d) == 0,
                    "0x0050967d split-continuation epilogue failed: " +
                        state_machine_block_module.last_error());
            require(read_guest_u32(state_machine_block_module, "register", 0) ==
                            0 &&
                        read_guest_u32(state_machine_block_module, "register",
                                       0x0c) == saved_ebx &&
                        read_guest_u32(state_machine_block_module, "register",
                                       0x10) == frame_pointer + 8 &&
                        read_guest_u32(state_machine_block_module, "register",
                                       0x14) == saved_ebp &&
                        read_guest_u32(state_machine_block_module, "register",
                                       0x18) == saved_esi &&
                        read_guest_u32(state_machine_block_module, "register",
                                       0x1c) == saved_edi,
                    "0x0050967d did not execute the saved-register epilogue "
                    "after 0x0050958c returned at the split continuation");

            constexpr uint32_t owner = 0x00039000;
            constexpr uint32_t child = 0x00039100;
            constexpr uint32_t stack_pointer = 0x00039200;
            constexpr uint32_t block_frame_pointer = 0x00039300;
            const uint8_t active_owner = 1;
            write_guest_u32(state_machine_block_module, "register", 0x0c,
                            owner);
            write_guest_u32(state_machine_block_module, "register", 0x18,
                            child);
            write_guest_u32(state_machine_block_module, "register", 0x10,
                            stack_pointer);
            write_guest_u32(state_machine_block_module, "register", 0x14,
                            block_frame_pointer);
            require(state_machine_block_module.write_guest(
                        "ram", owner + 0xad, 1, &active_owner),
                    "could not seed 0x005095f0 owner flag");
            require(state_machine_block_module.call(0x005095f0) == 0,
                    "0x005095f0 owner-active branch failed: " +
                        state_machine_block_module.last_error());
            require(read_guest_u32(state_machine_block_module, "ram",
                                   0x20160) == 0 &&
                        read_guest_u32(state_machine_block_module, "ram",
                                       0x20164) == 1 &&
                        read_guest_u32(state_machine_block_module, "ram",
                                       0x20168) == child &&
                        read_guest_u32(state_machine_block_module, "ram",
                                       stack_pointer - 4) == 0x00509610 &&
                        read_guest_u32(state_machine_block_module, "register",
                                       0x10) == stack_pointer &&
                        read_guest_u32(state_machine_block_module, "ram",
                                       0x20170) == child &&
                        read_guest_u32(state_machine_block_module, "ram",
                                       0x20174) == stack_pointer,
                    "0x005095f0 did not call 0x00508970 with the correct "
                    "return address and tail-dispatch to 0x00509588");

            constexpr uint32_t second_stack = 0x00039400;
            constexpr uint32_t second_frame = 0x00039500;
            const uint8_t inactive_owner = 0;
            const uint8_t child_active = 1;
            require(state_machine_block_module.write_guest(
                        "ram", owner + 0xad, 1, &inactive_owner) &&
                        state_machine_block_module.write_guest(
                            "ram", child + 0xed, 1, &child_active),
                    "could not seed 0x005095f0 inactive-owner branch");
            write_guest_u32(state_machine_block_module, "ram", child + 0xe4,
                            2);
            write_guest_u32(state_machine_block_module, "register", 0x10,
                            second_stack);
            write_guest_u32(state_machine_block_module, "register", 0x14,
                            second_frame);
            const uint8_t clear_local = 0;
            require(state_machine_block_module.write_guest(
                        "ram", second_frame - 2, 1, &clear_local),
                    "could not clear the 0x005095f0 local flag");
            require(state_machine_block_module.call(0x005095f0) == 0,
                    "0x005095f0 inactive-owner branch failed: " +
                        state_machine_block_module.last_error());
            require(read_guest_u32(state_machine_block_module, "ram",
                                   0x20160) == 1 &&
                        read_guest_u32(state_machine_block_module, "ram",
                                       0x20164) == 1 &&
                        read_guest_u32(state_machine_block_module, "ram",
                                       0x20170) == child &&
                        read_guest_u32(state_machine_block_module, "ram",
                                       0x20174) == second_stack &&
                        read_guest_u32(state_machine_block_module, "ram",
                                       second_stack - 4) == 0x00509600 &&
                        read_guest_u32(state_machine_block_module, "register",
                                       0x10) == second_stack &&
                        read_guest_u32(state_machine_block_module, "ram",
                                       second_frame - 2) == 1,
                    "0x005095f0 did not preserve the inactive-owner branch, "
                    "local flag write, or continuation stack");

            constexpr uint32_t initialization_stack = 0x0003a100;
            constexpr uint32_t initial_esi = 0x0003a111;
            constexpr uint32_t container = 0x0003b000;
            constexpr uint32_t global_owner = 0x0003c000;
            constexpr uint32_t return_address = 0x00407005;
            write_guest_u32(state_machine_block_module, "register", 0x10,
                            initialization_stack);
            write_guest_u32(state_machine_block_module, "register", 0x18,
                            initial_esi);
            write_guest_u32(state_machine_block_module, "register", 0x04,
                            0x12345678);
            write_guest_u32(state_machine_block_module, "ram",
                            initialization_stack, return_address);
            write_guest_u32(state_machine_block_module, "ram", 0x00bbf960,
                            container);
            write_guest_u32(state_machine_block_module, "ram", 0x00bc1850,
                            global_owner);
            require(state_machine_block_module.call(0x0054b560) == 0,
                    "Ghidra-lowered 0x0054b560 initializer failed: " +
                        state_machine_block_module.last_error());
            constexpr std::array<uint32_t, 8> initialization_calls = {
                1, 2, 3, 4, 5, 4, 6, 7};
            bool call_sequence_matches =
                read_guest_u32(state_machine_block_module, "ram", 0x20180) ==
                initialization_calls.size();
            for (size_t i = 0; call_sequence_matches &&
                               i < initialization_calls.size(); ++i) {
                call_sequence_matches =
                    read_guest_u32(state_machine_block_module, "ram",
                                   0x20184 + i * 4) == initialization_calls[i];
            }
            require(call_sequence_matches,
                    "0x0054b560 called its helper functions out of order");
            require(read_guest_u32(state_machine_block_module, "ram",
                                   0x20200 + 4 * 4) == container &&
                        read_guest_u32(state_machine_block_module, "ram",
                                       0x20200 + 6 * 4) == container &&
                        read_guest_u32(state_machine_block_module, "ram",
                                       0x20200 + 7 * 4) ==
                            global_owner + 0x1eec,
                    "0x0054b560 passed an unexpected receiver to a helper");
            require(read_guest_u32(state_machine_block_module, "register", 0) ==
                        7,
                    "0x0054b560 did not return 7 in EAX");
            require(read_guest_u32(state_machine_block_module, "register",
                                   0x10) == initialization_stack + 4,
                    "0x0054b560 did not consume its caller return address");
            require(read_guest_u32(state_machine_block_module, "register",
                                   0x18) == initial_esi,
                    "0x0054b560 did not restore ESI");

            constexpr uint32_t getter_receiver = 0x0003d000;
            constexpr uint32_t getter_stack = 0x0003d100;
            constexpr uint32_t getter_return_address = 0x00408005;
            const uint8_t getter_value = 0xa5;
            require(state_machine_block_module.write_guest(
                        "ram", getter_receiver + 0x32f, 1, &getter_value),
                    "could not seed 0x0085b0b0 byte field");
            write_guest_u32(state_machine_block_module, "register", 0x00,
                            0x11223344);
            write_guest_u32(state_machine_block_module, "register", 0x04,
                            getter_receiver);
            write_guest_u32(state_machine_block_module, "register", 0x10,
                            getter_stack);
            write_guest_u32(state_machine_block_module, "ram", getter_stack,
                            getter_return_address);
            require(state_machine_block_module.call(0x0085b0b0) == 0,
                    "0x0085b0b0 byte accessor failed: " +
                        state_machine_block_module.last_error());
            require(read_guest_u32(state_machine_block_module, "register",
                                   0x00) == 0x112233a5 &&
                        read_guest_u32(state_machine_block_module, "register",
                                       0x10) == getter_stack + 4 &&
                        read_guest_u32(state_machine_block_module, "register",
                                       0x284) == getter_return_address,
                    "0x0085b0b0 did not preserve EAX high bytes or emulate RET");

            constexpr uint32_t pointer_getter_receiver = 0x0003e000;
            constexpr uint32_t pointer_getter_stack = 0x0003e100;
            constexpr uint32_t pointer_getter_return = 0x00408105;
            constexpr uint32_t pointer_getter_value = 0x27f4e380;
            write_guest_u32(state_machine_block_module, "ram",
                            pointer_getter_receiver + 0x680,
                            pointer_getter_value);
            write_guest_u32(state_machine_block_module, "register", 0x04,
                            pointer_getter_receiver);
            write_guest_u32(state_machine_block_module, "register", 0x10,
                            pointer_getter_stack);
            write_guest_u32(state_machine_block_module, "ram",
                            pointer_getter_stack, pointer_getter_return);
            require(state_machine_block_module.call(0x0082d5f0) == 0 &&
                        read_guest_u32(state_machine_block_module, "register",
                                       0x00) == pointer_getter_value &&
                        read_guest_u32(state_machine_block_module, "register",
                                       0x10) == pointer_getter_stack + 4 &&
                        read_guest_u32(state_machine_block_module, "register",
                                       0x284) == pointer_getter_return,
                    "0x0082d5f0 did not load receiver +0x680 and emulate RET");
        }

        require(setenv("SHIFT_TRACE_GUEST_CALL_TARGETS", "0x00685700", 1) ==
                    0,
                "could not enable indirect tail-dispatch trace fixture");
        {
            shift::runtime::RecompiledPcodeModule tail_dispatch_module(argv[1]);
            require(tail_dispatch_module.load_override_module(argv[3]),
                    "tail-dispatch target fixture could not be loaded: " +
                        tail_dispatch_module.last_error());
            require(tail_dispatch_module.load_override_module(argv[9]),
                    "tail-dispatch frontier override could not be loaded: " +
                        tail_dispatch_module.last_error());
            constexpr uint32_t receiver = 0x00024000;
            constexpr uint32_t vtable = 0x00025000;
            constexpr uint32_t stack = 0x00033000;
            constexpr uint32_t return_address = 0x00406205;
            write_guest_u32(tail_dispatch_module, "register", 4, receiver);
            write_guest_u32(tail_dispatch_module, "register", 0x10, stack);
            write_guest_u32(tail_dispatch_module, "ram", receiver, vtable);
            write_guest_u32(tail_dispatch_module, "ram", vtable + 8,
                            0x00685700);
            write_guest_u32(tail_dispatch_module, "ram", stack,
                            return_address);
            require(tail_dispatch_module.call(0x005f1830) == 0,
                    "indirect tail-dispatch override failed: " +
                        tail_dispatch_module.last_error());
            std::array<uint8_t, 4> override_bytes{};
            require(tail_dispatch_module.read_guest(
                        "ram", 0x00020000, override_bytes.size(),
                        override_bytes.data()) &&
                        override_bytes ==
                            std::array<uint8_t, 4>{'O', 'V', 'R', 'D'} &&
                        read_guest_u32(tail_dispatch_module, "register", 0) ==
                            vtable,
                    "indirect tail-dispatch did not preserve MOV EAX,[ECX] "
                    "and reach the vtable target");
            const auto snapshot =
                tail_dispatch_module.guest_scheduler_snapshot();
            require(snapshot.guest_call_trace.size() == 1 &&
                        snapshot.guest_call_trace.front().caller ==
                            0x005f1830 &&
                        snapshot.guest_call_trace.front().function ==
                            0x00685700 &&
                        snapshot.guest_call_trace.front().has_return_address &&
                        snapshot.guest_call_trace.front().return_address ==
                            return_address &&
                        snapshot.guest_call_trace.front().completed,
                    "indirect tail-dispatch did not record the selected target");
        }
        {
            shift::runtime::RecompiledPcodeModule vtable_dispatch_module(argv[1]);
            require(vtable_dispatch_module.load_override_module(argv[9]),
                    "0x005b0d50 vtable-dispatch override could not be loaded: " +
                        vtable_dispatch_module.last_error());
            constexpr uint32_t receiver = 0x00026000;
            constexpr uint32_t vtable = 0x00027000;
            constexpr uint32_t stack = 0x00033000;
            constexpr uint32_t return_address = 0x00406405;
            write_guest_u32(vtable_dispatch_module, "register", 4, receiver);
            write_guest_u32(vtable_dispatch_module, "register", 0x10, stack);
            write_guest_u32(vtable_dispatch_module, "ram", receiver, vtable);
            write_guest_u32(vtable_dispatch_module, "ram", vtable + 0x48,
                            0x00685700);
            write_guest_u32(vtable_dispatch_module, "ram", stack,
                            return_address);
            require(vtable_dispatch_module.call(0x005b0d50) == 0,
                    "0x005b0d50 vtable-dispatch override failed: " +
                        vtable_dispatch_module.last_error());
            std::array<uint8_t, 4> dispatched_bytes{};
            const bool side_effect_read = vtable_dispatch_module.read_guest(
                "ram", 0x00020000, dispatched_bytes.size(),
                dispatched_bytes.data());
            const uint32_t returned_eax =
                read_guest_u32(vtable_dispatch_module, "register", 0);
            require(side_effect_read &&
                        dispatched_bytes ==
                            std::array<uint8_t, 4>{0xd0, 0x99, 0xaa, 0x00} &&
                        returned_eax == vtable,
                    "0x005b0d50 side_effect=" +
                        std::to_string(side_effect_read) + " bytes=" +
                        std::to_string(dispatched_bytes[0]) + "," +
                        std::to_string(dispatched_bytes[1]) + "," +
                        std::to_string(dispatched_bytes[2]) + "," +
                        std::to_string(dispatched_bytes[3]) + " EAX=" +
                        std::to_string(returned_eax));
            const auto snapshot =
                vtable_dispatch_module.guest_scheduler_snapshot();
            require(snapshot.guest_call_trace.size() == 1 &&
                        snapshot.guest_call_trace.front().caller ==
                            0x005b0d50 &&
                        snapshot.guest_call_trace.front().function ==
                            0x00685700 &&
                        snapshot.guest_call_trace.front().has_return_address &&
                        snapshot.guest_call_trace.front().return_address ==
                            return_address &&
                        snapshot.guest_call_trace.front().completed,
                    "0x005b0d50 did not preserve the original return address");
        }
        {
            shift::runtime::RecompiledPcodeModule async_request_module(argv[1]);
            require(async_request_module.load_override_module(argv[9]),
                    "0x0066cc70 request-handler override could not be loaded: " +
                        async_request_module.last_error());
            constexpr uint32_t receiver = 0x00028000;
            constexpr uint32_t request = 0x00029000;
            constexpr uint32_t stack = 0x00033000;
            constexpr uint32_t return_address = 0x00406505;
            constexpr uint32_t first_argument = 0x12345678;
            constexpr uint32_t second_argument = 0x87654321;
            constexpr uint32_t preserved_value = 0x0002a000;
            constexpr uint32_t saved_esi = 0x11111111;
            constexpr uint32_t saved_edi = 0x22222222;
            write_guest_u32(async_request_module, "register", 4, receiver);
            write_guest_u32(async_request_module, "register", 8, request);
            write_guest_u32(async_request_module, "register", 0x10, stack);
            write_guest_u32(async_request_module, "register", 0x18, saved_esi);
            write_guest_u32(async_request_module, "register", 0x1c, saved_edi);
            write_guest_u32(async_request_module, "ram", stack,
                            return_address);
            write_guest_u32(async_request_module, "ram", request + 0x10,
                            first_argument);
            write_guest_u32(async_request_module, "ram", request + 0x1c,
                            second_argument);
            write_guest_u32(async_request_module, "ram", receiver + 0xbc,
                            preserved_value);
            require(async_request_module.call(0x0066cc70) == 0,
                    "0x0066cc70 request-handler override failed: " +
                        async_request_module.last_error());
            require(read_guest_u32(async_request_module, "register", 0) == 1 &&
                        read_guest_u32(async_request_module, "register", 4) ==
                            receiver + 8 &&
                        read_guest_u32(async_request_module, "register", 8) ==
                            preserved_value &&
                        read_guest_u32(async_request_module, "register", 0x10) ==
                            stack + 4 &&
                        read_guest_u32(async_request_module, "register", 0x18) ==
                            saved_esi &&
                        read_guest_u32(async_request_module, "register", 0x1c) ==
                            saved_edi &&
                        read_guest_u32(async_request_module, "register", 0x284) ==
                            return_address &&
                        read_guest_u32(async_request_module, "ram", receiver + 0xbc) ==
                            preserved_value,
                    "0x0066cc70 return state eax=" +
                        std::to_string(read_guest_u32(async_request_module,
                                                      "register", 0)) +
                        " ecx=" +
                        std::to_string(read_guest_u32(async_request_module,
                                                      "register", 4)) +
                        " edx=" +
                        std::to_string(read_guest_u32(async_request_module,
                                                      "register", 8)) +
                        " esp=" +
                        std::to_string(read_guest_u32(async_request_module,
                                                      "register", 0x10)) +
                        " esi=" +
                        std::to_string(read_guest_u32(async_request_module,
                                                      "register", 0x18)) +
                        " edi=" +
                        std::to_string(read_guest_u32(async_request_module,
                                                      "register", 0x1c)) +
                        " eip=" +
                        std::to_string(read_guest_u32(async_request_module,
                                                      "register", 0x284)) +
                        " object=" +
                        std::to_string(read_guest_u32(async_request_module,
                                                      "ram", receiver + 0xbc)));
            require(read_guest_u32(async_request_module, "ram", 0x00020120) ==
                            receiver + 8 &&
                        read_guest_u32(async_request_module, "ram", 0x00020124) ==
                            preserved_value &&
                        read_guest_u32(async_request_module, "ram", 0x00020128) ==
                            first_argument &&
                        read_guest_u32(async_request_module, "ram", 0x0002012c) ==
                            second_argument,
                    "0x0066cc70 call args=" +
                        std::to_string(read_guest_u32(async_request_module,
                                                      "ram", 0x00020120)) +
                        "," +
                        std::to_string(read_guest_u32(async_request_module,
                                                      "ram", 0x00020124)) +
                        "," +
                        std::to_string(read_guest_u32(async_request_module,
                                                      "ram", 0x00020128)) +
                        "," +
                        std::to_string(read_guest_u32(async_request_module,
                                                      "ram", 0x0002012c)));
        }
        require(unsetenv("SHIFT_TRACE_GUEST_CALL_TARGETS") == 0,
                "could not disable indirect tail-dispatch trace fixture");

        {
            shift::runtime::RecompiledPcodeModule corrected_body_module(argv[1]);
            require(corrected_body_module.load_override_module(argv[9]),
                    "corrected 0x00652af0 body could not be loaded: " +
                        corrected_body_module.last_error());
            constexpr uint32_t receiver = 0x00034000;
            constexpr uint32_t stack = 0x00033000;
            constexpr uint32_t saved_ebp = 0x00036000;
            constexpr uint32_t return_address = 0x00406305;
            constexpr uint32_t argument = 0x100;
            write_guest_u32(corrected_body_module, "register", 4, receiver);
            write_guest_u32(corrected_body_module, "register", 0x10, stack);
            write_guest_u32(corrected_body_module, "register", 0x14,
                            saved_ebp);
            write_guest_u32(corrected_body_module, "ram", stack,
                            return_address);
            write_guest_u32(corrected_body_module, "ram", stack + 4,
                            argument);
            write_guest_u32(corrected_body_module, "ram", receiver + 0x54,
                            0x00035200);
            write_guest_u32(corrected_body_module, "ram", receiver + 0x58,
                            0x00035100);
            require(corrected_body_module.call(0x00652af0) == 0,
                    "corrected 0x00652af0 body failed: " +
                        corrected_body_module.last_error());
            require(read_guest_u32(corrected_body_module, "register", 0) ==
                            argument &&
                        read_guest_u32(corrected_body_module, "register",
                                       0x10) == stack + 8 &&
                        read_guest_u32(corrected_body_module, "register",
                                       0x14) == saved_ebp &&
                        read_guest_u32(corrected_body_module, "register",
                                       0x284) == return_address,
                    "corrected 0x00652af0 body did not execute its internal "
                    "0x00652b13 epilogue");
        }

        require(setenv("SHIFT_TRACE_UI_STATE_GATE", "1", 1) == 0,
                "could not enable UI state gate trace fixture");
        require(setenv("SHIFT_TRACE_GUEST_PROVENANCE", "0x00be250c", 1) == 0,
                "could not enable helper flag provenance fixture");
        {
            shift::runtime::RecompiledPcodeModule gate_trace_module(argv[1]);
            write_guest_u32(gate_trace_module, "register", 4, 0x00be2500);
            require(gate_trace_module.call(0x0050c7f0) == 0,
                    "helper flag writer fixture failed: " +
                        gate_trace_module.last_error());
            require(gate_trace_module.call(0x0050c7e0) == 0,
                    "adjacent helper byte writer fixture failed: " +
                        gate_trace_module.last_error());
            require(gate_trace_module.call(0x0050ceb0) == 0,
                    "UI state gate fixture failed: " +
                        gate_trace_module.last_error());
            const auto snapshot = gate_trace_module.guest_scheduler_snapshot();
            require(snapshot.ui_state_gate_trace_enabled &&
                        !snapshot.ui_state_gate_trace_truncated &&
                        snapshot.ui_state_gate_trace.size() == 2,
                    "UI state gate trace missed the gate/helper calls");
            const auto& helper = snapshot.ui_state_gate_trace.back();
            const auto& writer = helper.helper_flag_last_writer;
            require(helper.function == 0x0050c880,
                    "UI helper trace captured the wrong function");
            require(helper.has_helper_flag_byte &&
                        helper.helper_flag_byte == 1,
                    "UI helper trace missed the enabled flag byte");
            require(helper.has_helper_flag_last_writer,
                    "UI helper trace missed the flag byte's last writer");
            require(writer.function == 0x0050c7f0,
                    "UI helper trace identified the wrong flag writer");
            require(writer.has_ecx_entry &&
                        writer.ecx_entry == 0x00be2500,
                    "UI helper trace lost the writer ECX receiver");
            require(writer.write_address == 0x00be250c &&
                        writer.write_size == 1 &&
                        writer.word_value == 0x00000001,
                    "UI helper trace reported the wrong byte write");
        }
        require(unsetenv("SHIFT_TRACE_GUEST_PROVENANCE") == 0,
                "could not disable helper flag provenance fixture");
        require(unsetenv("SHIFT_TRACE_UI_STATE_GATE") == 0,
                "could not disable UI state gate trace fixture");

        shift::runtime::RecompiledPcodeModule module(argv[1]);
        require(module.load_supplemental_module(argv[2]),
                "P-code supplement could not be loaded: " + module.last_error());
        require(module.load_override_module(argv[3]),
                "P-code override could not be loaded: " + module.last_error());
        const auto image = module.load_pe32_image(argv[4]);
        require(image.image_base == 0x00400000 &&
                    image.image_size == 0x3000 &&
                    image.entry_point == 0x00401020 &&
                    image.section_count == 2 &&
                    image.import_module_count == 3 &&
                    image.import_function_count == 81 &&
                    image.import_stub_base == 0xf0000000,
                "PE32 loader returned unexpected image metadata: image=" +
                    std::to_string(image.image_base) + ", size=" +
                    std::to_string(image.image_size) + ", entry=" +
                    std::to_string(image.entry_point) + ", sections=" +
                    std::to_string(image.section_count) + ", modules=" +
                    std::to_string(image.import_module_count) + ", imports=" +
                    std::to_string(image.import_function_count) + ", stubs=" +
                    std::to_string(image.import_stub_base));

        shift::runtime::RecompiledPcodeModule winsock_module(argv[1]);
        const auto winsock_image =
            winsock_module.load_pe32_image(wsa_startup_fixture_path);
        require(winsock_image.import_module_count == 2 &&
                    winsock_image.import_function_count == 4,
                "Winsock fixture imports were not parsed");
        const uint32_t wsa_startup_stub = read_guest_u32(
            winsock_module, "ram", winsock_image.image_base + 0x2080);
        const uint32_t wsa_cleanup_stub = read_guest_u32(
            winsock_module, "ram", winsock_image.image_base + 0x2084);
        const uint32_t wsa_wait_stub = read_guest_u32(
            winsock_module, "ram", winsock_image.image_base + 0x2088);
        const uint32_t create_event_stub = read_guest_u32(
            winsock_module, "ram", winsock_image.image_base + 0x2100);
        require(wsa_startup_stub == 0xf0000000 &&
                    wsa_cleanup_stub == 0xf0000010 &&
                    wsa_wait_stub == 0xf0000020 &&
                    create_event_stub == 0xf0000030,
                "Winsock or Kernel32 imports were not mapped to their traps");
        const uint32_t wsadata_address = winsock_image.image_base + 0x2200;
        const uint32_t event_array_address = winsock_image.image_base + 0x23a0;
        write_guest_u32(winsock_module, "ram", event_array_address, 0);
        require(invoke_import(winsock_module, wsa_wait_stub,
                              {1, event_array_address, 0, 0, 0}) == UINT32_MAX,
                "WSAWaitForMultipleEvents succeeded before WSAStartup");
        require(invoke_import(winsock_module, wsa_startup_stub,
                              {0x0002, wsadata_address}) == 0,
                "WSAStartup did not accept Winsock 2.0");
        std::array<uint8_t, 0x190> wsadata{};
        for (size_t offset = 0; offset < wsadata.size(); offset += 16) {
            const size_t size = std::min<size_t>(16, wsadata.size() - offset);
            require(winsock_module.read_guest(
                        "ram", wsadata_address + offset, size,
                        wsadata.data() + offset),
                    "could not read WSAStartup's WSADATA output");
        }
        require(wsadata[0] == 2 && wsadata[1] == 0 && wsadata[2] == 2 &&
                    wsadata[3] == 2 &&
                    std::string(reinterpret_cast<const char*>(
                                    wsadata.data() + 4)) ==
                        "WinSock 2.0" &&
                    std::string(reinterpret_cast<const char*>(
                                    wsadata.data() + 0x105)) ==
                        "Running",
                "WSAStartup returned incorrect WSADATA fields");
        require(invoke_import(winsock_module, wsa_startup_stub,
                              {0x0001, wsadata_address}) == 0,
                "WSAStartup did not accept Winsock 1.0");
        require(winsock_module.read_guest("ram", wsadata_address, 4,
                                          wsadata.data()),
                "could not read negotiated Winsock 1.0 version");
        require(wsadata[0] == 1 && wsadata[1] == 0 && wsadata[2] == 2 &&
                    wsadata[3] == 2 &&
                    invoke_import(winsock_module, wsa_cleanup_stub, {}) == 0,
                "WSAStartup negotiated Winsock 1.0 incorrectly");
        require(invoke_import(winsock_module, wsa_startup_stub,
                              {0x0003, wsadata_address}) == 0,
                "WSAStartup did not negotiate a newer request down to 2.2");
        require(winsock_module.read_guest("ram", wsadata_address, 4,
                                          wsadata.data()),
                "could not read negotiated Winsock 2.2 version");
        require(wsadata[0] == 2 && wsadata[1] == 2 && wsadata[2] == 2 &&
                    wsadata[3] == 2 &&
                    invoke_import(winsock_module, wsa_cleanup_stub, {}) == 0,
                "WSAStartup negotiated Winsock 2.2 incorrectly");
        const uint32_t signaled_event = invoke_import(
            winsock_module, create_event_stub, {0, 1, 1, 0});
        const uint32_t unsignaled_event = invoke_import(
            winsock_module, create_event_stub, {0, 1, 0, 0});
        write_guest_u32(winsock_module, "ram", event_array_address,
                        signaled_event);
        require(invoke_import(winsock_module, wsa_wait_stub,
                              {1, event_array_address, 0, 0, 0}) == 0,
                "WSAWaitForMultipleEvents missed a signaled event");
        write_guest_u32(winsock_module, "ram", event_array_address,
                        unsignaled_event);
        require(invoke_import(winsock_module, wsa_wait_stub,
                              {1, event_array_address, 0, 0, 0}) == 0x102,
                "WSAWaitForMultipleEvents did not return its zero-timeout status");
        write_guest_u32(winsock_module, "ram", event_array_address, 0);
        require(invoke_import(winsock_module, wsa_wait_stub,
                              {1, event_array_address, 0, 0, 0}) == UINT32_MAX,
                "WSAWaitForMultipleEvents accepted an invalid event handle");
        require(invoke_import(winsock_module, wsa_startup_stub,
                              {0, wsadata_address}) == 10092 &&
                    invoke_import(winsock_module, wsa_startup_stub,
                                  {0x0002, 0}) == 10014,
                "WSAStartup did not return Winsock version or pointer errors");
        require(invoke_import(winsock_module, wsa_cleanup_stub, {}) == 0 &&
                    invoke_import(winsock_module, wsa_cleanup_stub, {}) ==
                        UINT32_MAX,
                "WSACleanup did not balance the WSAStartup reference count");
        require(invoke_import(winsock_module, wsa_wait_stub,
                              {1, event_array_address, 0, 0, 0}) == UINT32_MAX,
                "WSAWaitForMultipleEvents succeeded after WSACleanup");

        shift::runtime::RecompiledPcodeModule create_directory_module(argv[1]);
        const auto create_directory_image =
            create_directory_module.load_pe32_image(
                create_directory_fixture_path);
        require(create_directory_image.import_function_count == 81,
                "CreateDirectoryA fixture imports were not parsed");
        const uint32_t create_directory_api = read_guest_u32(
            create_directory_module, "ram",
            create_directory_image.image_base + 0x2c10);
        constexpr uint32_t create_directory_path_address = 0x00035000;
        const std::string create_directory_name =
            "create-directory-fixture-" + std::to_string(getpid());
        const std::filesystem::path create_directory_host_path =
            std::filesystem::current_path() / create_directory_name;
        std::filesystem::remove_all(create_directory_host_path);
        const std::string create_directory_guest_path =
            "C:\\" + create_directory_name;
        write_guest_bytes(
            create_directory_module, create_directory_path_address,
            reinterpret_cast<const uint8_t*>(create_directory_guest_path.c_str()),
            create_directory_guest_path.size() + 1);
        require(invoke_import(create_directory_module, create_directory_api,
                              {create_directory_path_address, 0}) == 1 &&
                    std::filesystem::is_directory(create_directory_host_path),
                "CreateDirectoryA did not create one guest-root directory");
        require(invoke_import(create_directory_module, create_directory_api,
                              {create_directory_path_address, 0}) == 0 &&
                    invoke_import(create_directory_module, 0xf0000240, {}) ==
                        183,
                "CreateDirectoryA did not report an existing directory");

        const std::string missing_parent_guest_path =
            "C:\\create-directory-missing-parent-" +
            std::to_string(getpid()) + "\\child";
        write_guest_bytes(
            create_directory_module, create_directory_path_address,
            reinterpret_cast<const uint8_t*>(missing_parent_guest_path.c_str()),
            missing_parent_guest_path.size() + 1);
        require(invoke_import(create_directory_module, create_directory_api,
                              {create_directory_path_address, 0}) == 0 &&
                    invoke_import(create_directory_module, 0xf0000240, {}) ==
                        3,
                "CreateDirectoryA recursively created missing parents");

        constexpr char escaped_create_directory_path[] = "C:\\..\\outside";
        write_guest_bytes(
            create_directory_module, create_directory_path_address,
            reinterpret_cast<const uint8_t*>(escaped_create_directory_path),
            sizeof(escaped_create_directory_path));
        require(invoke_import(create_directory_module, create_directory_api,
                              {create_directory_path_address, 0}) == 0 &&
                    invoke_import(create_directory_module, 0xf0000240, {}) ==
                        5,
                "CreateDirectoryA allowed a path outside the guest root");
        std::filesystem::remove_all(create_directory_host_path);

        write_guest_u32(module, "register", 0x10ac, 0x12345678);
        require(read_guest_u32(module, "register", 0x10ac) == 0x12345678,
                "P-code register bank did not cover extended x86 state");

        std::array<uint8_t, 4> value{};
        require(!module.read_guest("ram", 0x10, value.size(), value.data()) &&
                    module.last_error().find("reserved low memory") !=
                        std::string::npos,
                "guest RAM exposed a reserved low address to P-code reads");
        require(!module.write_guest("ram", 0xfffe, value.size(), value.data()) &&
                    module.last_error().find("reserved low memory") !=
                        std::string::npos,
                "guest RAM exposed the low-memory boundary to P-code writes");
        write_guest_bytes(module, 0x00010000, value.data(), value.size());
        require(module.read_guest("ram", 0x00010000, value.size(), value.data()),
                "guest RAM rejected the first available user address");
        require(module.read_guest("ram", image.image_base, 2, value.data()),
                "could not read mapped DOS header");
        require(value[0] == 'M' && value[1] == 'Z',
                "PE32 headers were not mapped at ImageBase");
        require(module.read_guest("ram", 0x00401000, value.size(), value.data()),
                "could not read mapped PE section");
        require(value == std::array<uint8_t, 4>{'P', '3', '2', '!'},
                "PE32 raw section bytes were not mapped at ImageBase + RVA");
        require(module.read_guest("ram", 0x00401200, value.size(), value.data()),
                "could not read PE section virtual tail");
        require(value == std::array<uint8_t, 4>{0, 0, 0, 0},
                "PE32 virtual section tail was not zero-filled");

        constexpr uint32_t retail_pool_object = 0x00402000;
        constexpr uint32_t retail_pool_stack = 0x00034000;
        shift::runtime::RecompiledPcodeModule retail_pool_module(argv[1]);
        (void)retail_pool_module.load_pe32_image(argv[4]);
        write_guest_u32(retail_pool_module, "ram", retail_pool_object, 0);
        write_guest_u32(retail_pool_module, "ram", retail_pool_object + 4,
                        0x10);
        write_guest_u32(retail_pool_module, "ram", retail_pool_object + 8,
                        0x10);
        write_guest_u32(retail_pool_module, "ram", retail_pool_object + 0x1c,
                        0);
        write_guest_u32(retail_pool_module, "register", 4,
                        retail_pool_object);
        write_guest_u32(retail_pool_module, "register", 0x10,
                        retail_pool_stack);
        require(retail_pool_module.call(0x00d8a600) == 0 &&
                    read_guest_u32(retail_pool_module, "ram",
                                   retail_pool_object) ==
                        retail_pool_object + 0x40 &&
                    read_guest_u32(retail_pool_module, "register", 4) ==
                        retail_pool_object &&
                    read_guest_u32(retail_pool_module, "register", 0x10) ==
                        retail_pool_stack,
                "retail pool initializer did not run the missing list helper "
                "with the expected frame and restore entry registers: " +
                    retail_pool_module.last_error());

        shift::runtime::RecompiledPcodeModule user32_module(argv[1]);
        const auto user32_image = user32_module.load_pe32_image(argv[7]);
        require(user32_image.import_module_count == 2 &&
                    user32_image.import_function_count == 9,
                "USER32/GDI32 fixture imports were not parsed");
        shift::runtime::RecompiledPcodeModule find_window_w_module(argv[1]);
        const auto find_window_w_image =
            find_window_w_module.load_pe32_image(find_window_w_fixture_path);
        require(find_window_w_image.import_function_count == 9,
                "FindWindowW fixture imports were not parsed");
        const uint32_t find_window_w = read_guest_u32(
            find_window_w_module, "ram",
            find_window_w_image.image_base + 0x2060);
        constexpr uint32_t find_window_class_name_address = 0x00033b00;
        constexpr uint32_t find_window_title_address = 0x00033b20;
        const std::array<uint8_t, 4> find_window_class_name = {
            'L', 0, 0, 0};
        const std::array<uint8_t, 2> empty_window_title = {0, 0};
        write_guest_bytes(find_window_w_module, find_window_class_name_address,
                          find_window_class_name.data(),
                          find_window_class_name.size());
        write_guest_bytes(find_window_w_module, find_window_title_address,
                          empty_window_title.data(),
                          empty_window_title.size());
        require(invoke_import(find_window_w_module, find_window_w,
                              {find_window_class_name_address, 0}) == 0 &&
                    invoke_import(find_window_w_module, find_window_w,
                                  {0, find_window_title_address}) == 0,
                "FindWindowW found a host window in the headless runtime");
        shift::runtime::RecompiledPcodeModule reg_open_key_ex_w_module(
            argv[1]);
        const auto reg_open_key_ex_w_image =
            reg_open_key_ex_w_module.load_pe32_image(
                reg_open_key_ex_w_fixture_path);
        require(reg_open_key_ex_w_image.import_module_count == 2 &&
                    reg_open_key_ex_w_image.import_function_count == 9,
                "ADVAPI32 registry fixture imports were not parsed");
        const uint32_t reg_open_key_ex_w = read_guest_u32(
            reg_open_key_ex_w_module, "ram",
            reg_open_key_ex_w_image.image_base + 0x2060);
        constexpr uint32_t registry_subkey_address = 0x00033c00;
        constexpr uint32_t registry_output_address = 0x00033d00;
        constexpr char16_t logitech_registry_subkey[] =
            u"Software\\Logitech\\Gaming Software";
        static_assert(sizeof(char16_t) == 2);
        write_guest_bytes(
            reg_open_key_ex_w_module, registry_subkey_address,
            reinterpret_cast<const uint8_t*>(logitech_registry_subkey),
            sizeof(logitech_registry_subkey));
        write_guest_u32(reg_open_key_ex_w_module, "ram",
                        registry_output_address, 0x11223344);
        require(invoke_import(
                    reg_open_key_ex_w_module, reg_open_key_ex_w,
                    {0x80000002, registry_subkey_address, 0, 0x20019,
                     registry_output_address}) == 2 &&
                    read_guest_u32(reg_open_key_ex_w_module, "ram",
                                   registry_output_address) == 0x11223344,
                "RegOpenKeyExW did not report the absent Logitech registry key");
        shift::runtime::RecompiledPcodeModule register_device_notification_w_module(
            argv[1]);
        const auto register_device_notification_w_image =
            register_device_notification_w_module.load_pe32_image(
                register_device_notification_w_fixture_path);
        require(register_device_notification_w_image.import_module_count == 2 &&
                    register_device_notification_w_image.import_function_count ==
                        9,
                "RegisterDeviceNotificationW fixture imports were not parsed");
        const uint32_t register_device_notification_w = read_guest_u32(
            register_device_notification_w_module, "ram",
            register_device_notification_w_image.image_base + 0x2060);
        constexpr uint32_t device_notification_filter_address = 0x00033e00;
        write_guest_u32(register_device_notification_w_module, "ram",
                        device_notification_filter_address, 32);
        write_guest_u32(register_device_notification_w_module, "ram",
                        device_notification_filter_address + 4, 5);
        write_guest_u32(register_device_notification_w_module, "ram",
                        device_notification_filter_address + 8, 0);
        require(invoke_import(
                    register_device_notification_w_module,
                    register_device_notification_w,
                    {0x00030008, device_notification_filter_address, 0}) ==
                    0x00030050,
                "RegisterDeviceNotificationW did not create a guest handle");
        write_guest_u32(register_device_notification_w_module, "ram",
                        device_notification_filter_address, 27);
        require(invoke_import(
                    register_device_notification_w_module,
                    register_device_notification_w,
                    {0x00030008, device_notification_filter_address, 0}) == 0 &&
                    invoke_import(
                        register_device_notification_w_module,
                        register_device_notification_w,
                        {0x00030008, 0xfffffff0, 0}) == 0,
                "RegisterDeviceNotificationW accepted an invalid filter");
        shift::runtime::RecompiledPcodeModule unregister_device_notification_module(
            argv[1]);
        const auto unregister_device_notification_image =
            unregister_device_notification_module.load_pe32_image(
                unregister_device_notification_fixture_path);
        const uint32_t unregister_device_notification = read_guest_u32(
            unregister_device_notification_module, "ram",
            unregister_device_notification_image.image_base + 0x2060);
        require(invoke_import(unregister_device_notification_module,
                              unregister_device_notification,
                              {0x00030050}) == 1 &&
                    invoke_import(unregister_device_notification_module,
                                  unregister_device_notification,
                                  {0x00030054}) == 0,
                "UnregisterDeviceNotification mishandled the guest handle");
        shift::runtime::RecompiledPcodeModule direct_input8_create_module(
            argv[1]);
        const auto direct_input8_create_image =
            direct_input8_create_module.load_pe32_image(
                direct_input8_create_fixture_path);
        require(direct_input8_create_image.import_module_count == 2 &&
                    direct_input8_create_image.import_function_count == 9,
                "DirectInput8Create fixture imports were not parsed");
        const uint32_t direct_input8_create = read_guest_u32(
            direct_input8_create_module, "ram",
            direct_input8_create_image.image_base + 0x2060);
        constexpr uint32_t direct_input8_iid_address = 0x00033e80;
        constexpr uint32_t direct_input8_output_address = 0x00033f00;
        const std::array<uint8_t, 16> direct_input8_iid{};
        write_guest_bytes(direct_input8_create_module,
                          direct_input8_iid_address,
                          direct_input8_iid.data(), direct_input8_iid.size());
        write_guest_u32(direct_input8_create_module, "ram",
                        direct_input8_output_address, 0x12345678);
        require(invoke_import(
                    direct_input8_create_module, direct_input8_create,
                    {direct_input8_create_image.image_base, 0x800,
                     direct_input8_iid_address, direct_input8_output_address,
                     0}) == 0x80004005 &&
                    read_guest_u32(direct_input8_create_module, "ram",
                                   direct_input8_output_address) == 0,
                "DirectInput8Create did not report the missing headless input provider");
        const uint32_t system_parameters_info = read_guest_u32(
            user32_module, "ram", user32_image.image_base + 0x2060);
        const uint32_t peek_message_w = read_guest_u32(
            user32_module, "ram", user32_image.image_base + 0x2064);
        const uint32_t get_desktop_window = read_guest_u32(
            user32_module, "ram", user32_image.image_base + 0x2068);
        const uint32_t load_icon_w = read_guest_u32(
            user32_module, "ram", user32_image.image_base + 0x206c);
        const uint32_t get_stock_object = read_guest_u32(
            user32_module, "ram", user32_image.image_base + 0x2120);
        const uint32_t register_class_ex = read_guest_u32(
            user32_module, "ram", user32_image.image_base + 0x2070);
        const uint32_t create_window_ex = read_guest_u32(
            user32_module, "ram", user32_image.image_base + 0x2074);
        const uint32_t clip_cursor = read_guest_u32(
            user32_module, "ram", user32_image.image_base + 0x2078);
        const uint32_t show_window = read_guest_u32(
            user32_module, "ram", user32_image.image_base + 0x207c);
        const uint32_t desktop_window =
            invoke_import(user32_module, get_desktop_window, {});
        require(desktop_window != 0 &&
                    invoke_import(user32_module, get_desktop_window, {}) ==
                        desktop_window,
                "GetDesktopWindow did not return a stable guest HWND");
        const uint32_t icon_handle = invoke_import(
            user32_module, load_icon_w, {user32_image.image_base, 0x65});
        require(icon_handle != 0 &&
                    invoke_import(user32_module, load_icon_w,
                                  {user32_image.image_base, 0x65}) ==
                        icon_handle,
                "LoadIconW did not return a stable guest icon handle");
        const uint32_t stock_object =
            invoke_import(user32_module, get_stock_object, {5});
        require(stock_object == 0x00030024 &&
                    invoke_import(user32_module, get_stock_object, {5}) ==
                        stock_object &&
                    invoke_import(user32_module, get_stock_object, {18}) == 0,
                "GetStockObject did not preserve guest stock-handle semantics");
        constexpr uint32_t window_class_address = 0x00033800;
        constexpr uint32_t window_class_name_address = 0x00033900;
        constexpr uint32_t window_title_address = 0x00033920;
        write_guest_u32(user32_module, "ram", window_class_address, 48);
        write_guest_u32(user32_module, "ram", window_class_address + 8,
                        user32_image.image_base + 0x1000);
        write_guest_u32(user32_module, "ram", window_class_address + 20,
                        user32_image.image_base);
        write_guest_u32(user32_module, "ram", window_class_address + 32,
                        stock_object);
        write_guest_u32(user32_module, "ram", window_class_address + 40,
                        window_class_name_address);
        const std::array<uint8_t, 2> class_name = {'S', 0};
        write_guest_bytes(user32_module, window_class_name_address,
                          class_name.data(), class_name.size());
        const std::array<uint8_t, 2> empty_title = {0, 0};
        write_guest_bytes(user32_module, window_title_address,
                          empty_title.data(), empty_title.size());
        require(invoke_import(user32_module, register_class_ex,
                              {window_class_address}) == 1,
                "RegisterClassExW rejected a valid guest class");
        write_guest_u32(user32_module, "ram", window_class_address, 40);
        require(invoke_import(user32_module, register_class_ex,
                              {window_class_address}) == 0,
                "RegisterClassExW accepted a malformed class size");
        const std::vector<uint32_t> create_window_arguments = {
            8, window_class_name_address, window_title_address, 0x80000000,
            0, 0, 640, 480, desktop_window, 0, user32_image.image_base, 0};
        const uint32_t window = invoke_import(
            user32_module, create_window_ex, create_window_arguments);
        require(window != 0 &&
                    invoke_import(user32_module, create_window_ex,
                                  create_window_arguments) == window,
                "CreateWindowExW did not return a stable guest HWND");
        require(invoke_import(user32_module, clip_cursor, {0x00033a00}) == 1 &&
                    invoke_import(user32_module, clip_cursor, {0}) == 1 &&
                    invoke_import(user32_module, clip_cursor, {0x00000001}) ==
                        0,
                "ClipCursor did not validate and accept guest RECT input");
        require(invoke_import(user32_module, show_window, {window, 5}) == 0 &&
                    invoke_import(user32_module, show_window, {window, 5}) == 1 &&
                    invoke_import(user32_module, show_window, {window, 0}) == 1 &&
                    invoke_import(user32_module, show_window, {window, 5}) == 0,
                "ShowWindow did not return and update guest visibility state");
        constexpr uint32_t peek_message_output = 0x00032f00;
        std::array<uint8_t, 28> initial_message{};
        initial_message.fill(0xa5);
        write_guest_bytes(user32_module, peek_message_output,
                          initial_message.data(), initial_message.size());
        require(invoke_import(user32_module, peek_message_w,
                              {peek_message_output, 0, 0, 0, 0}) == 0,
                "PeekMessageW should report an empty startup queue");
        std::array<uint8_t, 28> message_after_peek{};
        require(user32_module.read_guest("ram", peek_message_output, 16,
                                         message_after_peek.data()) &&
                    user32_module.read_guest(
                        "ram", peek_message_output + 16, 12,
                        message_after_peek.data() + 16) &&
                    message_after_peek == initial_message,
                "PeekMessageW modified MSG when no queued message existed");
        constexpr uint32_t system_parameters_buffer = 0x00033000;
        const std::array<std::array<uint32_t, 2>, 5> accessibility_apis =
            {{{0x0032, 0x0033}, {0x0034, 0x0035}, {0x0036, 0x0037},
              {0x003a, 0x003b}, {0x0042, 0x0043}}};
        const std::array<size_t, 5> accessibility_sizes = {24, 8, 28, 8, 12};
        const auto read_guest_range = [&](uint32_t address, size_t size) {
            std::vector<uint8_t> result(size);
            for (size_t offset = 0; offset < size; offset += 16) {
                const size_t chunk = std::min<size_t>(16, size - offset);
                require(user32_module.read_guest(
                            "ram", address + offset, chunk,
                            result.data() + offset),
                        "could not read accessibility settings buffer");
            }
            return result;
        };
        for (size_t index = 0; index < accessibility_apis.size(); ++index) {
            const size_t size = accessibility_sizes[index];
            std::vector<uint8_t> initial(size, 0);
            initial[0] = static_cast<uint8_t>(size);
            initial[1] = static_cast<uint8_t>(size >> 8);
            for (size_t byte = 4; byte < size; ++byte)
                initial[byte] = static_cast<uint8_t>(byte * 13 + index);
            write_guest_bytes(user32_module, system_parameters_buffer,
                              initial.data(), initial.size());
            require(invoke_import(user32_module, system_parameters_info,
                                  {accessibility_apis[index][0],
                                   static_cast<uint32_t>(size),
                                   system_parameters_buffer, 0}) == 1,
                    "SystemParametersInfoA GET action failed");
            std::vector<uint8_t> defaults(size, 0);
            defaults[0] = static_cast<uint8_t>(size);
            defaults[1] = static_cast<uint8_t>(size >> 8);
            require(read_guest_range(system_parameters_buffer, size) == defaults,
                    "SystemParametersInfoA GET did not return zero defaults");

            write_guest_bytes(user32_module, system_parameters_buffer,
                              initial.data(), initial.size());
            require(invoke_import(user32_module, system_parameters_info,
                                  {accessibility_apis[index][1],
                                   static_cast<uint32_t>(size),
                                   system_parameters_buffer, 0}) == 1,
                    "SystemParametersInfoA SET action failed");
            require(invoke_import(user32_module, system_parameters_info,
                                  {accessibility_apis[index][0],
                                   static_cast<uint32_t>(size),
                                   system_parameters_buffer, 0}) == 1 &&
                        read_guest_range(system_parameters_buffer, size) ==
                            initial,
                    "SystemParametersInfoA did not preserve GET/SET state");
        }
        require(invoke_import(user32_module, system_parameters_info,
                              {0x0043, 12, system_parameters_buffer, 1}) == 0 &&
                    invoke_import(user32_module, system_parameters_info,
                                  {0x0042, 8, system_parameters_buffer, 0}) == 0 &&
                    invoke_import(user32_module, system_parameters_info,
                                  {0xffff, 0, system_parameters_buffer, 0}) == 0,
                "SystemParametersInfoA accepted unsupported or malformed input");

        shift::runtime::RecompiledPcodeModule d3d9_module(argv[1]);
        const auto d3d9_image = d3d9_module.load_pe32_image(argv[8]);
        require(d3d9_image.import_module_count == 3 &&
                    d3d9_image.import_function_count == 11,
                "D3D9 fixture imports were not parsed");
        const uint32_t direct3d_create9 = read_guest_u32(
            d3d9_module, "ram", d3d9_image.image_base + 0x2060);
        const uint32_t d3dperf_end_event = read_guest_u32(
            d3d9_module, "ram", d3d9_image.image_base + 0x2064);
        const uint32_t d3dperf_begin_event = read_guest_u32(
            d3d9_module, "ram", d3d9_image.image_base + 0x2068);
        const uint32_t sh_get_folder_path = read_guest_u32(
            d3d9_module, "ram", d3d9_image.image_base + 0x2180);
        const uint32_t sh_create_directory = read_guest_u32(
            d3d9_module, "ram", d3d9_image.image_base + 0x2184);
        constexpr uint32_t folder_path_address = 0x00402c30;
        require(invoke_import(d3d9_module, sh_get_folder_path,
                              {0, 0x8005, 0, 0, folder_path_address}) == 0,
                "SHGetFolderPathA did not create the Documents special folder");
        std::vector<uint8_t> folder_path_bytes(260);
        for (size_t offset = 0; offset < folder_path_bytes.size(); offset += 16) {
            const size_t chunk = std::min<size_t>(16,
                                                   folder_path_bytes.size() - offset);
            require(d3d9_module.read_guest("ram", folder_path_address + offset,
                                           chunk, folder_path_bytes.data() + offset),
                    "could not read SHGetFolderPathA output");
        }
        const std::string folder_path(
            folder_path_bytes.begin(),
            std::find(folder_path_bytes.begin(), folder_path_bytes.end(), 0));
        require(folder_path == "C:\\Documents and Settings\\SHIFT\\My Documents" &&
                    std::filesystem::is_directory(
                        std::filesystem::current_path() /
                        "Documents and Settings/SHIFT/My Documents"),
                "SHGetFolderPathA returned an unexpected path or skipped creation");
        constexpr uint32_t sh_create_directory_path_address = 0x00035000;
        constexpr char create_directory_path[] =
            "C:\\Documents and Settings\\SHIFT\\My Documents\\SHCreateDirectoryExFixture";
        write_guest_bytes(
            d3d9_module, sh_create_directory_path_address,
            reinterpret_cast<const uint8_t*>(create_directory_path),
            sizeof(create_directory_path));
        const std::filesystem::path expected_created_directory =
            std::filesystem::current_path() /
            "Documents and Settings/SHIFT/My Documents/SHCreateDirectoryExFixture";
        require(invoke_import(d3d9_module, sh_create_directory,
                              {0, sh_create_directory_path_address, 0}) == 0 &&
                    std::filesystem::is_directory(expected_created_directory) &&
                    invoke_import(d3d9_module, sh_create_directory,
                                  {0, sh_create_directory_path_address, 0}) == 183,
                "SHCreateDirectoryExA did not create directories or report existing paths");
        constexpr char relative_create_directory_path[] = "relative-path";
        write_guest_bytes(
            d3d9_module, sh_create_directory_path_address,
            reinterpret_cast<const uint8_t*>(relative_create_directory_path),
            sizeof(relative_create_directory_path));
        require(invoke_import(d3d9_module, sh_create_directory,
                              {0, sh_create_directory_path_address, 0}) == 161,
                "SHCreateDirectoryExA accepted a relative path");
        constexpr char escaped_sh_create_directory_path[] =
            "C:\\..\\outside-guest-root";
        write_guest_bytes(
            d3d9_module, sh_create_directory_path_address,
            reinterpret_cast<const uint8_t*>(escaped_sh_create_directory_path),
            sizeof(escaped_sh_create_directory_path));
        require(invoke_import(d3d9_module, sh_create_directory,
                              {0, sh_create_directory_path_address, 0}) == 5,
                "SHCreateDirectoryExA allowed creation outside the guest root");
        std::filesystem::remove_all(std::filesystem::current_path() /
                                    "Documents and Settings");
        require(invoke_import(d3d9_module, sh_get_folder_path,
                              {0, 0x8004, 0, 0, folder_path_address}) ==
                        0x80070057 &&
                    read_guest_u32(d3d9_module, "ram", folder_path_address) == 0,
                "SHGetFolderPathA did not reject unsupported CSIDL values");
        require(d3d9_module.set_guest_display_mode(1366, 768, 60, 22),
                "could not configure the guest D3D9 display mode");
        const uint32_t d3d9_interface =
            invoke_import(d3d9_module, direct3d_create9, {32});
        require(d3d9_interface != 0 &&
                    invoke_import(d3d9_module, direct3d_create9, {31}) == 0,
                "Direct3DCreate9 did not validate the observed SDK version");
        const uint32_t d3d9_vtable =
            read_guest_u32(d3d9_module, "ram", d3d9_interface);
        require(d3d9_vtable != 0 &&
                    invoke_import(d3d9_module, d3dperf_begin_event,
                                  {0x44, 0x00033000}) == 0 &&
                    invoke_import(d3d9_module, d3dperf_end_event, {}) == 0,
                "D3D9 interface or performance markers were not initialized");
        const uint32_t add_ref =
            read_guest_u32(d3d9_module, "ram", d3d9_vtable + 4);
        const uint32_t release =
            read_guest_u32(d3d9_module, "ram", d3d9_vtable + 8);
        const uint32_t get_adapter_count =
            read_guest_u32(d3d9_module, "ram", d3d9_vtable + 4 * 4);
        const uint32_t get_adapter_mode_count =
            read_guest_u32(d3d9_module, "ram", d3d9_vtable + 6 * 4);
        const uint32_t enum_adapter_modes =
            read_guest_u32(d3d9_module, "ram", d3d9_vtable + 7 * 4);
        const uint32_t get_adapter_display_mode =
            read_guest_u32(d3d9_module, "ram", d3d9_vtable + 8 * 4);
        const uint32_t check_device_type =
            read_guest_u32(d3d9_module, "ram", d3d9_vtable + 9 * 4);
        const uint32_t display_mode_address = 0x00402c10;
        constexpr uint32_t enumerated_mode_address = 0x00402c50;
        require(invoke_import(d3d9_module, get_adapter_count,
                              {d3d9_interface}) == 1 &&
                    invoke_import(d3d9_module, get_adapter_mode_count,
                                  {d3d9_interface, 0, 22}) == 1 &&
                    invoke_import(d3d9_module, get_adapter_mode_count,
                                  {d3d9_interface, 0, 23}) == 0 &&
                    invoke_import(d3d9_module, get_adapter_mode_count,
                                  {d3d9_interface, 1, 22}) == 0 &&
                    invoke_import(d3d9_module, get_adapter_display_mode,
                              {d3d9_interface, 0, display_mode_address}) == 0 &&
                    read_guest_u32(d3d9_module, "ram", display_mode_address) ==
                        1366 &&
                    read_guest_u32(d3d9_module, "ram", display_mode_address + 4) ==
                        768 &&
                    read_guest_u32(d3d9_module, "ram", display_mode_address + 8) ==
                        60 &&
                    read_guest_u32(d3d9_module, "ram", display_mode_address + 12) ==
                        22,
                "GetAdapterDisplayMode did not fill the configured D3DDISPLAYMODE");
        require(invoke_import(d3d9_module, enum_adapter_modes,
                              {d3d9_interface, 0, 22, 0,
                               enumerated_mode_address}) == 0 &&
                    read_guest_u32(d3d9_module, "ram",
                                   enumerated_mode_address) == 1366 &&
                    read_guest_u32(d3d9_module, "ram",
                                   enumerated_mode_address + 4) == 768 &&
                    read_guest_u32(d3d9_module, "ram",
                                   enumerated_mode_address + 8) == 60 &&
                    read_guest_u32(d3d9_module, "ram",
                                   enumerated_mode_address + 12) == 22,
                "EnumAdapterModes did not return the configured guest mode");
        constexpr uint32_t enumerated_mode_sentinel = 0x6b6b6b6b;
        write_guest_u32(d3d9_module, "ram", enumerated_mode_address,
                        enumerated_mode_sentinel);
        require(invoke_import(d3d9_module, enum_adapter_modes,
                              {d3d9_interface, 0, 23, 0,
                               enumerated_mode_address}) == 0x8876086a &&
                    read_guest_u32(d3d9_module, "ram",
                                   enumerated_mode_address) ==
                        enumerated_mode_sentinel &&
                    invoke_import(d3d9_module, enum_adapter_modes,
                                  {d3d9_interface, 0, 22, 1,
                                   enumerated_mode_address}) == 0x8876086a &&
                    invoke_import(d3d9_module, enum_adapter_modes,
                                  {d3d9_interface, 1, 22, 0,
                                   enumerated_mode_address}) == 0x8876086c &&
                    invoke_import(d3d9_module, enum_adapter_modes,
                                  {d3d9_interface, 0, 22, 0, 0}) ==
                        0x8876086c,
                "EnumAdapterModes did not reject unavailable modes and invalid arguments");
        require(invoke_import(d3d9_module, check_device_type,
                              {d3d9_interface, 0, 1, 22, 21, 0}) ==
                    0x8876086a,
                "CheckDeviceType claimed support without a Vulkan surface");
        require(invoke_import(d3d9_module, get_adapter_display_mode,
                              {d3d9_interface, 1, display_mode_address}) ==
                        0x8876086c &&
                    invoke_import(d3d9_module, get_adapter_display_mode,
                                  {d3d9_interface, 0, 0}) == 0x8876086c,
                "GetAdapterDisplayMode did not reject invalid adapter/output");
        const uint32_t get_device_caps =
            read_guest_u32(d3d9_module, "ram", d3d9_vtable + 14 * 4);
        const uint32_t check_device_format =
            read_guest_u32(d3d9_module, "ram", d3d9_vtable + 10 * 4);
        const uint32_t check_device_multisample_type =
            read_guest_u32(d3d9_module, "ram", d3d9_vtable + 11 * 4);
        constexpr uint32_t caps_address = 0x00402c30;
        constexpr uint32_t caps_sentinel = 0xa5a5a5a5;
        write_guest_u32(d3d9_module, "ram", caps_address, caps_sentinel);
        require(invoke_import(d3d9_module, get_device_caps,
                              {d3d9_interface, 0, 1, caps_address}) ==
                        0x8876086a,
                "GetDeviceCaps did not report the unavailable D3D9 backend");
        require(read_guest_u32(d3d9_module, "ram", caps_address) ==
                    caps_sentinel,
                "GetDeviceCaps wrote fabricated capabilities on failure");
        require(invoke_import(d3d9_module, get_device_caps,
                              {d3d9_interface, 1, 1, caps_address}) ==
                        0x8876086c &&
                    invoke_import(d3d9_module, get_device_caps,
                                  {d3d9_interface, 0, 1, 0}) == 0x8876086c &&
                    invoke_import(d3d9_module, get_device_caps,
                                  {d3d9_interface, 0, 1, 0xffffff00}) ==
                        0x8876086c,
                "GetDeviceCaps did not reject invalid adapter/output");
        const uint32_t get_adapter_identifier =
            read_guest_u32(d3d9_module, "ram", d3d9_vtable + 5 * 4);
        constexpr uint32_t identifier_sentinel = 0x5a5a5a5a;
        write_guest_u32(d3d9_module, "ram", caps_address,
                        identifier_sentinel);
        require(invoke_import(d3d9_module, get_adapter_identifier,
                              {d3d9_interface, 0, 0, caps_address}) ==
                        0x8876086a &&
                    read_guest_u32(d3d9_module, "ram", caps_address) ==
                        identifier_sentinel,
                "GetAdapterIdentifier fabricated unavailable adapter data");
        require(invoke_import(d3d9_module, get_adapter_identifier,
                              {d3d9_interface, 1, 0, caps_address}) ==
                        0x8876086c &&
                    invoke_import(d3d9_module, get_adapter_identifier,
                                  {d3d9_interface, 0, 1, caps_address}) ==
                        0x8876086c &&
                    invoke_import(d3d9_module, get_adapter_identifier,
                                  {d3d9_interface, 0, 0, 0}) == 0x8876086c,
                "GetAdapterIdentifier did not reject invalid arguments");
        shift::runtime::RecompiledPcodeModule d3d9_provider_module(argv[1]);
        const auto provider_image =
            d3d9_provider_module.load_pe32_image(argv[8]);
        const uint32_t provider_create9 = read_guest_u32(
            d3d9_provider_module, "ram", provider_image.image_base + 0x2060);
        const uint32_t provider_d3dx_create_effect = read_guest_u32(
            d3d9_provider_module, "ram", provider_image.image_base + 0x2260);
        const uint32_t provider_d3dx_effect_compiler_from_file =
            read_guest_u32(d3d9_provider_module, "ram",
                           provider_image.image_base + 0x2264);
        const uint32_t provider_d3dx_create_line = read_guest_u32(
            d3d9_provider_module, "ram", provider_image.image_base + 0x2268);
        const uint32_t provider_d3dx_get_image_info = read_guest_u32(
            d3d9_provider_module, "ram", provider_image.image_base + 0x226c);
        const uint32_t provider_d3dx_create_texture_from_memory_ex =
            read_guest_u32(d3d9_provider_module, "ram",
                           provider_image.image_base + 0x2270);
        const uint32_t provider_d3dx_create_buffer = read_guest_u32(
            d3d9_provider_module, "ram", provider_image.image_base + 0x2274);
        shift::runtime::RecompiledGuestD3d9AdapterInfo adapter_info{};
        for (size_t index = 0; index < adapter_info.caps.size(); ++index) {
            adapter_info.caps[index] = 100 + static_cast<uint32_t>(index);
        }
        adapter_info.caps[0] = 1;
        adapter_info.vendor_id = 0x10de;
        adapter_info.device_id = 0x1234;
        adapter_info.description = "fixture adapter";
        adapter_info.supports_bgra8_surface = true;
        adapter_info.supports_bgra8_texture = true;
        adapter_info.supports_d24s8_depth_stencil = true;
        adapter_info.bgra8_sample_count_mask = 1 | 2 | 4;
        adapter_info.d24s8_sample_count_mask = 1 | 2;
        D3d9BackendFixture d3d9_backend_fixture{};
        adapter_info.backend_context = &d3d9_backend_fixture;
        adapter_info.create_device = &create_d3d9_fixture_device;
        adapter_info.create_vertex_buffer =
            &create_d3d9_fixture_vertex_buffer;
        adapter_info.update_vertex_buffer =
            &update_d3d9_fixture_vertex_buffer;
        adapter_info.release_vertex_buffer =
            &release_d3d9_fixture_vertex_buffer;
        adapter_info.create_index_buffer =
            &create_d3d9_fixture_index_buffer;
        adapter_info.update_index_buffer =
            &update_d3d9_fixture_index_buffer;
        adapter_info.release_index_buffer =
            &release_d3d9_fixture_index_buffer;
        adapter_info.clear = &clear_d3d9_fixture;
        adapter_info.present = &present_d3d9_fixture;
        require(d3d9_provider_module.set_guest_d3d9_adapter_info(adapter_info),
                "could not configure the fixture Vulkan adapter snapshot");
        const uint32_t provider_interface =
            invoke_import(d3d9_provider_module, provider_create9, {32});
        const uint32_t provider_vtable = read_guest_u32(
            d3d9_provider_module, "ram", provider_interface);
        const uint32_t provider_get_caps = read_guest_u32(
            d3d9_provider_module, "ram", provider_vtable + 14 * 4);
        const uint32_t provider_get_identifier = read_guest_u32(
            d3d9_provider_module, "ram", provider_vtable + 5 * 4);
        const uint32_t provider_check_device_type = read_guest_u32(
            d3d9_provider_module, "ram", provider_vtable + 9 * 4);
        const uint32_t provider_check_device_format = read_guest_u32(
            d3d9_provider_module, "ram", provider_vtable + 10 * 4);
        const uint32_t provider_check_depth_stencil_match = read_guest_u32(
            d3d9_provider_module, "ram", provider_vtable + 12 * 4);
        const uint32_t provider_check_multisample = read_guest_u32(
            d3d9_provider_module, "ram", provider_vtable + 11 * 4);
        const uint32_t provider_create_device = read_guest_u32(
            d3d9_provider_module, "ram", provider_vtable + 16 * 4);
        constexpr uint32_t provider_caps_address = 0x00403000;
        require(invoke_import(d3d9_provider_module, provider_get_caps,
                              {provider_interface, 0, 1,
                               provider_caps_address}) == 0,
                "GetDeviceCaps did not return the configured adapter snapshot");
        for (size_t index = 0; index < adapter_info.caps.size(); ++index) {
            require(read_guest_u32(d3d9_provider_module, "ram",
                                   provider_caps_address + index * 4) ==
                        adapter_info.caps[index],
                    "GetDeviceCaps changed a D3DCAPS9 word");
        }
        require(invoke_import(d3d9_provider_module, provider_get_caps,
                              {provider_interface, 0, 2,
                               provider_caps_address}) == 0x88760870,
                "GetDeviceCaps accepted an unsupported device type");
        require(invoke_import(d3d9_provider_module,
                              provider_check_device_type,
                              {provider_interface, 0, 1, 22, 21, 0}) == 0 &&
                    invoke_import(d3d9_provider_module,
                                  provider_check_device_type,
                                  {provider_interface, 0, 1, 22, 23, 0}) ==
                        0x8876086a,
                "CheckDeviceType did not honor the Vulkan surface format");
        require(invoke_import(d3d9_provider_module,
                              provider_check_device_format,
                              {provider_interface, 0, 1, 22, 0, 3, 21}) == 0 &&
                    invoke_import(d3d9_provider_module,
                                  provider_check_device_format,
                                  {provider_interface, 0, 1, 22, 5, 3, 21}) ==
                        0 &&
                    invoke_import(d3d9_provider_module,
                                  provider_check_device_format,
                                  {provider_interface, 0, 1, 22, 2, 3, 75}) ==
                        0 &&
                    invoke_import(d3d9_provider_module,
                                  provider_check_device_format,
                                  {provider_interface, 0, 1, 22, 2, 3, 21}) ==
                        0x8876086a &&
                    invoke_import(d3d9_provider_module,
                                  provider_check_device_format,
                                  {provider_interface, 0, 1, 22, 0, 3, 23}) ==
                        0x8876086a,
                "CheckDeviceFormat did not expose only Vulkan-backed formats");
        require(invoke_import(
                    d3d9_provider_module,
                    provider_check_depth_stencil_match,
                    {provider_interface, 0, 1, 22, 21, 75}) == 0 &&
                    invoke_import(
                        d3d9_provider_module,
                        provider_check_depth_stencil_match,
                        {provider_interface, 0, 1, 22, 21, 77}) ==
                        0x8876086a,
                "CheckDepthStencilMatch did not honor Vulkan-backed formats");
        constexpr uint32_t provider_quality_levels = 0x00402c80;
        require(invoke_import(d3d9_provider_module,
                              provider_check_multisample,
                              {provider_interface, 0, 1, 22, 1, 2,
                               provider_quality_levels}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   provider_quality_levels) == 1 &&
                    invoke_import(d3d9_provider_module,
                                  provider_check_multisample,
                                  {provider_interface, 0, 1, 75, 1, 2, 0}) == 0 &&
                    invoke_import(d3d9_provider_module,
                                  provider_check_multisample,
                                  {provider_interface, 0, 1, 75, 1, 4, 0}) ==
                        0x8876086a,
                "CheckDeviceMultiSampleType did not honor Vulkan sample support");
        constexpr uint32_t provider_identifier_address = 0x00404000;
        require(invoke_import(d3d9_provider_module, provider_get_identifier,
                              {provider_interface, 0, 0,
                               provider_identifier_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   provider_identifier_address + 1064) ==
                        adapter_info.vendor_id &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   provider_identifier_address + 1068) ==
                        adapter_info.device_id,
                "GetAdapterIdentifier did not return Vulkan adapter identity");
        std::array<uint8_t, 16> provider_description{};
        require(d3d9_provider_module.read_guest(
                    "ram", provider_identifier_address + 512,
                    provider_description.size(), provider_description.data()) &&
                    std::string(provider_description.begin(),
                                std::find(provider_description.begin(),
                                          provider_description.end(), 0)) ==
                        adapter_info.description,
                "GetAdapterIdentifier did not return its adapter description");
        constexpr uint32_t presentation_parameters_address = 0x00405000;
        constexpr uint32_t created_device_output_address = 0x00405100;
        const std::array<uint32_t, 14> retail_presentation_parameters = {
            800, 600, 21, 1, 2, 0, 1, 0x00030008, 1, 1, 75, 0, 0,
            0x80000000};
        for (size_t index = 0;
             index < retail_presentation_parameters.size(); ++index) {
            write_guest_u32(d3d9_provider_module, "ram",
                            presentation_parameters_address + index * 4,
                            retail_presentation_parameters[index]);
        }
        require(invoke_import(d3d9_provider_module, provider_create_device,
                              {provider_interface, 0, 1, 0x00030008, 0x50,
                               presentation_parameters_address,
                               created_device_output_address}) == 0 &&
                    d3d9_backend_fixture.called &&
                    d3d9_backend_fixture.focus_window == 0x00030008 &&
                    d3d9_backend_fixture.behavior_flags == 0x50 &&
                    d3d9_backend_fixture.parameters.back_buffer_width == 800 &&
                    d3d9_backend_fixture.parameters.back_buffer_height == 600 &&
                    d3d9_backend_fixture.parameters.multisample_type == 2 &&
                    d3d9_backend_fixture.parameters.auto_depth_stencil_format ==
                        75,
                "CreateDevice did not pass retail parameters to the Vulkan host");
        const auto create_device_snapshot =
            d3d9_provider_module.guest_scheduler_snapshot();
        require(create_device_snapshot.d3d9_create_device_attempted &&
                    create_device_snapshot.d3d9_create_device_callback_called &&
                    create_device_snapshot.d3d9_create_device_hresult == 0 &&
                    create_device_snapshot.d3d9_create_device_rejection.empty(),
                "CreateDevice result diagnostics did not record success");
        const uint32_t created_device = read_guest_u32(
            d3d9_provider_module, "ram", created_device_output_address);
        const uint32_t created_device_vtable = read_guest_u32(
            d3d9_provider_module, "ram", created_device);
        const uint32_t provider_device_release = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 2 * 4);
        const uint32_t device_set_vertex_declaration = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 87 * 4);
        const uint32_t device_get_vertex_declaration = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 88 * 4);
        const uint32_t device_set_stream_source = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 100 * 4);
        const uint32_t device_get_stream_source = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 101 * 4);
        const uint32_t device_set_indices = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 104 * 4);
        const uint32_t device_get_indices = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 105 * 4);
        const uint32_t device_get_texture = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 64 * 4);
        const uint32_t device_set_texture = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 65 * 4);
        const uint32_t create_texture = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 23 * 4);
        const uint32_t create_vertex_buffer = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 26 * 4);
        const uint32_t create_index_buffer = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 27 * 4);
        const uint32_t create_vertex_declaration = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 86 * 4);
        constexpr uint32_t managed_texture_output_address = 0x00405120;
        require(invoke_import(
                    d3d9_provider_module, create_texture,
                    {created_device, 2, 2, 1, 0, 21, 1,
                     managed_texture_output_address, 0}) == 0,
                "CreateTexture rejected a small managed A8R8G8B8 texture");
        const uint32_t managed_texture = read_guest_u32(
            d3d9_provider_module, "ram", managed_texture_output_address);
        const uint32_t managed_texture_vtable = read_guest_u32(
            d3d9_provider_module, "ram", managed_texture);
        const uint32_t managed_texture_release = read_guest_u32(
            d3d9_provider_module, "ram", managed_texture_vtable + 2 * 4);
        const uint32_t managed_texture_get_level_count = read_guest_u32(
            d3d9_provider_module, "ram", managed_texture_vtable + 13 * 4);
        const uint32_t managed_texture_get_level_desc = read_guest_u32(
            d3d9_provider_module, "ram", managed_texture_vtable + 17 * 4);
        const uint32_t managed_texture_lock_rect = read_guest_u32(
            d3d9_provider_module, "ram", managed_texture_vtable + 19 * 4);
        const uint32_t managed_texture_unlock_rect = read_guest_u32(
            d3d9_provider_module, "ram", managed_texture_vtable + 20 * 4);
        constexpr uint32_t managed_texture_desc_address = 0x00405140;
        constexpr uint32_t managed_texture_locked_rect_address = 0x00405160;
        require(managed_texture != 0 &&
                    invoke_import(d3d9_provider_module,
                                  managed_texture_get_level_count,
                                  {managed_texture}) == 1 &&
                    invoke_import(d3d9_provider_module,
                                  managed_texture_get_level_desc,
                                  {managed_texture, 0,
                                   managed_texture_desc_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   managed_texture_desc_address) == 21 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   managed_texture_desc_address + 12) == 1 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   managed_texture_desc_address + 24) == 2 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   managed_texture_desc_address + 28) == 2 &&
                    invoke_import(d3d9_provider_module,
                                  managed_texture_lock_rect,
                                  {managed_texture, 0,
                                   managed_texture_locked_rect_address, 0,
                                   0}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   managed_texture_locked_rect_address) == 8,
                "managed texture level description or lock data was incorrect");
        const uint32_t managed_texture_pixels = read_guest_u32(
            d3d9_provider_module, "ram",
            managed_texture_locked_rect_address + 4);
        write_guest_u32(d3d9_provider_module, "ram",
                        managed_texture_pixels, 0xff204060);
        require(invoke_import(d3d9_provider_module,
                              managed_texture_unlock_rect,
                              {managed_texture, 0}) == 0,
                "managed texture unlock failed");
        constexpr uint32_t device_texture_output_address = 0x00405318;
        require(invoke_import(d3d9_provider_module, device_set_texture,
                              {created_device, 0, managed_texture}) == 0 &&
                    invoke_import(d3d9_provider_module, device_set_texture,
                                  {created_device, 0, managed_texture}) == 0 &&
                    invoke_import(d3d9_provider_module, device_get_texture,
                                  {created_device, 0,
                                   device_texture_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   device_texture_output_address) == managed_texture &&
                    invoke_import(d3d9_provider_module, managed_texture_release,
                                  {managed_texture}) == 2 &&
                    invoke_import(d3d9_provider_module, managed_texture_release,
                                  {managed_texture}) == 1,
                "SetTexture/GetTexture failed to retain the bound texture");
        require(invoke_import(d3d9_provider_module, device_get_texture,
                              {created_device, 0,
                               device_texture_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   device_texture_output_address) == managed_texture &&
                    invoke_import(d3d9_provider_module, managed_texture_release,
                                  {managed_texture}) == 1 &&
                    invoke_import(d3d9_provider_module, device_set_texture,
                                  {created_device, 0, 0}) == 0 &&
                    invoke_import(d3d9_provider_module, device_get_texture,
                                  {created_device, 0,
                                   device_texture_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   device_texture_output_address) == 0,
                "SetTexture null unbind did not release and clear the texture");
        require(invoke_import(d3d9_provider_module, device_set_texture,
                              {created_device, 260, 0}) == 0x8876086c,
                "SetTexture accepted stage 260");
        constexpr uint32_t vertex_buffer_output_address = 0x00405190;
        require(invoke_import(
                    d3d9_provider_module, create_vertex_buffer,
                    {created_device, 24, 0, 0, 1,
                     vertex_buffer_output_address, 0}) == 0 &&
                    d3d9_backend_fixture.vertex_buffer_create_called &&
                    d3d9_backend_fixture.vertex_buffer_device == created_device &&
                    d3d9_backend_fixture.vertex_buffer_size == 24 &&
                    d3d9_backend_fixture.vertex_buffer_usage == 0 &&
                    d3d9_backend_fixture.vertex_buffer_fvf == 0 &&
                    d3d9_backend_fixture.vertex_buffer_pool == 1,
                "CreateVertexBuffer did not accept a static managed buffer");
        const uint32_t vertex_buffer = read_guest_u32(
            d3d9_provider_module, "ram", vertex_buffer_output_address);
        const uint32_t vertex_buffer_vtable = read_guest_u32(
            d3d9_provider_module, "ram", vertex_buffer);
        const uint32_t vertex_buffer_release = read_guest_u32(
            d3d9_provider_module, "ram", vertex_buffer_vtable + 2 * 4);
        const uint32_t vertex_buffer_lock = read_guest_u32(
            d3d9_provider_module, "ram", vertex_buffer_vtable + 11 * 4);
        const uint32_t vertex_buffer_unlock = read_guest_u32(
            d3d9_provider_module, "ram", vertex_buffer_vtable + 12 * 4);
        const uint32_t vertex_buffer_get_desc = read_guest_u32(
            d3d9_provider_module, "ram", vertex_buffer_vtable + 13 * 4);
        constexpr uint32_t vertex_buffer_desc_address = 0x004051b0;
        require(invoke_import(d3d9_provider_module, vertex_buffer_get_desc,
                              {vertex_buffer,
                               vertex_buffer_desc_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   vertex_buffer_desc_address) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   vertex_buffer_desc_address + 4) == 6 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   vertex_buffer_desc_address + 12) == 1 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   vertex_buffer_desc_address + 16) == 24,
                "managed vertex buffer description was incorrect");
        constexpr uint32_t vertex_buffer_locked_pointer_address = 0x004051d0;
        require(invoke_import(d3d9_provider_module, vertex_buffer_lock,
                              {vertex_buffer, 8, 8,
                               vertex_buffer_locked_pointer_address, 0}) == 0,
                "managed vertex buffer Lock rejected a valid range");
        const uint32_t vertex_buffer_locked_data = read_guest_u32(
            d3d9_provider_module, "ram", vertex_buffer_locked_pointer_address);
        write_guest_u32(d3d9_provider_module, "ram", vertex_buffer_locked_data,
                        0x11223344);
        write_guest_u32(d3d9_provider_module, "ram", vertex_buffer_locked_data + 4,
                        0x55667788);
        require(invoke_import(d3d9_provider_module, vertex_buffer_unlock,
                              {vertex_buffer}) == 0 &&
                    d3d9_backend_fixture.vertex_buffer_update_called &&
                    d3d9_backend_fixture.vertex_buffer_update_offset == 8 &&
                    d3d9_backend_fixture.vertex_buffer_update_size == 8 &&
                    d3d9_backend_fixture.vertex_buffer_update_data[0] == 0x44 &&
                    d3d9_backend_fixture.vertex_buffer_update_data[7] == 0x55,
                "managed vertex buffer Unlock did not preserve written bytes");
        constexpr uint32_t stream_buffer_output_address = 0x00405300;
        constexpr uint32_t stream_offset_output_address = 0x00405304;
        constexpr uint32_t stream_stride_output_address = 0x00405308;
        const uint32_t set_stream_result = invoke_import(
            d3d9_provider_module, device_set_stream_source,
            {created_device, 0, vertex_buffer, 8, 4});
        require(set_stream_result == 0,
                "SetStreamSource rejected a valid guest buffer: " +
                    std::to_string(set_stream_result));
        const uint32_t get_stream_result = invoke_import(
            d3d9_provider_module, device_get_stream_source,
            {created_device, 0, stream_buffer_output_address,
             stream_offset_output_address, stream_stride_output_address});
        require(get_stream_result == 0,
                "GetStreamSource rejected valid output pointers: " +
                    std::to_string(get_stream_result));
        require(read_guest_u32(d3d9_provider_module, "ram",
                               stream_buffer_output_address) == vertex_buffer &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   stream_offset_output_address) == 8 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   stream_stride_output_address) == 4,
                "GetStreamSource changed buffer, offset, or stride");
        const uint32_t stream_get_ref_release_result = invoke_import(
            d3d9_provider_module, vertex_buffer_release, {vertex_buffer});
        require(stream_get_ref_release_result == 1,
                "GetStreamSource did not AddRef its returned buffer");
        const uint32_t stream_unbind_result = invoke_import(
            d3d9_provider_module, device_set_stream_source,
            {created_device, 0, 0, 0, 0});
        require(stream_unbind_result == 0,
                "SetStreamSource rejected a null buffer");
        const uint32_t stream_final_release_result = invoke_import(
            d3d9_provider_module, vertex_buffer_release, {vertex_buffer});
        require(stream_final_release_result == 0 &&
                    d3d9_backend_fixture.vertex_buffer_release_called,
                "unbound vertex buffer was not released");
        const uint32_t invalid_stream_result = invoke_import(
            d3d9_provider_module, device_set_stream_source,
            {created_device, 16, 0, 0, 0});
        require(invalid_stream_result == 0x8876086c,
                "SetStreamSource accepted stream index 16: " +
                    std::to_string(invalid_stream_result));
        write_guest_u32(d3d9_provider_module, "ram", vertex_buffer_output_address,
                        0x77777777);
        require(invoke_import(
                    d3d9_provider_module, create_vertex_buffer,
                    {created_device, 24, 0x200, 0, 1,
                     vertex_buffer_output_address, 0}) == 0x8876086a &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   vertex_buffer_output_address) == 0,
                "CreateVertexBuffer accepted a dynamic managed buffer");
        constexpr uint32_t index_buffer_output_address = 0x004051a0;
        require(invoke_import(
                    d3d9_provider_module, create_index_buffer,
                    {created_device, 24, 0x20, 101, 0,
                     index_buffer_output_address, 0}) == 0 &&
                    d3d9_backend_fixture.index_buffer_create_called &&
                    d3d9_backend_fixture.index_buffer_device == created_device &&
                    d3d9_backend_fixture.index_buffer_size == 24 &&
                    d3d9_backend_fixture.index_buffer_usage == 0x20 &&
                    d3d9_backend_fixture.index_buffer_format == 101 &&
                    d3d9_backend_fixture.index_buffer_pool == 0,
                "CreateIndexBuffer did not pass its description to the Vulkan host");
        const uint32_t index_buffer = read_guest_u32(
            d3d9_provider_module, "ram", index_buffer_output_address);
        const uint32_t index_buffer_vtable = read_guest_u32(
            d3d9_provider_module, "ram", index_buffer);
        const uint32_t index_buffer_add_ref = read_guest_u32(
            d3d9_provider_module, "ram", index_buffer_vtable + 1 * 4);
        const uint32_t index_buffer_release = read_guest_u32(
            d3d9_provider_module, "ram", index_buffer_vtable + 2 * 4);
        const uint32_t index_buffer_get_device = read_guest_u32(
            d3d9_provider_module, "ram", index_buffer_vtable + 3 * 4);
        const uint32_t index_buffer_lock = read_guest_u32(
            d3d9_provider_module, "ram", index_buffer_vtable + 11 * 4);
        const uint32_t index_buffer_unlock = read_guest_u32(
            d3d9_provider_module, "ram", index_buffer_vtable + 12 * 4);
        const uint32_t index_buffer_get_desc = read_guest_u32(
            d3d9_provider_module, "ram", index_buffer_vtable + 13 * 4);
        constexpr uint32_t index_buffer_desc_address = 0x004051c0;
        require(index_buffer != 0 &&
                    invoke_import(d3d9_provider_module, index_buffer_get_desc,
                                  {index_buffer,
                                   index_buffer_desc_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   index_buffer_desc_address) == 101 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   index_buffer_desc_address + 4) == 7 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   index_buffer_desc_address + 8) == 0x20 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   index_buffer_desc_address + 12) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   index_buffer_desc_address + 16) == 24,
                "IDirect3DIndexBuffer9::GetDesc returned incorrect fields");
        constexpr uint32_t indices_output_address = 0x00405310;
        require(invoke_import(d3d9_provider_module, device_set_indices,
                              {created_device, index_buffer}) == 0 &&
                    invoke_import(d3d9_provider_module, device_get_indices,
                                  {created_device, indices_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   indices_output_address) == index_buffer &&
                    invoke_import(d3d9_provider_module, index_buffer_release,
                                  {index_buffer}) == 1 &&
                    invoke_import(d3d9_provider_module, device_set_indices,
                                  {created_device, 0}) == 0,
                "SetIndices/GetIndices did not preserve the index buffer binding");
        constexpr uint32_t index_buffer_locked_pointer_address = 0x004051e0;
        require(invoke_import(d3d9_provider_module, index_buffer_lock,
                              {index_buffer, 4, 8,
                               index_buffer_locked_pointer_address, 0}) == 0,
                "IDirect3DIndexBuffer9::Lock rejected a valid range");
        const uint32_t index_buffer_locked_data = read_guest_u32(
            d3d9_provider_module, "ram", index_buffer_locked_pointer_address);
        write_guest_u32(d3d9_provider_module, "ram", index_buffer_locked_data,
                        0x12345678);
        write_guest_u32(d3d9_provider_module, "ram", index_buffer_locked_data + 4,
                        0x9abcdef0);
        require(invoke_import(d3d9_provider_module, index_buffer_unlock,
                              {index_buffer}) == 0 &&
                    d3d9_backend_fixture.index_buffer_update_called &&
                    d3d9_backend_fixture.index_buffer_update_offset == 4 &&
                    d3d9_backend_fixture.index_buffer_update_size == 8 &&
                    d3d9_backend_fixture.index_buffer_update_data[0] == 0x78 &&
                    d3d9_backend_fixture.index_buffer_update_data[3] == 0x12 &&
                    d3d9_backend_fixture.index_buffer_update_data[4] == 0xf0 &&
                    d3d9_backend_fixture.index_buffer_update_data[7] == 0x9a,
                "IDirect3DIndexBuffer9::Unlock did not upload the written bytes");
        constexpr uint32_t index_buffer_device_output_address = 0x004051f0;
        require(invoke_import(d3d9_provider_module, index_buffer_add_ref,
                              {index_buffer}) == 2 &&
                    invoke_import(d3d9_provider_module, index_buffer_get_device,
                                  {index_buffer,
                                   index_buffer_device_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   index_buffer_device_output_address) ==
                        created_device &&
                    invoke_import(d3d9_provider_module, provider_device_release,
                                  {created_device}) == 2 &&
                    invoke_import(d3d9_provider_module, index_buffer_release,
                                  {index_buffer}) == 1 &&
                    invoke_import(d3d9_provider_module, index_buffer_release,
                                  {index_buffer}) == 0 &&
                    d3d9_backend_fixture.index_buffer_release_called,
                "IDirect3DIndexBuffer9 COM lifetime was incorrect");
        constexpr uint32_t managed_index_buffer_output_address = 0x004051b0;
        require(invoke_import(
                    d3d9_provider_module, create_index_buffer,
                    {created_device, 12, 0, 101, 1,
                     managed_index_buffer_output_address, 0}) == 0 &&
                    d3d9_backend_fixture.index_buffer_size == 12 &&
                    d3d9_backend_fixture.index_buffer_usage == 0 &&
                    d3d9_backend_fixture.index_buffer_pool == 1,
                "CreateIndexBuffer rejected a static managed buffer");
        const uint32_t managed_index_buffer = read_guest_u32(
            d3d9_provider_module, "ram", managed_index_buffer_output_address);
        constexpr uint32_t dynamic_managed_index_buffer_output_address =
            0x004051b4;
        require(managed_index_buffer != 0 &&
                    invoke_import(
                        d3d9_provider_module, create_index_buffer,
                        {created_device, 12, 0x200, 101, 1,
                         dynamic_managed_index_buffer_output_address, 0}) ==
                        0x8876086a &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   dynamic_managed_index_buffer_output_address) ==
                        0 &&
                    d3d9_backend_fixture.index_buffer_size == 12 &&
                    d3d9_backend_fixture.index_buffer_usage == 0 &&
                    d3d9_backend_fixture.index_buffer_pool == 1,
                "CreateIndexBuffer accepted a dynamic managed buffer");
        const uint32_t managed_index_buffer_vtable = read_guest_u32(
            d3d9_provider_module, "ram", managed_index_buffer);
        const uint32_t managed_index_buffer_release = read_guest_u32(
            d3d9_provider_module, "ram", managed_index_buffer_vtable + 2 * 4);
        require(invoke_import(d3d9_provider_module, managed_index_buffer_release,
                              {managed_index_buffer}) == 0,
                "managed index buffer release failed");
        constexpr uint32_t vertex_declaration_elements_address = 0x00405200;
        constexpr uint32_t vertex_declaration_output_address = 0x00405220;
        write_guest_u32(d3d9_provider_module, "ram",
                        vertex_declaration_elements_address, 0);
        write_guest_u32(d3d9_provider_module, "ram",
                        vertex_declaration_elements_address + 4, 2);
        write_guest_u32(d3d9_provider_module, "ram",
                        vertex_declaration_elements_address + 8, 0xff);
        write_guest_u32(d3d9_provider_module, "ram",
                        vertex_declaration_elements_address + 12, 17);
        require(invoke_import(
                    d3d9_provider_module, create_vertex_declaration,
                    {created_device, vertex_declaration_elements_address,
                     vertex_declaration_output_address}) == 0,
                "CreateVertexDeclaration rejected a position element");
        const uint32_t vertex_declaration = read_guest_u32(
            d3d9_provider_module, "ram", vertex_declaration_output_address);
        const uint32_t vertex_declaration_vtable = read_guest_u32(
            d3d9_provider_module, "ram", vertex_declaration);
        const uint32_t vertex_declaration_query_interface = read_guest_u32(
            d3d9_provider_module, "ram", vertex_declaration_vtable);
        const uint32_t vertex_declaration_add_ref = read_guest_u32(
            d3d9_provider_module, "ram", vertex_declaration_vtable + 1 * 4);
        const uint32_t vertex_declaration_release = read_guest_u32(
            d3d9_provider_module, "ram", vertex_declaration_vtable + 2 * 4);
        const uint32_t vertex_declaration_get_device = read_guest_u32(
            d3d9_provider_module, "ram", vertex_declaration_vtable + 3 * 4);
        const uint32_t vertex_declaration_get_declaration = read_guest_u32(
            d3d9_provider_module, "ram", vertex_declaration_vtable + 4 * 4);
        constexpr uint32_t vertex_declaration_binding_output_address =
            0x00405314;
        require(invoke_import(d3d9_provider_module,
                              device_set_vertex_declaration,
                              {created_device, vertex_declaration}) == 0 &&
                    invoke_import(d3d9_provider_module,
                                  device_get_vertex_declaration,
                                  {created_device,
                                   vertex_declaration_binding_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   vertex_declaration_binding_output_address) ==
                        vertex_declaration &&
                    invoke_import(d3d9_provider_module,
                                  vertex_declaration_release,
                                  {vertex_declaration}) == 1 &&
                    invoke_import(d3d9_provider_module,
                                  device_set_vertex_declaration,
                                  {created_device, 0}) == 0 &&
                    invoke_import(d3d9_provider_module,
                                  device_get_vertex_declaration,
                                  {created_device,
                                   vertex_declaration_binding_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   vertex_declaration_binding_output_address) == 0,
                "SetVertexDeclaration/GetVertexDeclaration lost binding state");
        constexpr uint32_t vertex_declaration_count_address = 0x00405240;
        write_guest_u32(d3d9_provider_module, "ram",
                        vertex_declaration_count_address, 0);
        require(vertex_declaration != 0 &&
                    invoke_import(d3d9_provider_module,
                                  vertex_declaration_get_declaration,
                                  {vertex_declaration, 0,
                                   vertex_declaration_count_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   vertex_declaration_count_address) == 2,
                "GetDeclaration did not report element and terminator count");
        constexpr uint32_t vertex_declaration_copy_address = 0x00405260;
        write_guest_u32(d3d9_provider_module, "ram",
                        vertex_declaration_count_address, 2);
        constexpr uint32_t iunknown_iid_address = 0x00405280;
        constexpr std::array<uint8_t, 16> iunknown_iid = {
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46};
        write_guest_bytes(d3d9_provider_module, iunknown_iid_address,
                          iunknown_iid.data(), iunknown_iid.size());
        constexpr uint32_t vertex_declaration_query_output_address =
            0x004052a0;
        require(invoke_import(d3d9_provider_module,
                              vertex_declaration_get_declaration,
                              {vertex_declaration,
                               vertex_declaration_copy_address,
                               vertex_declaration_count_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   vertex_declaration_copy_address) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   vertex_declaration_copy_address + 4) == 2 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   vertex_declaration_copy_address + 8) == 0xff &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   vertex_declaration_copy_address + 12) == 17 &&
                    invoke_import(d3d9_provider_module,
                                  vertex_declaration_query_interface,
                                  {vertex_declaration, iunknown_iid_address,
                                   vertex_declaration_query_output_address}) ==
                        0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   vertex_declaration_query_output_address) ==
                        vertex_declaration &&
                    invoke_import(d3d9_provider_module,
                                  vertex_declaration_release,
                                  {vertex_declaration}) == 1,
                "GetDeclaration or QueryInterface returned wrong data");
        constexpr uint32_t vertex_declaration_device_output_address =
            0x004052c0;
        require(invoke_import(d3d9_provider_module,
                              vertex_declaration_add_ref,
                              {vertex_declaration}) == 2 &&
                    invoke_import(d3d9_provider_module,
                                  vertex_declaration_get_device,
                                  {vertex_declaration,
                                   vertex_declaration_device_output_address}) ==
                        0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   vertex_declaration_device_output_address) ==
                        created_device &&
                    invoke_import(d3d9_provider_module,
                                  provider_device_release,
                                  {created_device}) == 2 &&
                    invoke_import(d3d9_provider_module,
                                  vertex_declaration_release,
                                  {vertex_declaration}) == 1 &&
                    invoke_import(d3d9_provider_module,
                                  vertex_declaration_release,
                                  {vertex_declaration}) == 0,
                "IDirect3DVertexDeclaration9 COM lifetime was incorrect");
        constexpr uint32_t image_source_address = 0x00035800;
        constexpr uint32_t image_info_address = 0x00035880;
        std::vector<uint8_t> dds_header(208, 0);
        std::copy_n("DDS ", 4, dds_header.begin());
        write_u32(dds_header, 4, 124);
        write_u32(dds_header, 8, 0x000a1007);
        write_u32(dds_header, 12, 4);
        write_u32(dds_header, 16, 8);
        write_u32(dds_header, 20, 32);
        write_u32(dds_header, 28, 4);
        write_u32(dds_header, 76, 32);
        write_u32(dds_header, 80, 4);
        write_u32(dds_header, 84, 0x35545844);  // DXT5.
        write_guest_bytes(d3d9_provider_module, image_source_address,
                          dds_header.data(), dds_header.size());
        require(invoke_import(
                    d3d9_provider_module, provider_d3dx_get_image_info,
                    {image_source_address,
                     static_cast<uint32_t>(dds_header.size()),
                     image_info_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   image_info_address) == 8 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   image_info_address + 4) == 4 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   image_info_address + 8) == 1 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   image_info_address + 12) == 4 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   image_info_address + 16) == 0x35545844 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   image_info_address + 20) == 3 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   image_info_address + 24) == 4,
                "D3DX image info did not report the DDS metadata");
        std::vector<uint8_t> a1r5g5b5_dds(214, 0);
        std::copy_n("DDS ", 4, a1r5g5b5_dds.begin());
        write_u32(a1r5g5b5_dds, 4, 124);
        write_u32(a1r5g5b5_dds, 8, 0x0002100f);
        write_u32(a1r5g5b5_dds, 12, 4);
        write_u32(a1r5g5b5_dds, 16, 8);
        write_u32(a1r5g5b5_dds, 20, 16);
        write_u32(a1r5g5b5_dds, 28, 4);
        write_u32(a1r5g5b5_dds, 76, 32);
        write_u32(a1r5g5b5_dds, 80, 0x41);
        write_u32(a1r5g5b5_dds, 88, 16);
        write_u32(a1r5g5b5_dds, 92, 0x7c00);
        write_u32(a1r5g5b5_dds, 96, 0x03e0);
        write_u32(a1r5g5b5_dds, 100, 0x001f);
        write_u32(a1r5g5b5_dds, 104, 0x8000);
        for (size_t index = 128; index < a1r5g5b5_dds.size(); ++index)
            a1r5g5b5_dds[index] = static_cast<uint8_t>(index ^ 0xa5);
        write_guest_bytes(d3d9_provider_module, image_source_address,
                          a1r5g5b5_dds.data(), a1r5g5b5_dds.size());
        require(invoke_import(
                    d3d9_provider_module, provider_d3dx_get_image_info,
                    {image_source_address,
                     static_cast<uint32_t>(a1r5g5b5_dds.size()),
                     image_info_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   image_info_address + 16) == 25 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   image_info_address + 24) == 4,
                "D3DX image info did not decode uncompressed DDS masks");
        write_guest_u32(d3d9_provider_module, "ram", image_info_address,
                        0x5a5a5a5a);
        require(invoke_import(
                    d3d9_provider_module, provider_d3dx_get_image_info,
                    {image_source_address, 127, image_info_address}) ==
                    0x8876086c &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   image_info_address) == 0x5a5a5a5a,
                "D3DX image info accepted a truncated DDS header");

        constexpr uint32_t d3dx_device_wrapper_address = 0x00035900;
        constexpr uint32_t d3dx_device_wrapper_vtable = 0x00035920;
        constexpr uint32_t d3dx_source_address = 0x00035a00;
        constexpr uint32_t d3dx_texture_output_address = 0x00035940;
        constexpr uint32_t d3dx_source_info_address = 0x00035950;
        write_guest_bytes(d3d9_provider_module, d3dx_source_address,
                          a1r5g5b5_dds.data(), a1r5g5b5_dds.size());
        write_guest_u32(d3d9_provider_module, "ram",
                        d3dx_device_wrapper_address,
                        d3dx_device_wrapper_vtable);
        write_guest_u32(d3d9_provider_module, "ram",
                        d3dx_device_wrapper_address + 4, 0);
        write_guest_u32(d3d9_provider_module, "ram",
                        d3dx_device_wrapper_address + 8, created_device);
        require(invoke_import(
                    d3d9_provider_module,
                    provider_d3dx_create_texture_from_memory_ex,
                    {d3dx_device_wrapper_address, d3dx_source_address,
                     static_cast<uint32_t>(a1r5g5b5_dds.size()), UINT32_MAX,
                     UINT32_MAX, 4, 0, 0, 1, 1, 1, 0,
                     d3dx_source_info_address, 0,
                     d3dx_texture_output_address}) == 0,
                "D3DXCreateTextureFromFileInMemoryEx rejected the retail DDS path");
        const uint32_t d3dx_texture = read_guest_u32(
            d3d9_provider_module, "ram", d3dx_texture_output_address);
        const uint32_t d3dx_texture_vtable = read_guest_u32(
            d3d9_provider_module, "ram", d3dx_texture);
        const uint32_t d3dx_texture_get_level_count = read_guest_u32(
            d3d9_provider_module, "ram", d3dx_texture_vtable + 13 * 4);
        const uint32_t d3dx_texture_get_level_desc = read_guest_u32(
            d3d9_provider_module, "ram", d3dx_texture_vtable + 17 * 4);
        const uint32_t d3dx_texture_lock_rect = read_guest_u32(
            d3d9_provider_module, "ram", d3dx_texture_vtable + 19 * 4);
        const uint32_t d3dx_texture_unlock_rect = read_guest_u32(
            d3d9_provider_module, "ram", d3dx_texture_vtable + 20 * 4);
        const uint32_t d3dx_texture_release = read_guest_u32(
            d3d9_provider_module, "ram", d3dx_texture_vtable + 2 * 4);
        constexpr uint32_t d3dx_texture_desc_address = 0x00035970;
        constexpr uint32_t d3dx_texture_locked_rect_address = 0x00035990;
        require(d3dx_texture != 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   d3dx_source_info_address) == 8 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   d3dx_source_info_address + 4) == 4 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   d3dx_source_info_address + 12) == 4 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   d3dx_source_info_address + 16) == 25 &&
                    invoke_import(d3d9_provider_module,
                                  d3dx_texture_get_level_count,
                                  {d3dx_texture}) == 4 &&
                    invoke_import(d3d9_provider_module,
                                  d3dx_texture_get_level_desc,
                                  {d3dx_texture, 3,
                                   d3dx_texture_desc_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   d3dx_texture_desc_address) == 25 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   d3dx_texture_desc_address + 24) == 1 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   d3dx_texture_desc_address + 28) == 1,
                "D3DX texture metadata or mip descriptions were incorrect");
        require(invoke_import(d3d9_provider_module, d3dx_texture_lock_rect,
                              {d3dx_texture, 0,
                               d3dx_texture_locked_rect_address, 0, 0}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   d3dx_texture_locked_rect_address) == 16,
                "D3DX texture base mip pitch was incorrect");
        const uint32_t d3dx_texture_pixels = read_guest_u32(
            d3d9_provider_module, "ram",
            d3dx_texture_locked_rect_address + 4);
        std::array<uint8_t, 4> copied_base_pixels{};
        require(d3d9_provider_module.read_guest(
                    "ram", d3dx_texture_pixels, copied_base_pixels.size(),
                    copied_base_pixels.data()),
                "D3DX texture base mip pointer could not be read");
        require(copied_base_pixels[0] == a1r5g5b5_dds[128] &&
                    copied_base_pixels[3] == a1r5g5b5_dds[131],
                "D3DX texture base mip data mismatch: got " +
                    std::to_string(copied_base_pixels[0]) + "," +
                    std::to_string(copied_base_pixels[3]) + " expected " +
                    std::to_string(a1r5g5b5_dds[128]) + "," +
                    std::to_string(a1r5g5b5_dds[131]) + " at " +
                    std::to_string(d3dx_texture_pixels));
        require(invoke_import(d3d9_provider_module,
                              d3dx_texture_unlock_rect,
                              {d3dx_texture, 0}) == 0,
                "D3DX texture base mip unlock failed");
        require(invoke_import(d3d9_provider_module,
                              d3dx_texture_lock_rect,
                              {d3dx_texture, 3,
                               d3dx_texture_locked_rect_address, 0, 0}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   d3dx_texture_locked_rect_address) == 2,
                "D3DX texture final mip lock or pitch was incorrect");
        const uint32_t d3dx_texture_mip3_pixels = read_guest_u32(
            d3d9_provider_module, "ram",
            d3dx_texture_locked_rect_address + 4);
        std::array<uint8_t, 2> copied_mip3_pixel{};
        require(d3d9_provider_module.read_guest(
                    "ram", d3dx_texture_mip3_pixels,
                    copied_mip3_pixel.size(), copied_mip3_pixel.data()) &&
                    copied_mip3_pixel[0] == a1r5g5b5_dds[212] &&
                    copied_mip3_pixel[1] == a1r5g5b5_dds[213] &&
                    invoke_import(d3d9_provider_module,
                                  d3dx_texture_unlock_rect,
                                  {d3dx_texture, 3}) == 0 &&
                    invoke_import(d3d9_provider_module,
                                  d3dx_texture_release,
                                  {d3dx_texture}) == 0,
                "D3DX texture final mip or release was incorrect");

        std::vector<uint8_t> shader_effect = make_d3dx9_shader_effect();
        if (const char* captured_effect =
                std::getenv("SHIFT_TEST_D3DX_EFFECT");
            captured_effect && *captured_effect) {
            std::ifstream input(captured_effect, std::ios::binary);
            require(static_cast<bool>(input),
                    "could not open optional captured D3DX effect");
            shader_effect.assign(std::istreambuf_iterator<char>(input), {});
            require(!shader_effect.empty(),
                    "optional captured D3DX effect was empty");
        }
        constexpr uint32_t effect_source_address = 0x00036000;
        constexpr uint32_t effect_output_address = 0x00037000;
        constexpr uint32_t effect_errors_address = 0x00037004;
        constexpr uint32_t effect_next_technique_address = 0x00037008;
        constexpr uint32_t effect_desc_address = 0x00037010;
        write_guest_bytes(d3d9_provider_module, effect_source_address,
                          shader_effect.data(), shader_effect.size());
        require(invoke_import(
                    d3d9_provider_module, provider_d3dx_create_effect,
                    {created_device, effect_source_address,
                     static_cast<uint32_t>(shader_effect.size()), 0, 0, 0, 0,
                     effect_output_address, effect_errors_address}) == 0,
                "D3DXCreateEffect did not accept a shader effect binary");
        constexpr uint32_t missing_effect_path_address = 0x00039000;
        constexpr uint32_t compiler_output_address = 0x00039080;
        constexpr uint32_t compiler_errors_address = 0x00039084;
        constexpr char missing_effect_path[] =
            "C:\\no-such-shift-runtime-test-dir\\missing.fx";
        write_guest_bytes(
            d3d9_provider_module, missing_effect_path_address,
            reinterpret_cast<const uint8_t*>(missing_effect_path),
            sizeof(missing_effect_path));
        write_guest_u32(d3d9_provider_module, "ram", compiler_output_address,
                        0x7a7a7a7a);
        write_guest_u32(d3d9_provider_module, "ram", compiler_errors_address,
                        0x7a7a7a7a);
        require(invoke_import(
                    d3d9_provider_module,
                    provider_d3dx_effect_compiler_from_file,
                    {missing_effect_path_address, 0, 0, 0x10000,
                     compiler_output_address, compiler_errors_address}) ==
                        0x8876086c &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   compiler_output_address) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   compiler_errors_address) == 0,
                "D3DX effect compiler did not fail with clear outputs for a missing file");
        const uint32_t guest_effect = read_guest_u32(
            d3d9_provider_module, "ram", effect_output_address);
        constexpr uint32_t malformed_effect_address = 0x00036040;
        constexpr std::array<uint8_t, 7> malformed_effect{};
        write_guest_bytes(d3d9_provider_module, malformed_effect_address,
                          malformed_effect.data(), malformed_effect.size());
        require(invoke_import(
                    d3d9_provider_module, provider_d3dx_create_effect,
                    {created_device, malformed_effect_address,
                     static_cast<uint32_t>(malformed_effect.size()), 0, 0, 0, 0,
                     effect_output_address, effect_errors_address}) ==
                        0x80004005 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   effect_output_address) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   effect_errors_address) == 0,
                "D3DXCreateEffect accepted truncated input or left stale outputs");
        const uint32_t guest_effect_vtable = read_guest_u32(
            d3d9_provider_module, "ram", guest_effect);
        require(guest_effect != 0 && guest_effect_vtable != 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   effect_errors_address) == 0,
                "D3DXCreateEffect did not initialize its COM outputs");
        const uint32_t effect_query_interface = read_guest_u32(
            d3d9_provider_module, "ram", guest_effect_vtable);
        const uint32_t effect_add_ref = read_guest_u32(
            d3d9_provider_module, "ram", guest_effect_vtable + 4);
        const uint32_t effect_release = read_guest_u32(
            d3d9_provider_module, "ram", guest_effect_vtable + 8);
        const uint32_t effect_get_desc = read_guest_u32(
            d3d9_provider_module, "ram", guest_effect_vtable + 3 * 4);
        const uint32_t effect_get_device = read_guest_u32(
            d3d9_provider_module, "ram", guest_effect_vtable + 68 * 4);
        const uint32_t effect_find_next_valid_technique = read_guest_u32(
            d3d9_provider_module, "ram", guest_effect_vtable + 61 * 4);
        shift::runtime::D3dx9BinaryEffect expected_effect_desc;
        std::string effect_desc_parse_error;
        require(shift::runtime::parse_d3dx9_binary_effect(
                    shader_effect.data(), shader_effect.size(),
                    expected_effect_desc, effect_desc_parse_error),
                "could not parse effect fixture for GetDesc expectations: " +
                    effect_desc_parse_error);
        require(invoke_import(d3d9_provider_module, effect_get_desc,
                              {guest_effect, effect_desc_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   effect_desc_address) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   effect_desc_address + 4) ==
                        expected_effect_desc.parameters.size() &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   effect_desc_address + 8) ==
                        expected_effect_desc.techniques.size() &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   effect_desc_address + 12) == 0,
                "ID3DXEffect::GetDesc returned incorrect effect counts");
        constexpr uint32_t effect_device_output_address = 0x0003700c;
        require(invoke_import(d3d9_provider_module, effect_get_device,
                              {guest_effect, effect_device_output_address}) ==
                        0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   effect_device_output_address) ==
                        created_device &&
                    invoke_import(d3d9_provider_module,
                                  provider_device_release,
                                  {created_device}) == 2,
                "ID3DXEffect::GetDevice did not return and retain its device");
        constexpr uint32_t effect_iid_address = 0x00037100;
        constexpr std::array<uint8_t, 16> iid_id3dx_effect = {
            0xb3, 0xb4, 0xce, 0xf6, 0x4c, 0x4e, 0xdd, 0x40,
            0xb8, 0x83, 0x8d, 0x8d, 0xe5, 0xea, 0x0c, 0xd5};
        write_guest_bytes(d3d9_provider_module, effect_iid_address,
                          iid_id3dx_effect.data(), iid_id3dx_effect.size());
        require(invoke_import(d3d9_provider_module, effect_query_interface,
                              {guest_effect, effect_iid_address,
                               effect_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   effect_output_address) == guest_effect &&
                    invoke_import(d3d9_provider_module, effect_release,
                                  {guest_effect}) == 1 &&
                    invoke_import(
                        d3d9_provider_module,
                        effect_find_next_valid_technique,
                        {guest_effect, 0, effect_next_technique_address}) == 1 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   effect_next_technique_address) == 0 &&
                    invoke_import(d3d9_provider_module, effect_add_ref,
                                  {guest_effect}) == 2 &&
                    invoke_import(d3d9_provider_module, effect_release,
                                  {guest_effect}) == 1 &&
                    invoke_import(d3d9_provider_module, effect_release,
                                  {guest_effect}) == 0,
                "ID3DXEffect COM lifetime or invalid-technique result changed");
        constexpr uint32_t effect_texture_output_address = 0x00405180;
        require(invoke_import(
                    d3d9_provider_module, create_texture,
                    {created_device, 2, 2, 1, 0, 21, 1,
                     effect_texture_output_address, 0}) == 0,
                "CreateTexture failed to create the effect binding fixture");
        const uint32_t effect_texture = read_guest_u32(
            d3d9_provider_module, "ram", effect_texture_output_address);
        const uint32_t effect_texture_vtable = read_guest_u32(
            d3d9_provider_module, "ram", effect_texture);
        const uint32_t effect_texture_add_ref = read_guest_u32(
            d3d9_provider_module, "ram", effect_texture_vtable + 1 * 4);
        const uint32_t effect_texture_release = read_guest_u32(
            d3d9_provider_module, "ram", effect_texture_vtable + 2 * 4);
        std::vector<uint8_t> complete_shader_effect =
            make_d3dx9_shader_effect(true);
        shift::runtime::D3dx9BinaryEffect parsed_complete_shader_effect;
        std::string complete_shader_effect_parse_error;
        require(shift::runtime::parse_d3dx9_binary_effect(
                    complete_shader_effect.data(), complete_shader_effect.size(),
                    parsed_complete_shader_effect,
                    complete_shader_effect_parse_error),
                "complete shader effect fixture was invalid: " +
                    complete_shader_effect_parse_error);
        require(parsed_complete_shader_effect.parameters.size() == 2 &&
                    parsed_complete_shader_effect.parameters[1].type.name ==
                        "TextureParameter" &&
                    parsed_complete_shader_effect.parameters[1].type.type == 5,
                "complete shader effect fixture lost its texture parameter metadata");
        write_guest_bytes(d3d9_provider_module, effect_source_address,
                          complete_shader_effect.data(),
                          complete_shader_effect.size());
        require(invoke_import(
                    d3d9_provider_module, provider_d3dx_create_effect,
                    {created_device, effect_source_address,
                     static_cast<uint32_t>(complete_shader_effect.size()),
                     0, 0, 0, 0, effect_output_address,
                     effect_errors_address}) == 0,
                "D3DXCreateEffect rejected a complete vertex/pixel effect");
        const uint32_t complete_effect = read_guest_u32(
            d3d9_provider_module, "ram", effect_output_address);
        const uint32_t complete_effect_vtable = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect);
        const uint32_t complete_find_next = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 61 * 4);
        const uint32_t complete_get_technique = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 12 * 4);
        const uint32_t complete_get_technique_desc = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 5 * 4);
        const uint32_t complete_set_technique = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 58 * 4);
        const uint32_t complete_get_current_technique = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 59 * 4);
        const uint32_t complete_begin = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 63 * 4);
        const uint32_t complete_begin_pass = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 64 * 4);
        const uint32_t complete_commit_changes = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 65 * 4);
        const uint32_t complete_end_pass = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 66 * 4);
        const uint32_t complete_end = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 67 * 4);
        const uint32_t complete_get_annotation_by_name = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 19 * 4);
        const uint32_t complete_get_annotation = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 18 * 4);
        const uint32_t complete_get_parameter_desc = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 4 * 4);
        const uint32_t complete_get_parameter = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 8 * 4);
        const uint32_t complete_get_parameter_by_name = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 9 * 4);
        const uint32_t complete_get_parameter_by_semantic = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 10 * 4);
        const uint32_t complete_get_bool = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 23 * 4);
        const uint32_t complete_get_int = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 27 * 4);
        const uint32_t complete_get_string = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 51 * 4);
        const uint32_t complete_set_texture = read_guest_u32(
            d3d9_provider_module, "ram", complete_effect_vtable + 52 * 4);
        require(invoke_import(d3d9_provider_module, complete_find_next,
                              {complete_effect, 0,
                               effect_next_technique_address}) == 0,
                "FindNextValidTechnique rejected a complete shader technique");
        const uint32_t technique_handle = read_guest_u32(
            d3d9_provider_module, "ram", effect_next_technique_address);
        std::array<uint8_t, 10> technique_name{};
        require(technique_handle != 0 &&
                    d3d9_provider_module.read_guest(
                        "ram", technique_handle, technique_name.size(),
                        technique_name.data()) &&
                    std::equal(technique_name.begin(), technique_name.end(),
                               "ShadowGen"),
                "FindNextValidTechnique did not return its guest technique handle");
        require(invoke_import(d3d9_provider_module, complete_get_technique,
                              {complete_effect, 0}) == technique_handle &&
                    invoke_import(d3d9_provider_module,
                                  complete_get_technique,
                                  {complete_effect, 1}) == 0,
                "ID3DXEffect::GetTechnique returned an incorrect indexed handle");
        require(invoke_import(d3d9_provider_module,
                              complete_get_current_technique,
                              {complete_effect}) == technique_handle &&
                    invoke_import(d3d9_provider_module, complete_set_technique,
                                  {complete_effect, technique_handle}) == 0 &&
                    invoke_import(d3d9_provider_module,
                                 complete_get_current_technique,
                                 {complete_effect}) == technique_handle &&
                    invoke_import(d3d9_provider_module, complete_set_technique,
                                  {complete_effect, UINT32_MAX}) ==
                        0x8876086c,
                "ID3DXEffect technique selection did not validate or update the current handle");
        constexpr uint32_t effect_pass_count_address = 0x00037180;
        require(invoke_import(d3d9_provider_module, complete_begin,
                              {complete_effect, effect_pass_count_address,
                               0x3}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   effect_pass_count_address) == 1 &&
                    invoke_import(d3d9_provider_module, complete_begin_pass,
                                  {complete_effect, 1}) == 0x8876086c &&
                    invoke_import(d3d9_provider_module, complete_begin_pass,
                                  {complete_effect, 0}) == 0 &&
                    invoke_import(d3d9_provider_module,
                                  complete_commit_changes,
                                  {complete_effect}) == 0 &&
                    invoke_import(d3d9_provider_module, complete_end_pass,
                                  {complete_effect}) == 0 &&
                    invoke_import(d3d9_provider_module, complete_end,
                                  {complete_effect}) == 0 &&
                    invoke_import(d3d9_provider_module, complete_end,
                                  {complete_effect}) == 0x8876086c,
                "ID3DXEffect Begin/Pass/Commit/End state sequence was invalid");
        const uint32_t parameter_handle = invoke_import(
            d3d9_provider_module, complete_get_parameter,
            {complete_effect, 0, 0});
        const uint32_t texture_parameter_handle = invoke_import(
            d3d9_provider_module, complete_get_parameter,
            {complete_effect, 0, 1});
        std::array<uint8_t, 16> parameter_name{};
        require(parameter_handle != 0 &&
                    invoke_import(d3d9_provider_module,
                                  complete_get_parameter,
                                  {complete_effect, 0, 2}) == 0 &&
                    d3d9_provider_module.read_guest(
                        "ram", parameter_handle, parameter_name.size(),
                        parameter_name.data()) &&
                    std::equal(parameter_name.begin(), parameter_name.end(),
                               "ShadowParameter") &&
                    texture_parameter_handle != 0,
                "ID3DXEffect::GetParameter returned an incorrect indexed handle");
        constexpr uint32_t texture_parameter_name_address = 0x00037120;
        constexpr char texture_parameter_name[] = "TextureParameter";
        write_guest_bytes(
            d3d9_provider_module, texture_parameter_name_address,
            reinterpret_cast<const uint8_t*>(texture_parameter_name),
            sizeof(texture_parameter_name));
        require(invoke_import(d3d9_provider_module,
                              complete_get_parameter_by_name,
                              {complete_effect, 0,
                               texture_parameter_name_address}) ==
                    texture_parameter_handle,
                "ID3DXEffect::GetParameterByName missed the texture parameter");
        constexpr uint32_t parameter_semantic_address = 0x00037090;
        constexpr char parameter_semantic[] = "World";
        write_guest_bytes(
            d3d9_provider_module, parameter_semantic_address,
            reinterpret_cast<const uint8_t*>(parameter_semantic),
            sizeof(parameter_semantic));
        require(invoke_import(
                    d3d9_provider_module,
                    complete_get_parameter_by_semantic,
                    {complete_effect, 0, parameter_semantic_address}) ==
                    parameter_handle,
                "ID3DXEffect::GetParameterBySemantic returned an incorrect handle");
        constexpr uint32_t parameter_desc_address = 0x00037240;
        require(invoke_import(d3d9_provider_module,
                              complete_get_parameter_desc,
                              {complete_effect, parameter_handle,
                               parameter_desc_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   parameter_desc_address) == parameter_handle &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   parameter_desc_address + 12) == 3 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   parameter_desc_address + 16) == 1 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   parameter_desc_address + 20) == 1 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   parameter_desc_address + 36) == 4,
                "ID3DXEffect::GetParameterDesc returned an invalid parameter descriptor");
        require(invoke_import(d3d9_provider_module, complete_set_texture,
                              {complete_effect, texture_parameter_handle,
                               effect_texture}) == 0 &&
                    invoke_import(d3d9_provider_module, complete_set_texture,
                                  {complete_effect, parameter_handle,
                                   effect_texture}) == 0x8876086c,
                "ID3DXEffect::SetTexture accepted an invalid parameter type");
        require(invoke_import(d3d9_provider_module, effect_texture_add_ref,
                              {effect_texture}) == 3 &&
                    invoke_import(d3d9_provider_module,
                                  effect_texture_release,
                                  {effect_texture}) == 2,
                "ID3DXEffect::SetTexture did not retain its texture");
        require(invoke_import(d3d9_provider_module,
                              complete_get_technique_desc,
                              {complete_effect, technique_handle,
                               effect_desc_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   effect_desc_address) == technique_handle &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   effect_desc_address + 4) == 3 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   effect_desc_address + 8) == 1,
                "ID3DXEffect::GetTechniqueDesc returned an incorrect descriptor");
        constexpr uint32_t annotation_name_address = 0x00037050;
        constexpr uint32_t annotation_value_address = 0x00037070;
        constexpr char annotation_name[] = "supportsSpecialisedLighting";
        write_guest_bytes(
            d3d9_provider_module, annotation_name_address,
            reinterpret_cast<const uint8_t*>(annotation_name),
            sizeof(annotation_name));
        const uint32_t annotation_handle = invoke_import(
            d3d9_provider_module, complete_get_annotation_by_name,
            {complete_effect, technique_handle, annotation_name_address});
        require(annotation_handle != 0 &&
                    invoke_import(d3d9_provider_module,
                                  complete_get_annotation,
                                  {complete_effect, technique_handle, 0}) ==
                        annotation_handle &&
                    invoke_import(d3d9_provider_module,
                                  complete_get_annotation,
                                  {complete_effect, technique_handle, 5}) == 0 &&
                    invoke_import(
                        d3d9_provider_module, complete_get_annotation_by_name,
                        {complete_effect, technique_handle,
                         annotation_name_address + 1}) == 0 &&
                    invoke_import(d3d9_provider_module, complete_get_bool,
                                  {complete_effect, annotation_handle,
                                   annotation_value_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   annotation_value_address) == 0,
                "ID3DXEffect annotation lookup or BOOL retrieval changed");
        constexpr uint32_t annotation_desc_address = 0x00037200;
        require(invoke_import(d3d9_provider_module,
                              complete_get_parameter_desc,
                              {complete_effect, annotation_handle,
                               annotation_desc_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   annotation_desc_address) ==
                        annotation_handle &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   annotation_desc_address + 8) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   annotation_desc_address + 12) == 1 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   annotation_desc_address + 16) == 1 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   annotation_desc_address + 20) == 1 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   annotation_desc_address + 36) == 4,
                "ID3DXEffect::GetParameterDesc returned an invalid annotation descriptor");
        constexpr uint32_t integer_annotation_name_address = 0x00037120;
        constexpr uint32_t integer_annotation_value_address = 0x00037140;
        constexpr char integer_annotation_name[] = "testIntegerAnnotation";
        write_guest_bytes(
            d3d9_provider_module, integer_annotation_name_address,
            reinterpret_cast<const uint8_t*>(integer_annotation_name),
            sizeof(integer_annotation_name));
        const uint32_t integer_annotation_handle = invoke_import(
            d3d9_provider_module, complete_get_annotation_by_name,
            {complete_effect, technique_handle,
             integer_annotation_name_address});
        require(integer_annotation_handle != 0 &&
                    invoke_import(d3d9_provider_module,
                                  complete_get_annotation,
                                  {complete_effect, technique_handle, 1}) ==
                        integer_annotation_handle &&
                    invoke_import(d3d9_provider_module, complete_get_int,
                                  {complete_effect, integer_annotation_handle,
                                   integer_annotation_value_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   integer_annotation_value_address) == 1 &&
                    invoke_import(d3d9_provider_module, complete_get_int,
                                  {complete_effect, annotation_handle,
                                   integer_annotation_value_address}) ==
                        0x8876086c &&
                    invoke_import(d3d9_provider_module, complete_get_int,
                                  {complete_effect, parameter_handle,
                                   integer_annotation_value_address}) ==
                        0x8876086c,
                "ID3DXEffect::GetInt accepted the wrong type or lost the annotation value");
        constexpr uint32_t integer_annotation_desc_address = 0x00037260;
        require(invoke_import(d3d9_provider_module,
                              complete_get_parameter_desc,
                              {complete_effect, integer_annotation_handle,
                               integer_annotation_desc_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   integer_annotation_desc_address + 12) == 2 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   integer_annotation_desc_address + 36) == 4,
                "integer effect annotation descriptor had the wrong type or size");
        constexpr uint32_t string_annotation_name_address = 0x00037120;
        constexpr uint32_t string_output_address = 0x00037160;
        constexpr char string_annotation_name[] = "testStringAnnotation";
        write_guest_bytes(
            d3d9_provider_module, string_annotation_name_address,
            reinterpret_cast<const uint8_t*>(string_annotation_name),
            sizeof(string_annotation_name));
        const uint32_t string_annotation_handle = invoke_import(
            d3d9_provider_module, complete_get_annotation_by_name,
            {complete_effect, technique_handle,
             string_annotation_name_address});
        require(string_annotation_handle != 0 &&
                    invoke_import(d3d9_provider_module, complete_get_annotation,
                                  {complete_effect, technique_handle, 2}) ==
                        string_annotation_handle &&
                    invoke_import(d3d9_provider_module, complete_get_string,
                                  {complete_effect, string_annotation_handle,
                                   string_output_address}) == 0,
                "ID3DXEffect::GetString rejected a string annotation");
        const uint32_t returned_string_address = read_guest_u32(
            d3d9_provider_module, "ram", string_output_address);
        std::array<uint8_t, 5> returned_string{};
        require(returned_string_address != 0 &&
                    d3d9_provider_module.read_guest(
                        "ram", returned_string_address,
                        returned_string.size(), returned_string.data()) &&
                    std::equal(returned_string.begin(), returned_string.end(),
                               "road") &&
                    invoke_import(d3d9_provider_module, complete_get_string,
                                  {complete_effect, string_annotation_handle,
                                   string_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   string_output_address) ==
                        returned_string_address &&
                    invoke_import(d3d9_provider_module, complete_get_string,
                                  {complete_effect, integer_annotation_handle,
                                   string_output_address}) == 0x8876086c &&
                    invoke_import(d3d9_provider_module, complete_get_string,
                                  {complete_effect, parameter_handle,
                                   string_output_address}) == 0x8876086c,
                "ID3DXEffect::GetString returned unstable data or accepted another type");
        constexpr uint32_t string_annotation_desc_address = 0x00037300;
        require(invoke_import(d3d9_provider_module,
                              complete_get_parameter_desc,
                              {complete_effect, string_annotation_handle,
                               string_annotation_desc_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   string_annotation_desc_address + 12) == 4 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   string_annotation_desc_address + 36) == 4,
                "string effect annotation descriptor had the wrong type or size");
        require(invoke_import(d3d9_provider_module, complete_find_next,
                              {complete_effect, technique_handle,
                               effect_next_technique_address}) == 1 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   effect_next_technique_address) == 0 &&
                    invoke_import(d3d9_provider_module, complete_find_next,
                                  {complete_effect, UINT32_MAX,
                                   effect_next_technique_address}) ==
                        0x8876086c &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   effect_next_technique_address) == 0 &&
                    invoke_import(d3d9_provider_module, effect_release,
                                  {complete_effect}) == 0,
                "FindNextValidTechnique did not stop after the last valid technique");
        require(invoke_import(d3d9_provider_module, effect_texture_release,
                              {effect_texture}) == 0,
                "ID3DXEffect::Release did not release its retained texture");
        constexpr uint32_t device_wrapper_address = 0x00038000;
        constexpr uint32_t device_wrapper_vtable = 0x00038100;
        constexpr uint32_t wrapped_effect_output_address = 0x00038020;
        constexpr uint32_t wrapped_device_output_address = 0x00038024;
        write_guest_u32(d3d9_provider_module, "ram", device_wrapper_address,
                        device_wrapper_vtable);
        write_guest_u32(d3d9_provider_module, "ram", device_wrapper_address + 4,
                        0);
        write_guest_u32(d3d9_provider_module, "ram", device_wrapper_address + 8,
                        created_device);
        require(invoke_import(
                    d3d9_provider_module, provider_d3dx_create_effect,
                    {device_wrapper_address, effect_source_address,
                     static_cast<uint32_t>(complete_shader_effect.size()),
                     0, 0, 0, 0,
                     wrapped_effect_output_address, effect_errors_address}) == 0,
                "D3DXCreateEffect rejected the game device forwarding object");
        const uint32_t wrapped_effect = read_guest_u32(
            d3d9_provider_module, "ram", wrapped_effect_output_address);
        const uint32_t wrapped_effect_vtable = read_guest_u32(
            d3d9_provider_module, "ram", wrapped_effect);
        const uint32_t wrapped_effect_get_device = read_guest_u32(
            d3d9_provider_module, "ram", wrapped_effect_vtable + 68 * 4);
        require(invoke_import(d3d9_provider_module, wrapped_effect_get_device,
                              {wrapped_effect, wrapped_device_output_address}) ==
                        0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   wrapped_device_output_address) ==
                        device_wrapper_address &&
                    invoke_import(d3d9_provider_module,
                                  provider_device_release,
                                  {created_device}) == 2 &&
                    invoke_import(d3d9_provider_module,
                                  read_guest_u32(
                                      d3d9_provider_module, "ram",
                                  wrapped_effect_vtable + 2 * 4),
                                  {wrapped_effect}) == 0,
                "D3DX effect did not preserve its forwarding device identity");
        constexpr uint32_t retail_effect_source_address = 0x0003a000;
        constexpr uint32_t retail_effect_output_address = 0x0003b000;
        constexpr uint32_t retail_effect_errors_address = 0x0003b004;
        constexpr uint32_t retail_effect_desc_address = 0x0003b010;
        const auto retail_effect_source =
            shift::runtime::detail::kRetailDefaultEffectSource;
        write_guest_bytes(
            d3d9_provider_module, retail_effect_source_address,
            reinterpret_cast<const uint8_t*>(retail_effect_source.data()),
            retail_effect_source.size());
        require(invoke_import(
                    d3d9_provider_module, provider_d3dx_create_effect,
                    {created_device, retail_effect_source_address,
                     static_cast<uint32_t>(retail_effect_source.size()), 0, 0,
                     0, 0, retail_effect_output_address,
                     retail_effect_errors_address}) == 0,
                "D3DXCreateEffect rejected the exact embedded retail ASCII effect");
        const uint32_t retail_effect = read_guest_u32(
            d3d9_provider_module, "ram", retail_effect_output_address);
        const uint32_t retail_effect_vtable = read_guest_u32(
            d3d9_provider_module, "ram", retail_effect);
        const uint32_t retail_effect_get_desc = read_guest_u32(
            d3d9_provider_module, "ram", retail_effect_vtable + 3 * 4);
        const uint32_t retail_effect_get_technique = read_guest_u32(
            d3d9_provider_module, "ram", retail_effect_vtable + 12 * 4);
        const uint32_t retail_effect_get_technique_desc = read_guest_u32(
            d3d9_provider_module, "ram", retail_effect_vtable + 5 * 4);
        require(retail_effect != 0 &&
                    invoke_import(d3d9_provider_module,
                                  retail_effect_get_desc,
                                  {retail_effect,
                                   retail_effect_desc_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   retail_effect_desc_address + 4) == 1 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   retail_effect_desc_address + 8) == 1,
                "retail ASCII effect metadata did not report one parameter and technique");
        const uint32_t retail_technique = invoke_import(
            d3d9_provider_module, retail_effect_get_technique,
            {retail_effect, 0});
        require(retail_technique != 0 &&
                    invoke_import(d3d9_provider_module,
                                  retail_effect_get_technique_desc,
                                  {retail_effect, retail_technique,
                                   retail_effect_desc_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   retail_effect_desc_address + 4) == 3 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   retail_effect_desc_address + 8) == 1,
                "retail ASCII effect technique annotations or pass count changed");
        auto changed_retail_effect_source =
            std::vector<uint8_t>(retail_effect_source.begin(),
                                 retail_effect_source.end());
        changed_retail_effect_source[0] ^= 1;
        write_guest_bytes(d3d9_provider_module, retail_effect_source_address,
                          changed_retail_effect_source.data(),
                          changed_retail_effect_source.size());
        write_guest_u32(d3d9_provider_module, "ram",
                        retail_effect_output_address, 0x7a7a7a7a);
        write_guest_u32(d3d9_provider_module, "ram",
                        retail_effect_errors_address, 0x7a7a7a7a);
        require(invoke_import(
                    d3d9_provider_module, provider_d3dx_create_effect,
                    {created_device, retail_effect_source_address,
                     static_cast<uint32_t>(changed_retail_effect_source.size()),
                     0, 0, 0, 0, retail_effect_output_address,
                     retail_effect_errors_address}) == 0x80004005 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   retail_effect_output_address) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   retail_effect_errors_address) == 0 &&
                    invoke_import(
                        d3d9_provider_module,
                        read_guest_u32(d3d9_provider_module, "ram",
                                       retail_effect_vtable + 2 * 4),
                        {retail_effect}) == 0,
                "ASCII effect cache accepted altered source or leaked its effect");
        constexpr uint32_t line_output_address = 0x00038340;
        constexpr uint32_t line_iid_address = 0x00038350;
        constexpr uint32_t line_query_output_address = 0x00038360;
        constexpr uint32_t line_device_output_address = 0x00038364;
        write_guest_u32(d3d9_provider_module, "ram", line_output_address,
                        0x7a7a7a7a);
        require(invoke_import(d3d9_provider_module,
                              provider_d3dx_create_line,
                              {0, line_output_address}) == 0x88760870 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   line_output_address) == 0,
                "D3DXCreateLine did not clear output for an invalid device");
        require(invoke_import(d3d9_provider_module,
                              provider_d3dx_create_line,
                              {device_wrapper_address, line_output_address}) == 0,
                "D3DXCreateLine rejected a valid forwarding device");
        const uint32_t guest_line = read_guest_u32(
            d3d9_provider_module, "ram", line_output_address);
        const uint32_t guest_line_vtable = read_guest_u32(
            d3d9_provider_module, "ram", guest_line);
        require(guest_line != 0 && guest_line_vtable != 0,
                "D3DXCreateLine did not initialize its COM object");
        const uint32_t line_query_interface = read_guest_u32(
            d3d9_provider_module, "ram", guest_line_vtable);
        const uint32_t line_add_ref = read_guest_u32(
            d3d9_provider_module, "ram", guest_line_vtable + 4);
        const uint32_t line_release = read_guest_u32(
            d3d9_provider_module, "ram", guest_line_vtable + 8);
        const uint32_t line_get_device = read_guest_u32(
            d3d9_provider_module, "ram", guest_line_vtable + 3 * 4);
        require(invoke_import(d3d9_provider_module, line_add_ref,
                              {guest_line}) == 2,
                "ID3DXLine::AddRef did not retain the object");
        constexpr std::array<uint8_t, 16> iid_unknown = {
            0, 0, 0, 0, 0, 0, 0, 0, 0xc0, 0, 0, 0, 0, 0, 0, 0x46};
        write_guest_bytes(d3d9_provider_module, line_iid_address,
                          iid_unknown.data(), iid_unknown.size());
        require(invoke_import(d3d9_provider_module, line_query_interface,
                              {guest_line, line_iid_address,
                               line_query_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   line_query_output_address) == guest_line &&
                    invoke_import(d3d9_provider_module, line_release,
                                  {guest_line}) == 2,
                "ID3DXLine::QueryInterface did not support IUnknown");
        constexpr std::array<uint8_t, 16> iid_d3dx_line = {
            0x7f, 0xba, 0x79, 0xd3, 0x42, 0x90, 0xc4, 0x4a,
            0x9f, 0x5e, 0x58, 0x19, 0x2a, 0x4c, 0x6b, 0xd8};
        write_guest_bytes(d3d9_provider_module, line_iid_address,
                          iid_d3dx_line.data(), iid_d3dx_line.size());
        require(invoke_import(d3d9_provider_module, line_query_interface,
                              {guest_line, line_iid_address,
                               line_query_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   line_query_output_address) == guest_line &&
                    invoke_import(d3d9_provider_module, line_release,
                                  {guest_line}) == 2,
                "ID3DXLine::QueryInterface rejected its own IID");
        constexpr std::array<uint8_t, 16> iid_unsupported = {
            1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16};
        write_guest_bytes(d3d9_provider_module, line_iid_address,
                          iid_unsupported.data(), iid_unsupported.size());
        write_guest_u32(d3d9_provider_module, "ram", line_query_output_address,
                        0x7a7a7a7a);
        require(invoke_import(d3d9_provider_module, line_query_interface,
                              {guest_line, line_iid_address,
                               line_query_output_address}) == 0x80004002 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   line_query_output_address) == 0,
                "ID3DXLine::QueryInterface accepted an unknown interface");
        require(invoke_import(d3d9_provider_module, line_get_device,
                              {guest_line, line_device_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   line_device_output_address) ==
                        device_wrapper_address,
                "ID3DXLine::GetDevice lost the forwarding device identity");
        const uint32_t line_set_pattern = read_guest_u32(
            d3d9_provider_module, "ram", guest_line_vtable + 7 * 4);
        const uint32_t line_get_pattern = read_guest_u32(
            d3d9_provider_module, "ram", guest_line_vtable + 8 * 4);
        const uint32_t line_set_width = read_guest_u32(
            d3d9_provider_module, "ram", guest_line_vtable + 11 * 4);
        const uint32_t line_get_width = read_guest_u32(
            d3d9_provider_module, "ram", guest_line_vtable + 12 * 4);
        const uint32_t line_set_antialias = read_guest_u32(
            d3d9_provider_module, "ram", guest_line_vtable + 13 * 4);
        const uint32_t line_get_antialias = read_guest_u32(
            d3d9_provider_module, "ram", guest_line_vtable + 14 * 4);
        const uint32_t line_begin = read_guest_u32(
            d3d9_provider_module, "ram", guest_line_vtable + 4 * 4);
        const uint32_t line_draw = read_guest_u32(
            d3d9_provider_module, "ram", guest_line_vtable + 5 * 4);
        const uint32_t line_end = read_guest_u32(
            d3d9_provider_module, "ram", guest_line_vtable + 17 * 4);
        const uint32_t line_lost_device = read_guest_u32(
            d3d9_provider_module, "ram", guest_line_vtable + 18 * 4);
        const uint32_t line_reset_device = read_guest_u32(
            d3d9_provider_module, "ram", guest_line_vtable + 19 * 4);
        require(invoke_import(d3d9_provider_module, line_set_pattern,
                              {guest_line, 0x00ff00ff}) == 0 &&
                    invoke_import(d3d9_provider_module, line_get_pattern,
                                  {guest_line}) == 0x00ff00ff &&
                    invoke_import(d3d9_provider_module, line_set_width,
                                  {guest_line, 0x40200000}) == 0 &&
                    invoke_import(d3d9_provider_module, line_get_width,
                                  {guest_line}) == 0,
                "ID3DXLine pattern or width state did not round-trip");
        std::array<uint8_t, 10> expected_x87_width = {
            0, 0, 0, 0, 0, 0, 0, 0xa0, 0, 0x40};
        std::array<uint8_t, 10> actual_x87_width{};
        require(d3d9_provider_module.read_guest(
                    "register", 0x1100, actual_x87_width.size(),
                    actual_x87_width.data()) &&
                    actual_x87_width == expected_x87_width &&
                    invoke_import(d3d9_provider_module, line_set_antialias,
                                  {guest_line, 1}) == 0 &&
                    invoke_import(d3d9_provider_module, line_get_antialias,
                                  {guest_line}) == 1 &&
                    invoke_import(d3d9_provider_module, line_begin,
                                  {guest_line}) == 0 &&
                    invoke_import(d3d9_provider_module, line_begin,
                                  {guest_line}) == 0x8876086c &&
                    invoke_import(d3d9_provider_module, line_draw,
                                  {guest_line, 0x00038400, 2, 0xffffffff}) ==
                        0x8876086a &&
                    invoke_import(d3d9_provider_module, line_end,
                                  {guest_line}) == 0 &&
                    invoke_import(d3d9_provider_module, line_end,
                                  {guest_line}) == 0x8876086c &&
                    invoke_import(d3d9_provider_module, line_lost_device,
                                  {guest_line}) == 0 &&
                    invoke_import(d3d9_provider_module, line_reset_device,
                                  {guest_line}) == 0,
                "ID3DXLine state, x87 float return, or drawing contract failed");
        require(invoke_import(d3d9_provider_module, line_release,
                              {guest_line}) == 1 &&
                    invoke_import(d3d9_provider_module, line_release,
                                  {guest_line}) == 0 &&
                    invoke_import(d3d9_provider_module,
                                  provider_device_release,
                                  {created_device}) >= 1,
                "ID3DXLine did not release its device/object references");

        constexpr uint32_t buffer_output_address = 0x00038380;
        constexpr uint32_t buffer_iid_address = 0x00038390;
        constexpr uint32_t buffer_query_output_address = 0x000383a0;
        constexpr uint32_t unsupported_iid_address = 0x000383b0;
        constexpr uint32_t unsupported_query_output_address = 0x000383c0;
        write_guest_u32(d3d9_provider_module, "ram", buffer_output_address,
                        UINT32_MAX);
        require(invoke_import(d3d9_provider_module,
                              provider_d3dx_create_buffer,
                              {16, buffer_output_address}) == 0,
                "D3DXCreateBuffer did not create a 16-byte buffer");
        const uint32_t guest_buffer = read_guest_u32(
            d3d9_provider_module, "ram", buffer_output_address);
        const uint32_t guest_buffer_vtable = read_guest_u32(
            d3d9_provider_module, "ram", guest_buffer);
        require(guest_buffer != 0 && guest_buffer_vtable != 0,
                "D3DXCreateBuffer did not initialize its COM object");
        const uint32_t buffer_query_interface = read_guest_u32(
            d3d9_provider_module, "ram", guest_buffer_vtable);
        const uint32_t buffer_add_ref = read_guest_u32(
            d3d9_provider_module, "ram", guest_buffer_vtable + 4);
        const uint32_t buffer_release = read_guest_u32(
            d3d9_provider_module, "ram", guest_buffer_vtable + 8);
        const uint32_t buffer_get_pointer = read_guest_u32(
            d3d9_provider_module, "ram", guest_buffer_vtable + 3 * 4);
        const uint32_t buffer_get_size = read_guest_u32(
            d3d9_provider_module, "ram", guest_buffer_vtable + 4 * 4);
        const uint32_t guest_buffer_data = invoke_import(
            d3d9_provider_module, buffer_get_pointer, {guest_buffer});
        require(guest_buffer_data != 0 &&
                    invoke_import(d3d9_provider_module, buffer_get_size,
                                  {guest_buffer}) == 16,
                "ID3DXBuffer did not expose its storage and size");
        constexpr std::array<uint8_t, 8> buffer_pattern = {
            0x53, 0x48, 0x49, 0x46, 0x54, 0x00, 0x9a, 0xff};
        write_guest_bytes(d3d9_provider_module, guest_buffer_data,
                          buffer_pattern.data(), buffer_pattern.size());
        std::array<uint8_t, 8> buffer_readback{};
        require(d3d9_provider_module.read_guest(
                    "ram", guest_buffer_data, buffer_readback.size(),
                    buffer_readback.data()) &&
                    buffer_readback == buffer_pattern,
                "ID3DXBuffer storage did not preserve guest writes");
        require(invoke_import(d3d9_provider_module, buffer_add_ref,
                              {guest_buffer}) == 2,
                "ID3DXBuffer::AddRef did not retain the object");
        constexpr std::array<uint8_t, 16> buffer_iid_unknown = {
            0, 0, 0, 0, 0, 0, 0, 0, 0xc0, 0, 0, 0, 0, 0, 0, 0x46};
        constexpr std::array<uint8_t, 16> iid_d3dx_buffer = {
            0x08, 0xfb, 0xa5, 0x8b, 0x95, 0x51, 0xe2, 0x40,
            0xac, 0x58, 0x0d, 0x98, 0x9c, 0x3a, 0x01, 0x02};
        write_guest_bytes(d3d9_provider_module, buffer_iid_address,
                          iid_d3dx_buffer.data(), iid_d3dx_buffer.size());
        require(invoke_import(d3d9_provider_module, buffer_query_interface,
                              {guest_buffer, buffer_iid_address,
                               buffer_query_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   buffer_query_output_address) == guest_buffer,
                "ID3DXBuffer::QueryInterface did not return ID3DXBuffer");
        write_guest_bytes(d3d9_provider_module, unsupported_iid_address,
                          buffer_iid_unknown.data(),
                          buffer_iid_unknown.size());
        require(invoke_import(d3d9_provider_module, buffer_query_interface,
                              {guest_buffer, unsupported_iid_address,
                               unsupported_query_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   unsupported_query_output_address) ==
                        guest_buffer,
                "ID3DXBuffer::QueryInterface did not support IUnknown");
        constexpr std::array<uint8_t, 16> buffer_iid_unsupported = {
            0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x40,
            0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff};
        write_guest_bytes(d3d9_provider_module, unsupported_iid_address,
                          buffer_iid_unsupported.data(),
                          buffer_iid_unsupported.size());
        write_guest_u32(d3d9_provider_module, "ram",
                        unsupported_query_output_address, UINT32_MAX);
        require(invoke_import(d3d9_provider_module, buffer_query_interface,
                              {guest_buffer, unsupported_iid_address,
                               unsupported_query_output_address}) ==
                        0x80004002 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   unsupported_query_output_address) == 0,
                "ID3DXBuffer::QueryInterface accepted an unsupported IID");
        require(invoke_import(d3d9_provider_module, buffer_release,
                              {guest_buffer}) == 3 &&
                    invoke_import(d3d9_provider_module, buffer_release,
                                  {guest_buffer}) == 2 &&
                    invoke_import(d3d9_provider_module, buffer_release,
                                  {guest_buffer}) == 1 &&
                    invoke_import(d3d9_provider_module, buffer_release,
                                  {guest_buffer}) == 0,
                "ID3DXBuffer::Release did not free the object at refcount zero");
        write_guest_u32(d3d9_provider_module, "ram", buffer_output_address,
                        UINT32_MAX);
        require(invoke_import(d3d9_provider_module,
                              provider_d3dx_create_buffer,
                              {0, buffer_output_address}) == 0,
                "D3DXCreateBuffer rejected a zero-length buffer");
        const uint32_t empty_buffer = read_guest_u32(
            d3d9_provider_module, "ram", buffer_output_address);
        const uint32_t empty_vtable = read_guest_u32(
            d3d9_provider_module, "ram", empty_buffer);
        require(empty_buffer != 0 &&
                    invoke_import(d3d9_provider_module,
                                  read_guest_u32(d3d9_provider_module, "ram",
                                                 empty_vtable + 3 * 4),
                                  {empty_buffer}) != 0 &&
                    invoke_import(d3d9_provider_module,
                                  read_guest_u32(d3d9_provider_module, "ram",
                                                 empty_vtable + 4 * 4),
                                  {empty_buffer}) == 0 &&
                    invoke_import(d3d9_provider_module,
                                  read_guest_u32(d3d9_provider_module, "ram",
                                                 empty_vtable + 8),
                                  {empty_buffer}) == 0,
                "zero-length ID3DXBuffer did not retain valid object semantics");
        require(invoke_import(d3d9_provider_module,
                              provider_d3dx_create_buffer,
                              {16, 0}) == 0x8876086c,
                "D3DXCreateBuffer accepted a null output pointer");
        write_guest_u32(d3d9_provider_module, "ram", buffer_output_address,
                        UINT32_MAX);
        require(invoke_import(d3d9_provider_module,
                              provider_d3dx_create_buffer,
                              {UINT32_MAX, buffer_output_address}) ==
                        0x8007000e &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   buffer_output_address) == 0,
                "D3DXCreateBuffer did not clear output on allocation failure");

        const uint32_t test_cooperative_level = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 3 * 4);
        const uint32_t device_get_device_caps = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 7 * 4);
        const uint32_t created_device_add_ref = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 4);
        const uint32_t created_device_release = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 8);
        const uint32_t get_number_of_swap_chains = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 15 * 4);
        const uint32_t set_vertex_shader = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 92 * 4);
        const uint32_t set_pixel_shader = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 107 * 4);
        const uint32_t create_vertex_shader = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 91 * 4);
        const uint32_t get_vertex_shader = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 93 * 4);
        const uint32_t create_pixel_shader = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 106 * 4);
        const uint32_t get_pixel_shader = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 108 * 4);
        constexpr uint32_t vertex_shader_function_address = 0x00406000;
        constexpr uint32_t pixel_shader_function_address = 0x00406040;
        constexpr uint32_t vertex_shader_output_address = 0x00406100;
        constexpr uint32_t pixel_shader_output_address = 0x00406104;
        constexpr uint32_t shader_get_output_address = 0x00406108;
        constexpr uint32_t shader_iid_address = 0x00406110;
        constexpr uint32_t shader_query_output_address = 0x00406120;
        constexpr uint32_t shader_device_output_address = 0x00406124;
        constexpr uint32_t shader_function_size_address = 0x00406128;
        constexpr uint32_t shader_function_output_address = 0x00406140;
        constexpr std::array<uint32_t, 6> vertex_shader_function = {
            0xfffe0300, 0x0002fffe, 0x54414243, 0x0000ffff, 0x00000000,
            0x0000ffff};
        constexpr std::array<uint32_t, 4> pixel_shader_function = {
            0xffff0300, 0x0001fffe, 0x54414243, 0x0000ffff};
        for (size_t index = 0; index < vertex_shader_function.size(); ++index) {
            write_guest_u32(d3d9_provider_module, "ram",
                            vertex_shader_function_address + index * 4,
                            vertex_shader_function[index]);
        }
        for (size_t index = 0; index < pixel_shader_function.size(); ++index) {
            write_guest_u32(d3d9_provider_module, "ram",
                            pixel_shader_function_address + index * 4,
                            pixel_shader_function[index]);
        }
        write_guest_u32(d3d9_provider_module, "ram",
                        vertex_shader_output_address, 0x7a7a7a7a);
        require(invoke_import(d3d9_provider_module, create_vertex_shader,
                              {created_device, pixel_shader_function_address,
                               vertex_shader_output_address}) == 0x8876086c &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   vertex_shader_output_address) == 0,
                "CreateVertexShader accepted pixel-stage bytecode or kept a stale output");
        write_guest_u32(d3d9_provider_module, "ram",
                        vertex_shader_output_address, 0x7a7a7a7a);
        write_guest_u32(d3d9_provider_module, "ram",
                        vertex_shader_function_address, 0);
        require(invoke_import(d3d9_provider_module, create_vertex_shader,
                              {created_device, vertex_shader_function_address,
                               vertex_shader_output_address}) == 0x8876086c &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   vertex_shader_output_address) == 0,
                "CreateVertexShader accepted a malformed version token");
        write_guest_u32(d3d9_provider_module, "ram",
                        vertex_shader_function_address,
                        vertex_shader_function[0]);
        require(invoke_import(d3d9_provider_module, create_vertex_shader,
                              {created_device, vertex_shader_function_address,
                               0xfffffffd}) == 0x8876086c,
                "CreateVertexShader accepted an out-of-range guest output pointer");
        require(invoke_import(d3d9_provider_module, create_vertex_shader,
                              {created_device, vertex_shader_function_address,
                               vertex_shader_output_address}) == 0 &&
                    invoke_import(d3d9_provider_module, create_pixel_shader,
                                  {created_device, pixel_shader_function_address,
                                   pixel_shader_output_address}) == 0,
                "D3D9 shader creation rejected bounded SM3 token streams");
        const uint32_t vertex_shader = read_guest_u32(
            d3d9_provider_module, "ram", vertex_shader_output_address);
        const uint32_t pixel_shader = read_guest_u32(
            d3d9_provider_module, "ram", pixel_shader_output_address);
        const uint32_t vertex_shader_vtable = read_guest_u32(
            d3d9_provider_module, "ram", vertex_shader);
        const uint32_t pixel_shader_vtable = read_guest_u32(
            d3d9_provider_module, "ram", pixel_shader);
        require(vertex_shader != 0 && pixel_shader != 0 &&
                    vertex_shader_vtable != 0 && pixel_shader_vtable != 0,
                "D3D9 shader creation did not initialize both COM objects");
        const uint32_t vertex_shader_query_interface = read_guest_u32(
            d3d9_provider_module, "ram", vertex_shader_vtable);
        const uint32_t vertex_shader_add_ref = read_guest_u32(
            d3d9_provider_module, "ram", vertex_shader_vtable + 4);
        const uint32_t vertex_shader_release = read_guest_u32(
            d3d9_provider_module, "ram", vertex_shader_vtable + 8);
        const uint32_t vertex_shader_get_device = read_guest_u32(
            d3d9_provider_module, "ram", vertex_shader_vtable + 3 * 4);
        const uint32_t vertex_shader_get_function = read_guest_u32(
            d3d9_provider_module, "ram", vertex_shader_vtable + 4 * 4);
        const uint32_t pixel_shader_get_function = read_guest_u32(
            d3d9_provider_module, "ram", pixel_shader_vtable + 4 * 4);
        const uint32_t pixel_shader_release = read_guest_u32(
            d3d9_provider_module, "ram", pixel_shader_vtable + 8);
        require(invoke_import(d3d9_provider_module, vertex_shader_add_ref,
                              {vertex_shader}) == 2 &&
                    invoke_import(d3d9_provider_module, vertex_shader_release,
                                  {vertex_shader}) == 1,
                "IDirect3DVertexShader9 reference count did not round-trip");
        constexpr std::array<uint8_t, 16> iid_vertex_shader = {
            0x7e, 0x55, 0xc5, 0xef, 0x65, 0x62, 0x13, 0x46,
            0x8a, 0x94, 0x43, 0x85, 0x78, 0x89, 0xeb, 0x36};
        write_guest_bytes(d3d9_provider_module, shader_iid_address,
                          iid_vertex_shader.data(), iid_vertex_shader.size());
        write_guest_u32(d3d9_provider_module, "ram",
                        shader_query_output_address, 0x7a7a7a7a);
        require(invoke_import(d3d9_provider_module,
                              vertex_shader_query_interface,
                              {vertex_shader, shader_iid_address,
                               shader_query_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   shader_query_output_address) == vertex_shader &&
                    invoke_import(d3d9_provider_module, vertex_shader_release,
                                  {vertex_shader}) == 1,
                "IDirect3DVertexShader9::QueryInterface rejected its own IID");
        constexpr std::array<uint8_t, 16> iid_shader_unknown = {
            0, 0, 0, 0, 0, 0, 0, 0, 0xc0, 0, 0, 0, 0, 0, 0, 0x46};
        write_guest_bytes(d3d9_provider_module, shader_iid_address,
                          iid_shader_unknown.data(),
                          iid_shader_unknown.size());
        write_guest_u32(d3d9_provider_module, "ram",
                        shader_query_output_address, 0x7a7a7a7a);
        require(invoke_import(d3d9_provider_module,
                              vertex_shader_query_interface,
                              {vertex_shader, shader_iid_address,
                               shader_query_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   shader_query_output_address) == vertex_shader &&
                    invoke_import(d3d9_provider_module, vertex_shader_release,
                                  {vertex_shader}) == 1,
                "IDirect3DVertexShader9::QueryInterface did not support IUnknown");
        write_guest_u32(d3d9_provider_module, "ram", shader_function_size_address,
                        0);
        require(invoke_import(d3d9_provider_module, vertex_shader_get_function,
                              {vertex_shader, 0, shader_function_size_address}) ==
                        0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   shader_function_size_address) ==
                        vertex_shader_function.size() * sizeof(uint32_t),
                "GetFunction did not report the stored token stream size");
        const uint32_t vertex_shader_function_size = read_guest_u32(
            d3d9_provider_module, "ram", shader_function_size_address);
        write_guest_u32(d3d9_provider_module, "ram", shader_function_size_address,
                        vertex_shader_function_size);
        require(invoke_import(d3d9_provider_module, vertex_shader_get_function,
                              {vertex_shader, shader_function_output_address,
                               shader_function_size_address}) == 0,
                "GetFunction did not copy the stored token stream");
        for (size_t index = 0; index < vertex_shader_function.size(); ++index) {
            require(read_guest_u32(d3d9_provider_module, "ram",
                                   shader_function_output_address + index * 4) ==
                        vertex_shader_function[index],
                    "GetFunction changed a shader token during round-trip");
        }
        write_guest_u32(d3d9_provider_module, "ram", shader_function_size_address,
                        vertex_shader_function_size - sizeof(uint32_t));
        require(invoke_import(d3d9_provider_module, vertex_shader_get_function,
                              {vertex_shader, shader_function_output_address,
                               shader_function_size_address}) == 0x8876086c,
                "GetFunction accepted an undersized output buffer");
        require(invoke_import(d3d9_provider_module, vertex_shader_get_device,
                              {vertex_shader, shader_device_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   shader_device_output_address) == created_device &&
                    invoke_import(d3d9_provider_module, provider_device_release,
                                  {created_device}) >= 1,
                "IDirect3DVertexShader9::GetDevice lost its parent device");
        write_guest_u32(d3d9_provider_module, "ram", shader_function_size_address,
                        0);
        require(invoke_import(d3d9_provider_module, pixel_shader_get_function,
                              {pixel_shader, 0, shader_function_size_address}) ==
                        0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   shader_function_size_address) ==
                        pixel_shader_function.size() * sizeof(uint32_t),
                "pixel GetFunction did not report its token stream size");
        const uint32_t pixel_shader_function_size = read_guest_u32(
            d3d9_provider_module, "ram", shader_function_size_address);
        write_guest_u32(d3d9_provider_module, "ram", shader_function_size_address,
                        pixel_shader_function_size);
        constexpr uint32_t pixel_shader_function_output_address = 0x00406160;
        require(invoke_import(d3d9_provider_module, pixel_shader_get_function,
                              {pixel_shader,
                               pixel_shader_function_output_address,
                               shader_function_size_address}) == 0,
                "pixel GetFunction did not copy the token stream");
        for (size_t index = 0; index < pixel_shader_function.size(); ++index) {
            require(read_guest_u32(
                        d3d9_provider_module, "ram",
                        pixel_shader_function_output_address + index * 4) ==
                        pixel_shader_function[index],
                    "pixel GetFunction changed a shader token during round-trip");
        }
        write_guest_u32(d3d9_provider_module, "ram", shader_get_output_address,
                        0x7a7a7a7a);
        require(invoke_import(d3d9_provider_module, set_vertex_shader,
                              {created_device, vertex_shader}) == 0 &&
                    invoke_import(d3d9_provider_module, set_vertex_shader,
                                  {created_device, vertex_shader}) == 0 &&
                    invoke_import(d3d9_provider_module, set_pixel_shader,
                                  {created_device, vertex_shader}) == 0x8876086c &&
                    invoke_import(d3d9_provider_module, get_vertex_shader,
                                  {created_device, shader_get_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   shader_get_output_address) == vertex_shader &&
                    invoke_import(d3d9_provider_module, vertex_shader_release,
                                  {vertex_shader}) == 2,
                "vertex shader binding, stage validation, or getter ownership failed");
        require(invoke_import(d3d9_provider_module, vertex_shader_release,
                              {vertex_shader}) == 1 &&
                    invoke_import(d3d9_provider_module, set_vertex_shader,
                                  {created_device, 0}) == 0 &&
                    invoke_import(d3d9_provider_module, get_vertex_shader,
                                  {created_device, shader_get_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   shader_get_output_address) == 0,
                "vertex shader NULL unbind or final Release failed");
        write_guest_u32(d3d9_provider_module, "ram", shader_get_output_address,
                        0x7a7a7a7a);
        require(invoke_import(d3d9_provider_module, set_pixel_shader,
                              {created_device, pixel_shader}) == 0 &&
                    invoke_import(d3d9_provider_module, get_pixel_shader,
                                  {created_device, shader_get_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   shader_get_output_address) == pixel_shader &&
                    invoke_import(d3d9_provider_module, pixel_shader_release,
                                  {pixel_shader}) == 2 &&
                    invoke_import(d3d9_provider_module, pixel_shader_release,
                                  {pixel_shader}) == 1 &&
                    invoke_import(d3d9_provider_module, set_pixel_shader,
                                  {created_device, 0}) == 0 &&
                    invoke_import(d3d9_provider_module, get_pixel_shader,
                                  {created_device, shader_get_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   shader_get_output_address) == 0,
                "pixel shader binding, getter ownership, or NULL unbind failed");
        const uint32_t get_texture = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 64 * 4);
        const uint32_t get_render_target = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 38 * 4);
        const uint32_t get_back_buffer = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 18 * 4);
        const uint32_t get_depth_stencil_surface = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 40 * 4);
        const uint32_t get_viewport = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 48 * 4);
        const uint32_t get_gamma_ramp = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 22 * 4);
        const uint32_t set_sampler_state = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 69 * 4);
        const uint32_t device_present = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 17 * 4);
        const uint32_t device_begin_scene = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 41 * 4);
        const uint32_t device_end_scene = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 42 * 4);
        const uint32_t set_render_state = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 57 * 4);
        const uint32_t get_render_state = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 58 * 4);
        const uint32_t set_viewport = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 47 * 4);
        constexpr uint32_t texture_output_address = 0x00405140;
        constexpr uint32_t render_target_output_address = 0x00405144;
        constexpr uint32_t back_buffer_output_address = 0x0040514c;
        constexpr uint32_t depth_surface_output_address = 0x00405148;
        constexpr uint32_t viewport_output_address = 0x00405150;
        constexpr uint32_t gamma_ramp_output_address = 0x00405200;
        write_guest_u32(d3d9_provider_module, "ram", texture_output_address,
                        0x7a7a7a7a);
        write_guest_u32(d3d9_provider_module, "ram", render_target_output_address,
                        0x7a7a7a7a);
        write_guest_u32(d3d9_provider_module, "ram", back_buffer_output_address,
                        0x7a7a7a7a);
        write_guest_u32(d3d9_provider_module, "ram", depth_surface_output_address,
                        0x7a7a7a7a);
        write_guest_u32(d3d9_provider_module, "ram", viewport_output_address,
                        0x7a7a7a7a);
        require(created_device != 0 && created_device_vtable != 0 &&
                    invoke_import(d3d9_provider_module,
                                  test_cooperative_level,
                                  {created_device}) == 0 &&
                    invoke_import(d3d9_provider_module,
                                  get_number_of_swap_chains,
                                  {created_device}) == 1 &&
                    invoke_import(d3d9_provider_module, get_texture,
                                  {created_device, 0,
                                   texture_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   texture_output_address) == 0 &&
                    invoke_import(d3d9_provider_module, get_render_target,
                                  {created_device, 0,
                                   render_target_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   render_target_output_address) != 0 &&
                    invoke_import(d3d9_provider_module, get_back_buffer,
                                  {created_device, 0, 0, 0,
                                   back_buffer_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   back_buffer_output_address) ==
                        read_guest_u32(d3d9_provider_module, "ram",
                                       render_target_output_address) &&
                    invoke_import(d3d9_provider_module,
                                  get_depth_stencil_surface,
                                  {created_device,
                                   depth_surface_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   depth_surface_output_address) != 0 &&
                    invoke_import(d3d9_provider_module, get_viewport,
                                  {created_device,
                                   viewport_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   viewport_output_address + 8) == 800 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   viewport_output_address + 12) == 600 &&
                    invoke_import(d3d9_provider_module, set_sampler_state,
                                  {created_device, 0, 1, 1}) == 0 &&
                    invoke_import(d3d9_provider_module, set_vertex_shader,
                                  {created_device, 0}) == 0 &&
                    invoke_import(d3d9_provider_module, set_pixel_shader,
                                  {created_device, 0}) == 0,
                "CreateDevice did not create a usable device vtable");
        require(invoke_import(d3d9_provider_module, device_get_device_caps,
                              {created_device, caps_address}) == 0,
                "IDirect3DDevice9::GetDeviceCaps did not return successfully");
        for (size_t index = 0; index < adapter_info.caps.size(); ++index) {
            require(read_guest_u32(d3d9_provider_module, "ram",
                                   caps_address + index * 4) ==
                        adapter_info.caps[index],
                    "IDirect3DDevice9::GetDeviceCaps changed a D3DCAPS9 word");
        }
        constexpr uint32_t render_state_output_address = 0x004052f0;
        write_guest_u32(d3d9_provider_module, "ram",
                        render_state_output_address, 0x7a7a7a7a);
        require(invoke_import(d3d9_provider_module, set_render_state,
                              {created_device, 0xa8, 0x0f}) == 0 &&
                    invoke_import(d3d9_provider_module, get_render_state,
                                  {created_device, 0xa8,
                                   render_state_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   render_state_output_address) == 0x0f &&
                    invoke_import(d3d9_provider_module, set_render_state,
                                  {created_device, 0, 0}) == 0x8876086c,
                "IDirect3DDevice9 render-state methods did not preserve validated state");
        constexpr uint32_t viewport_input_address = 0x00405300;
        constexpr std::array<uint32_t, 6> custom_viewport = {
            10, 20, 320, 240, 0x3e4ccccd, 0x3f4ccccd};
        for (size_t index = 0; index < custom_viewport.size(); ++index) {
            write_guest_u32(d3d9_provider_module, "ram",
                            viewport_input_address + index * 4,
                            custom_viewport[index]);
        }
        require(invoke_import(d3d9_provider_module, set_viewport,
                              {created_device, viewport_input_address}) == 0 &&
                    invoke_import(d3d9_provider_module, get_viewport,
                                  {created_device,
                                   viewport_output_address}) == 0,
                "IDirect3DDevice9 viewport methods did not accept a valid viewport");
        for (size_t index = 0; index < custom_viewport.size(); ++index) {
            require(read_guest_u32(d3d9_provider_module, "ram",
                                   viewport_output_address + index * 4) ==
                        custom_viewport[index],
                    "IDirect3DDevice9::GetViewport changed viewport state");
        }
        write_guest_u32(d3d9_provider_module, "ram",
                        viewport_input_address + 8, 0);
        require(invoke_import(d3d9_provider_module, set_viewport,
                              {created_device, viewport_input_address}) ==
                    0x8876086c &&
                    invoke_import(d3d9_provider_module, get_viewport,
                                  {created_device,
                                   viewport_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   viewport_output_address + 8) == 320,
                "IDirect3DDevice9 rejected an invalid viewport or changed saved state");
        require(invoke_import(d3d9_provider_module, device_begin_scene,
                              {created_device}) == 0 &&
                    invoke_import(d3d9_provider_module, device_begin_scene,
                                  {created_device}) == 0x8876086c &&
                    invoke_import(d3d9_provider_module, device_end_scene,
                                  {created_device}) == 0 &&
                    invoke_import(d3d9_provider_module, device_end_scene,
                                  {created_device}) == 0x8876086c,
                "IDirect3DDevice9 BeginScene/EndScene state was not validated");
        require(invoke_import(d3d9_provider_module, device_present,
                              {created_device, 0, 0, 0, 0}) == 0 &&
                    invoke_import(d3d9_provider_module, device_present,
                                  {created_device, 1, 0, 0, 0}) ==
                        0x8876086a &&
                    d3d9_backend_fixture.present_calls == 1,
                "IDirect3DDevice9::Present accepted an unsupported request");
        std::array<uint8_t, 3 * 256 * sizeof(uint16_t)> gamma_ramp_sentinel{};
        gamma_ramp_sentinel.fill(0xa5);
        write_guest_bytes(d3d9_provider_module, gamma_ramp_output_address,
                          gamma_ramp_sentinel.data(),
                          gamma_ramp_sentinel.size());
        require(call_import(d3d9_provider_module, get_gamma_ramp,
                            {created_device, 0, gamma_ramp_output_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "register", 0x10) ==
                        0x32010,
                "IDirect3DDevice9::GetGammaRamp did not return normally");
        for (size_t channel = 0; channel < 3; ++channel) {
            for (const size_t sample : {size_t{0}, size_t{1}, size_t{128},
                                         size_t{255}}) {
                const uint16_t expected =
                    static_cast<uint16_t>(sample * 257);
                const uint64_t address = gamma_ramp_output_address +
                    (channel * 256 + sample) * sizeof(uint16_t);
                require(read_guest_u16(d3d9_provider_module, "ram", address) ==
                            expected,
                        "IDirect3DDevice9::GetGammaRamp did not return an identity ramp");
            }
        }
        const uint32_t render_target_surface = read_guest_u32(
            d3d9_provider_module, "ram", render_target_output_address);
        const uint32_t surface_vtable = read_guest_u32(
            d3d9_provider_module, "ram", render_target_surface);
        const uint32_t surface_get_desc = read_guest_u32(
            d3d9_provider_module, "ram", surface_vtable + 12 * 4);
        constexpr uint32_t surface_desc_address = 0x00405160;
        require(invoke_import(d3d9_provider_module, surface_get_desc,
                              {render_target_surface,
                               surface_desc_address}) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   surface_desc_address) == 21 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   surface_desc_address + 4) == 1 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   surface_desc_address + 8) == 1 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   surface_desc_address + 12) == 0 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   surface_desc_address + 16) == 2 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   surface_desc_address + 24) == 800 &&
                    read_guest_u32(d3d9_provider_module, "ram",
                                   surface_desc_address + 28) == 600 &&
                    invoke_import(d3d9_provider_module, surface_get_desc,
                                  {render_target_surface, 0}) ==
                        0x8876086c,
                "IDirect3DSurface9::GetDesc returned an invalid backbuffer description");
        const uint32_t device_clear = read_guest_u32(
            d3d9_provider_module, "ram", created_device_vtable + 43 * 4);
        require(invoke_import(d3d9_provider_module, device_clear,
                              {created_device, 0, 0, 7, 0,
                               0x3f800000, 0}) == 0 &&
                    invoke_import(d3d9_provider_module, device_clear,
                                  {created_device, 0, 0, 8, 0, 0, 0}) ==
                        0x8876086c,
                "IDirect3DDevice9::Clear did not validate and accept the retail clear flags");
        const auto clear_snapshot =
            d3d9_provider_module.guest_scheduler_snapshot();
        require(clear_snapshot.d3d9_clear_call_count == 1 &&
                    clear_snapshot.d3d9_last_clear_flags == 7 &&
                    clear_snapshot.d3d9_last_clear_color == 0 &&
                    clear_snapshot.d3d9_last_clear_depth_bits ==
                        0x3f800000 &&
                    clear_snapshot.d3d9_last_clear_stencil == 0 &&
                    clear_snapshot.d3d9_last_clear_rect_count == 0,
                "IDirect3DDevice9::Clear did not preserve its accepted request");
        require(d3d9_backend_fixture.clear_calls == 1 &&
                    d3d9_backend_fixture.clear_flags == 7 &&
                    d3d9_backend_fixture.clear_color == 0 &&
                    d3d9_backend_fixture.clear_depth_bits == 0x3f800000 &&
                    d3d9_backend_fixture.clear_stencil == 0 &&
                    d3d9_backend_fixture.clear_rect_count == 0,
                "IDirect3DDevice9::Clear did not forward its request to the backend");
        require(invoke_import(d3d9_provider_module,
                              created_device_add_ref,
                              {created_device}) == 2 &&
                    invoke_import(d3d9_provider_module,
                                  created_device_release,
                                  {created_device}) == 1 &&
                    invoke_import(d3d9_provider_module,
                                  created_device_release,
                                  {created_device}) == 0,
                "CreateDevice did not create a reference-counted device vtable");
        require(invoke_import(d3d9_module, check_device_format,
                              {d3d9_interface, 0, 1, 0, 1, 1, 1}) ==
                        0x8876086a &&
                    invoke_import(d3d9_module, check_device_format,
                                  {d3d9_interface, 1, 1, 0, 1, 1, 1}) ==
                        0x8876086c &&
                    invoke_import(d3d9_module, check_device_format,
                                  {d3d9_interface, 0, 0, 0, 1, 1, 1}) ==
                        0x8876086c,
                "CheckDeviceFormat did not fail closed for unsupported formats");
        constexpr uint32_t quality_levels_address = 0x00402c80;
        constexpr uint32_t quality_levels_sentinel = 0x7a7a7a7a;
        write_guest_u32(d3d9_module, "ram", quality_levels_address,
                        quality_levels_sentinel);
        require(invoke_import(d3d9_module, check_device_multisample_type,
                              {d3d9_interface, 0, 1, 22, 0, 2,
                               quality_levels_address}) == 0x8876086a &&
                    read_guest_u32(d3d9_module, "ram",
                                   quality_levels_address) ==
                        quality_levels_sentinel &&
                    invoke_import(d3d9_module,
                                  check_device_multisample_type,
                                  {d3d9_interface, 0, 1, 22, 0, 2, 0}) ==
                        0x8876086a &&
                    invoke_import(d3d9_module,
                                  check_device_multisample_type,
                                  {d3d9_interface, 1, 1, 22, 0, 2, 0}) ==
                        0x8876086c &&
                    invoke_import(d3d9_module,
                                  check_device_multisample_type,
                                  {d3d9_interface, 0, 1, 22, 0, 17, 0}) ==
                        0x8876086c &&
                    invoke_import(d3d9_module,
                                  check_device_multisample_type,
                                  {d3d9_interface, 0, 2, 22, 0, 2, 0}) ==
                        0x88760870,
                "CheckDeviceMultiSampleType fabricated or misclassified device support");
        require(invoke_import(d3d9_module, add_ref, {d3d9_interface}) == 2 &&
                    invoke_import(d3d9_module, release, {d3d9_interface}) == 1 &&
                    invoke_import(d3d9_module, release, {d3d9_interface}) == 0,
                "IDirect3D9 reference counting did not follow COM lifetime rules");
        const uint32_t trap_interface =
            invoke_import(d3d9_module, direct3d_create9, {32});
        const uint32_t trap_vtable =
            read_guest_u32(d3d9_module, "ram", trap_interface);
        const uint32_t register_software_device =
            read_guest_u32(d3d9_module, "ram", trap_vtable + 3 * 4);
        require(call_import(d3d9_module, register_software_device,
                            {trap_interface, 0}) != 0 &&
                    d3d9_module.last_error().find(
                        "d3d9.dll!IDirect3D9::RegisterSoftwareDevice") !=
                        std::string::npos,
                "unimplemented IDirect3D9 method did not fail closed by name");
        require(module.read_guest("ram", 0x00402c00, value.size(), value.data()),
                "could not read imported function IAT entry");
        require(value == std::array<uint8_t, 4>{0, 0, 0, 0xf0},
                "named import IAT entry was not mapped to its guest trap");
        require(module.read_guest("ram", 0x00402c04, value.size(), value.data()),
                "could not read ordinal IAT entry");
        require(value == std::array<uint8_t, 4>{0x10, 0, 0, 0xf0},
                "ordinal import IAT entry was not mapped to its guest trap");
        require(module.read_guest("ram", 0x00402c08, value.size(),
                                  value.data()),
                "could not read GetSystemTimeAsFileTime IAT entry");
        require(value == std::array<uint8_t, 4>{0x20, 0, 0, 0xf0},
                "GetSystemTimeAsFileTime IAT entry was not mapped to its guest trap");
        for (uint32_t index = 0; index < 72; ++index) {
            const uint32_t iat_entry = read_guest_u32(
                module, "ram", 0x00402c00 + index * sizeof(uint32_t));
            require(iat_entry == 0xf0000000 + index * 0x10,
                    "Kernel32 IAT slot was not mapped to its guest trap");
        }
        require(read_guest_u32(module, "ram", 0x00402d20) == 0xf0000480 &&
                    read_guest_u32(module, "ram", 0x00402d24) == 0xf0000490 &&
                    read_guest_u32(module, "ram", 0x00402d28) == 0xf00004a0,
                "ImageHlp IAT slots were not mapped to their guest traps");
        require(read_guest_u32(module, "ram", 0x00402d40) == 0xf00004b0 &&
                    read_guest_u32(module, "ram", 0x00402d44) == 0xf00004c0,
                "WinMM timer IAT slots were not mapped to their guest traps");
        require(read_guest_u32(module, "ram", 0x00402d30) == 0xf00004d0 &&
                    read_guest_u32(module, "ram", 0x00402d34) == 0xf00004e0 &&
                    read_guest_u32(module, "ram", 0x00402d38) == 0xf00004f0,
                "Kernel32 fiber IAT slots were not mapped to their guest traps");
        require(read_guest_u32(module, "ram", 0x00402d3c) == 0xf0000500,
                "Kernel32 memory-status IAT slot was not mapped to its guest trap");
        require(invoke_import(module, 5, {}) ==
                    static_cast<uint32_t>(syscall(SYS_gettid)),
                "one-based P-code import ID did not route to its Kernel32 trap");
        constexpr uint32_t time_begin_period = 0xf00004b0;
        constexpr uint32_t time_end_period = 0xf00004c0;
        require(invoke_import(module, 76, {1}) == 0 &&
                    invoke_import(module, time_begin_period, {1}) == 0 &&
                    invoke_import(module, time_end_period, {2}) == 97 &&
                    invoke_import(module, 77, {1}) == 0 &&
                    invoke_import(module, time_end_period, {1}) == 0 &&
                    invoke_import(module, time_end_period, {1}) == 97 &&
                    invoke_import(module, time_begin_period, {0}) == 97,
                "WinMM timer requests did not enforce supported resolution and matching lifetimes");
        shift::runtime::RecompiledPcodeModule time_module(argv[1]);
        const auto time_image = time_module.load_pe32_image(argv[6]);
        const uint32_t time_get_time_stub = read_guest_u32(
            time_module, "ram", time_image.image_base + 0x2d44);
        const uint32_t time_get_before = invoke_import(
            time_module, time_get_time_stub, {});
        const uint32_t time_get_after = invoke_import(
            time_module, time_get_time_stub, {});
        require(time_get_after >= time_get_before,
                "WINMM timeGetTime did not return monotonic DWORD milliseconds");
        require(invoke_import(module, 0x00401120, {}) ==
                    static_cast<uint32_t>(syscall(SYS_gettid)),
                "absolute indirect jump thunk did not route through the guest IAT");
        constexpr uint32_t interlocked_compare_exchange = 0xf0000440;
        constexpr uint32_t interlocked_operand_address = 0x00032d00;
        write_guest_u32(module, "ram", interlocked_operand_address, 5);
        require(invoke_import(module, interlocked_compare_exchange,
                              {interlocked_operand_address, 9, 5}) == 5 &&
                    read_guest_u32(module, "ram",
                                   interlocked_operand_address) == 9 &&
                    invoke_import(module, interlocked_compare_exchange,
                                  {interlocked_operand_address, 12, 5}) == 9 &&
                    read_guest_u32(module, "ram",
                                   interlocked_operand_address) == 9,
                "InterlockedCompareExchange did not return the prior value or conditionally store");
        constexpr uint32_t virtual_alloc = 0xf0000450;
        constexpr uint32_t virtual_free = 0xf0000460;
        const uint32_t virtual_address = invoke_import(
            module, virtual_alloc, {0, 0x20000, 0x1000, 0x04});
        require(virtual_address == 0x20000000,
                "VirtualAlloc did not return an aligned guest address");
        write_guest_u32(module, "ram", virtual_address, 0x12345678);
        require(invoke_import(module, virtual_free,
                              {virtual_address, 0, 0x8000}) == 1 &&
                    invoke_import(module, virtual_alloc,
                                  {virtual_address, 0x20000, 0x3000, 0x04}) ==
                        virtual_address &&
                    read_guest_u32(module, "ram", virtual_address) == 0 &&
                    invoke_import(module, virtual_free,
                                  {virtual_address, 0, 0x8000}) == 1,
                "VirtualFree/VirtualAlloc did not release and zero a guest region");
        constexpr uint32_t module_file_name_address = 0x00032b00;
        const std::string expected_module_path = argv[4];
        require(invoke_import(module, 0xf00002d0,
                              {0, module_file_name_address, 260}) ==
                    expected_module_path.size(),
                "GetModuleFileNameA returned the wrong loaded image path length");
        std::vector<uint8_t> module_path(expected_module_path.size() + 1);
        for (size_t offset = 0; offset < module_path.size(); offset += 16) {
            const size_t size = std::min<size_t>(16, module_path.size() - offset);
            require(module.read_guest("ram", module_file_name_address + offset,
                                      size, module_path.data() + offset),
                    "could not read GetModuleFileNameA output");
        }
        require(std::string(module_path.begin(), module_path.end() - 1) ==
                    expected_module_path &&
                    module_path.back() == 0,
                "GetModuleFileNameA did not return the loaded image path");
        (void)invoke_import(module, 0xf0000250, {0});
        require(invoke_import(module, 0xf00002d0,
                              {image.image_base, module_file_name_address, 4}) == 4 &&
                    read_guest_u32(module, "ram", module_file_name_address) != 0 &&
                    invoke_import(module, 0xf0000240, {}) == 0,
                "GetModuleFileNameA did not preserve the Windows XP truncation behavior");

        require(module.call(0x00401000) == 0,
                "fixture P-code entry call failed: " + module.last_error());
        require(module.call(0x00404000) == 0,
                "P-code could not read the mapped PE image: " + module.last_error());
        require(module.dispatched_function_count() == 4,
                "nested P-code functions were not dispatched");
        require(module.unique_dispatched_function_count() == 3,
                "unique P-code function accounting did not deduplicate repeated dispatches");
        const auto filetime_now = [] {
            using Duration = std::chrono::duration<
                int64_t, std::ratio<1, 10000000>>;
            return UINT64_C(116444736000000000) +
                static_cast<uint64_t>(std::chrono::duration_cast<Duration>(
                    std::chrono::system_clock::now().time_since_epoch()).count());
        };
        const uint64_t filetime_before = filetime_now();
        require(module.call(0x00406000) == 0,
                "GetSystemTimeAsFileTime import dispatch failed: " +
                    module.last_error());
        const uint64_t filetime_after = filetime_now();
        std::array<uint8_t, 8> filetime_bytes{};
        require(module.read_guest("ram", 0x00030100, filetime_bytes.size(),
                                  filetime_bytes.data()),
                "could not read guest FILETIME result");
        uint64_t filetime = 0;
        for (size_t index = 0; index < filetime_bytes.size(); ++index) {
            filetime |= static_cast<uint64_t>(filetime_bytes[index]) <<
                        (index * 8);
        }
        require(filetime >= filetime_before && filetime <= filetime_after,
                "GetSystemTimeAsFileTime returned a value outside the call interval");
        require(module.dispatched_function_count() == 5,
                "guest clock API caller was not dispatched");
        require(module.unique_dispatched_function_count() == 4,
                "unique P-code function accounting did not include the clock caller");
        require(module.read_guest("register", 0, value.size(), value.data()),
                "could not read fixture EAX value");
        require(value == std::array<uint8_t, 4>{0x34, 0x12, 0, 0},
                "fixture did not preserve little-endian EAX bytes");
        require(module.read_guest("ram", 0x20000, value.size(), value.data()),
                "could not read fixture RAM write");
        require(value == std::array<uint8_t, 4>{'O', 'V', 'R', 'D'},
                "explicit P-code override did not replace the base export");

        require(invoke_import(module, 0xf0000030, {}) ==
                    static_cast<uint32_t>(getpid()),
                "GetCurrentProcessId returned the wrong process id");
        require(invoke_import(module, 0xf0000360, {}) == UINT32_MAX,
                "GetCurrentProcess did not return its pseudo-handle");
        require(invoke_import(module, 0xf0000370, {UINT32_MAX}) == 0x20,
                "GetPriorityClass did not report normal priority for this process");
        require(invoke_import(module, 0xf0000370, {0x12345678}) == 0,
                "GetPriorityClass accepted an unknown process handle");
        require(invoke_import(module, 0xf0000240, {}) == 6,
                "GetPriorityClass did not report an invalid handle");
        (void)invoke_import(module, 0xf0000250, {0});
        require(invoke_import(module, 0xf0000380, {}) == UINT32_MAX - 1,
                "GetCurrentThread did not return its pseudo-handle");
        require(invoke_import(module, 0xf0000390, {UINT32_MAX - 1}) == 0,
                "GetThreadPriority did not report the guest thread's default priority");
        require(invoke_import(module, 0xf00003a0, {UINT32_MAX, 0x100}) == 1 &&
                    invoke_import(module, 0xf0000370, {UINT32_MAX}) == 0x100,
                "SetPriorityClass did not update the guest process profile");
        require(invoke_import(module, 0xf00003b0,
                              {UINT32_MAX - 1, 15}) == 1 &&
                    invoke_import(module, 0xf0000390,
                                  {UINT32_MAX - 1}) == 15,
                "SetThreadPriority did not update the guest thread profile");
        require(invoke_import(module, 0xf0000480, {0x16}) == 0x16 &&
                    invoke_import(module, 0xf0000490,
                                  {UINT32_MAX, 0, 1}) == 1 &&
                    invoke_import(module, 0xf00004a0, {UINT32_MAX}) == 1,
                "ImageHlp symbol-handler setup/cleanup did not succeed");
        {
            shift::runtime::RecompiledPcodeModule stack_walk64_module(argv[1]);
            (void)stack_walk64_module.load_pe32_image(stack_walk64_fixture_path);
            constexpr uint32_t stack_walk64 = 0xf00004a0;
            constexpr uint32_t stack_frame = 0x00070000;
            constexpr uint32_t frame_pointer = 0x00072000;
            write_guest_u32(stack_walk64_module, "ram", stack_frame + 0x00,
                            0x00401100);
            write_guest_u32(stack_walk64_module, "ram", stack_frame + 0x04, 0);
            write_guest_u32(stack_walk64_module, "ram", stack_frame + 0x0c, 3);
            write_guest_u32(stack_walk64_module, "ram", stack_frame + 0x20,
                            frame_pointer);
            write_guest_u32(stack_walk64_module, "ram", stack_frame + 0x24, 0);
            write_guest_u32(stack_walk64_module, "ram", stack_frame + 0x2c, 3);
            write_guest_u32(stack_walk64_module, "ram", stack_frame + 0x30,
                            0x00071f00);
            write_guest_u32(stack_walk64_module, "ram", stack_frame + 0x34, 0);
            write_guest_u32(stack_walk64_module, "ram", stack_frame + 0x3c, 3);
            write_guest_u32(stack_walk64_module, "ram", frame_pointer,
                            frame_pointer + 0x20);
            write_guest_u32(stack_walk64_module, "ram", frame_pointer + 4,
                            0x00401234);
            write_guest_u32(stack_walk64_module, "ram", frame_pointer + 0x24,
                            0x00405678);
            require(invoke_import(stack_walk64_module, stack_walk64,
                                  {0x014c, UINT32_MAX, UINT32_MAX - 1,
                                   stack_frame, 0, 0, 0, 0, 0}) == 1 &&
                        read_guest_u32(stack_walk64_module, "ram",
                                       stack_frame + 0x00) == 0x00401234 &&
                        read_guest_u32(stack_walk64_module, "ram",
                                       stack_frame + 0x10) == 0x00405678 &&
                        read_guest_u32(stack_walk64_module, "ram",
                                       stack_frame + 0x20) ==
                            frame_pointer + 0x20 &&
                        read_guest_u32(stack_walk64_module, "ram",
                                       stack_frame + 0x30) ==
                            frame_pointer + 0x28,
                    "StackWalk64 did not advance an initialized I386 frame-pointer chain");
            write_guest_u32(stack_walk64_module, "ram", stack_frame + 0x30, 0);
            require(invoke_import(stack_walk64_module, stack_walk64,
                                  {0x014c, UINT32_MAX, UINT32_MAX - 1,
                                   stack_frame, 0, 0, 0, 0, 0}) == 0 &&
                        read_guest_u32(stack_walk64_module, "ram",
                                       stack_frame + 0x00) == 0x00401234,
                    "StackWalk64 did not fail cleanly when AddrStack was uninitialized");
        }
        constexpr uint32_t wait_for_single_object_ex = 0xf0000430;
        constexpr uint32_t manual_event = 0x00060000;
        require(invoke_import(module, 0xf00003f0, {0, 1, 1, 0}) ==
                    manual_event &&
                    invoke_import(module, 0xf0000310, {manual_event, 0}) == 0 &&
                    invoke_import(module, 0xf0000420, {manual_event}) == 1 &&
                    invoke_import(module, 0xf0000310,
                                  {manual_event, 0}) == 0x102 &&
                    invoke_import(module, wait_for_single_object_ex,
                                  {manual_event, UINT32_MAX, 0}) == UINT32_MAX &&
                    invoke_import(module, 0xf0000240, {}) == 50 &&
                    invoke_import(module, 0xf0000410, {manual_event}) == 1 &&
                    invoke_import(module, wait_for_single_object_ex,
                                  {manual_event, 0, 0}) == 0 &&
                    invoke_import(module, 0xf0000350, {manual_event}) == 1,
                "manual-reset event state did not persist through wait/reset/set/close");
        constexpr uint32_t auto_event = 0x00060004;
        require(invoke_import(module, 0xf0000400, {0, 0, 1, 0}) == auto_event &&
                    invoke_import(module, 0xf0000310, {auto_event, 0}) == 0 &&
                    invoke_import(module, 0xf0000310,
                                  {auto_event, 0}) == 0x102 &&
                    invoke_import(module, 0xf0000350, {auto_event}) == 1,
                "auto-reset event did not consume its signaled state on wait");
        constexpr char named_event_name[] = "UnsupportedNamedEvent";
        constexpr uint32_t named_event_name_address = 0x00032d80;
        write_guest_bytes(
            module, named_event_name_address,
            reinterpret_cast<const uint8_t*>(named_event_name),
            sizeof(named_event_name));
        require(invoke_import(module, 0xf0000400,
                              {0, 1, 0, named_event_name_address}) == 0 &&
                    invoke_import(module, 0xf0000240, {}) == 50,
                "CreateEventA did not fail closed for an unsupported named event");
        const std::string guest_file_path =
            "recompiled_pcode_file_fixture_" + std::to_string(getpid()) +
            ".dat";
        constexpr char guest_file_data[] = "runtime-probe";
        {
            std::ofstream file(guest_file_path, std::ios::binary | std::ios::trunc);
            require(static_cast<bool>(file),
                    "could not create guest file API fixture");
            file.write(guest_file_data, sizeof(guest_file_data) - 1);
            require(static_cast<bool>(file),
                    "could not write guest file API fixture");
        }
        constexpr uint32_t guest_file_name_address = 0x00032e00;
        write_guest_bytes(
            module, guest_file_name_address,
            reinterpret_cast<const uint8_t*>(guest_file_path.c_str()),
            guest_file_path.size() + 1);
        const uint32_t guest_file_handle = invoke_import(
            module, 0xf00003c0,
            {guest_file_name_address, 0x80000000, 1, 0, 3, 0x80, 0});
        require(guest_file_handle != UINT32_MAX,
                "CreateFileA could not open a relative read-only file");
        require(invoke_import(module, 0xf00003d0,
                              {guest_file_handle, 0}) ==
                    sizeof(guest_file_data) - 1,
                "GetFileSize returned the wrong size");
        constexpr uint32_t guest_file_buffer_address = 0x00032e40;
        constexpr uint32_t guest_file_bytes_read_address = 0x00032e80;
        require(invoke_import(
                    module, 0xf00003e0,
                    {guest_file_handle, guest_file_buffer_address,
                     sizeof(guest_file_data) - 1,
                     guest_file_bytes_read_address, 0}) == 1 &&
                    read_guest_u32(module, "ram",
                                   guest_file_bytes_read_address) ==
                        sizeof(guest_file_data) - 1,
                "ReadFile did not copy the guest file bytes");
        std::array<uint8_t, sizeof(guest_file_data) - 1> guest_file_readback{};
        require(module.read_guest("ram", guest_file_buffer_address,
                                  guest_file_readback.size(),
                                  guest_file_readback.data()) &&
                    std::equal(guest_file_readback.begin(),
                               guest_file_readback.end(), guest_file_data),
                "ReadFile returned unexpected guest file contents");

        {
            shift::runtime::RecompiledPcodeModule set_file_pointer_module(
                argv[1]);
            const auto image = set_file_pointer_module.load_pe32_image(
                set_file_pointer_fixture_path);
            require(image.import_function_count == 81,
                    "SetFilePointer PE32 fixture import count changed");
            write_guest_bytes(
                set_file_pointer_module, guest_file_name_address,
                reinterpret_cast<const uint8_t*>(guest_file_path.c_str()),
                guest_file_path.size() + 1);
            const uint32_t handle = invoke_import(
                set_file_pointer_module, 0xf00003c0,
                {guest_file_name_address, 0x80000000, 1, 0, 3, 0x80, 0});
            require(handle != UINT32_MAX,
                    "SetFilePointer fixture could not open its input file");
            constexpr uint32_t high_part_address = 0x00032ec0;
            constexpr uint32_t read_buffer_address = 0x00032e40;
            constexpr uint32_t bytes_read_address = 0x00032e80;
            write_guest_u32(set_file_pointer_module, "ram", high_part_address,
                            0);
            require(invoke_import(set_file_pointer_module, 0xf00003d0,
                                  {handle, 7, high_part_address, 0}) == 7 &&
                        read_guest_u32(set_file_pointer_module, "ram",
                                       high_part_address) == 0 &&
                        invoke_import(set_file_pointer_module, 0xf00003e0,
                                      {handle, read_buffer_address, 6,
                                       bytes_read_address, 0}) == 1,
                    "SetFilePointer did not seek from FILE_BEGIN");
            std::array<uint8_t, 6> seek_readback{};
            require(set_file_pointer_module.read_guest(
                        "ram", read_buffer_address, seek_readback.size(),
                        seek_readback.data()) &&
                        seek_readback ==
                            std::array<uint8_t, 6>{'-', 'p', 'r', 'o', 'b', 'e'},
                    "SetFilePointer FILE_BEGIN seek returned wrong bytes");
            require(invoke_import(set_file_pointer_module, 0xf00003d0,
                                  {handle, UINT32_MAX - 1, 0, 1}) == 11 &&
                        invoke_import(set_file_pointer_module, 0xf00003e0,
                                      {handle, read_buffer_address, 2,
                                       bytes_read_address, 0}) == 1,
                    "SetFilePointer did not apply a negative FILE_CURRENT offset");
            std::array<uint8_t, 2> current_readback{};
            require(set_file_pointer_module.read_guest(
                        "ram", read_buffer_address, current_readback.size(),
                        current_readback.data()) &&
                        current_readback == std::array<uint8_t, 2>{'b', 'e'},
                    "SetFilePointer FILE_CURRENT seek returned wrong bytes");
            require(invoke_import(set_file_pointer_module, 0xf00003d0,
                                  {handle, UINT32_MAX - 3, 0, 2}) == 9 &&
                        invoke_import(set_file_pointer_module, 0xf00003e0,
                                      {handle, read_buffer_address, 4,
                                       bytes_read_address, 0}) == 1,
                    "SetFilePointer did not seek backward from FILE_END");
            std::array<uint8_t, 4> end_readback{};
            require(set_file_pointer_module.read_guest(
                        "ram", read_buffer_address, end_readback.size(),
                        end_readback.data()) &&
                        end_readback == std::array<uint8_t, 4>{'r', 'o', 'b', 'e'},
                    "SetFilePointer FILE_END seek returned wrong bytes");
            require(invoke_import(set_file_pointer_module, 0xf00003d0,
                                  {handle, UINT32_MAX, 0, 0}) == UINT32_MAX &&
                        invoke_import(set_file_pointer_module, 0xf0000240,
                                      {}) == 131 &&
                        invoke_import(set_file_pointer_module, 0xf00003d0,
                                      {UINT32_MAX, 0, 0, 0}) == UINT32_MAX &&
                        invoke_import(set_file_pointer_module, 0xf0000240,
                                      {}) == 6 &&
                        invoke_import(set_file_pointer_module, 0xf00003d0,
                                      {handle, 0, 0, 3}) == UINT32_MAX &&
                        invoke_import(set_file_pointer_module, 0xf0000240,
                                      {}) == 87,
                    "SetFilePointer errors did not preserve Win32 error codes");
            require(invoke_import(set_file_pointer_module, 0xf0000350,
                                  {handle}) == 1,
                    "SetFilePointer fixture did not close its file handle");
        }

        {
            shift::runtime::RecompiledPcodeModule write_file_module(argv[1]);
            const auto write_file_image =
                write_file_module.load_pe32_image(write_file_fixture_path);
            require(write_file_image.import_function_count == 81,
                    "WriteFile PE32 fixture import count changed");
            std::array<uint8_t, 0x58> write_file_buffer{};
            for (size_t index = 0; index < write_file_buffer.size(); ++index)
                write_file_buffer[index] = static_cast<uint8_t>(index);
            write_guest_bytes(write_file_module, 0x00032e40,
                              write_file_buffer.data(),
                              write_file_buffer.size());
            require(invoke_import(
                        write_file_module, 0xf00003e0,
                        {UINT32_MAX, 0x00032e40,
                         static_cast<uint32_t>(write_file_buffer.size()),
                         0x00032e80, 0}) == 0 &&
                        invoke_import(write_file_module, 0xf0000240, {}) == 6,
                    "WriteFile did not report INVALID_HANDLE_VALUE");
            const std::string guest_write_file_path =
                "recompiled_pcode_writefile_fixture_" +
                std::to_string(getpid()) + ".dat";
            std::filesystem::remove(guest_write_file_path);
            write_guest_bytes(
                write_file_module, 0x00032e00,
                reinterpret_cast<const uint8_t*>(guest_write_file_path.c_str()),
                guest_write_file_path.size() + 1);
            const uint32_t writable_handle = invoke_import(
                write_file_module, 0xf00003c0,
                {0x00032e00, 0xc0000000, 1, 0, 4, 0x80, 0});
            require(writable_handle != UINT32_MAX,
                    "CreateFileA did not create an OPEN_ALWAYS read/write file");
            require(invoke_import(
                        write_file_module, 0xf00003e0,
                        {writable_handle, 0x00032e40,
                         static_cast<uint32_t>(write_file_buffer.size()),
                         0x00032e80, 0}) == 1 &&
                        read_guest_u32(write_file_module, "ram", 0x00032e80) ==
                            write_file_buffer.size(),
                    "WriteFile did not write and report the guest byte count");
            std::ifstream written_file(guest_write_file_path,
                                       std::ios::binary);
            std::vector<uint8_t> written_bytes(
                std::istreambuf_iterator<char>(written_file), {});
            require(written_file.good() || written_file.eof(),
                    "could not read back the guest WriteFile fixture");
            require(written_bytes == std::vector<uint8_t>(
                                         write_file_buffer.begin(),
                                         write_file_buffer.end()),
                    "WriteFile produced unexpected host file bytes");
            require(invoke_import(write_file_module, 0xf0000350,
                                  {writable_handle}) == 1,
                    "CloseHandle did not close the writable guest file");
            std::filesystem::remove(guest_write_file_path);
        }

        {
            shift::runtime::RecompiledPcodeModule read_file_ex_module(argv[1]);
            const auto read_file_ex_image =
                read_file_ex_module.load_pe32_image(read_file_ex_fixture_path);
            require(read_file_ex_image.import_function_count == 81,
                    "ReadFileEx PE32 fixture import count changed");
            const uint32_t path_address = 0x00032e00;
            write_guest_bytes(
                read_file_ex_module, path_address,
                reinterpret_cast<const uint8_t*>(guest_file_path.c_str()),
                guest_file_path.size() + 1);
            const uint32_t handle = invoke_import(
                read_file_ex_module, 0xf00003c0,
                {path_address, 0x80000000, 1, 0, 3, 0x80, 0});
            require(handle != UINT32_MAX,
                    "ReadFileEx fixture could not open its input file");
            constexpr uint32_t buffer_address = 0x00032e40;
            constexpr uint32_t overlapped_address = 0x00032f00;
            constexpr uint32_t completion_record = 0x00020100;
            constexpr uint32_t completion_routine = 0x0040d100;
            const uint32_t event_handle = invoke_import(
                read_file_ex_module, 0xf0000400, {0, 0, 0, 0});
            require(event_handle != 0,
                    "ReadFileEx fixture could not create its wait event");
            write_guest_u32(read_file_ex_module, "ram", overlapped_address,
                            UINT32_MAX);
            write_guest_u32(read_file_ex_module, "ram",
                            overlapped_address + 4, UINT32_MAX);
            write_guest_u32(read_file_ex_module, "ram",
                            overlapped_address + 8, 8);
            write_guest_u32(read_file_ex_module, "ram",
                            overlapped_address + 12, 0);
            write_guest_u32(read_file_ex_module, "ram",
                            overlapped_address + 16, 0);
            require(invoke_import(
                        read_file_ex_module, 0xf00003e0,
                        {handle, buffer_address, 5, overlapped_address,
                         completion_routine}) == 1 &&
                        read_guest_u32(read_file_ex_module, "ram",
                                       overlapped_address) == 0 &&
                        read_guest_u32(read_file_ex_module, "ram",
                                       overlapped_address + 4) == 5,
                    "ReadFileEx did not complete the overlapped read");
            std::array<uint8_t, 5> read_file_ex_bytes{};
            require(read_file_ex_module.read_guest(
                        "ram", buffer_address, read_file_ex_bytes.size(),
                        read_file_ex_bytes.data()) &&
                        read_file_ex_bytes ==
                            std::array<uint8_t, 5>{'p', 'r', 'o', 'b', 'e'},
                    "ReadFileEx did not honor the OVERLAPPED file offset");
            const uint32_t non_alertable_result = invoke_import(
                read_file_ex_module, 0xf0000430, {event_handle, 0, 0});
            const uint32_t callback_before_alertable_wait =
                read_guest_u32(read_file_ex_module, "ram", completion_record);
            require(non_alertable_result == 0x102 &&
                        callback_before_alertable_wait == 0,
                    "non-alertable wait result=" +
                        std::to_string(non_alertable_result) +
                        " callback_error=" +
                        std::to_string(callback_before_alertable_wait));
            require(invoke_import(read_file_ex_module, 0xf0000430,
                                  {event_handle, 0, 1}) == 0x000000c0 &&
                        read_guest_u32(read_file_ex_module, "ram",
                                       completion_record) == 0 &&
                        read_guest_u32(read_file_ex_module, "ram",
                                       completion_record + 4) == 5 &&
                        read_guest_u32(read_file_ex_module, "ram",
                                       completion_record + 8) ==
                            overlapped_address,
                    "alertable wait did not dispatch ReadFileEx completion");
            require(invoke_import(read_file_ex_module, 0xf0000350, {handle}) ==
                        1,
                    "ReadFileEx fixture did not close its file handle");
            require(invoke_import(read_file_ex_module, 0xf0000350,
                                  {event_handle}) == 1,
                    "ReadFileEx fixture did not close its wait event");
        }
        require(invoke_import(module, 0xf0000350, {guest_file_handle}) == 1,
                "CloseHandle did not close the guest file");
        std::filesystem::remove(guest_file_path);

        const std::string guest_directory_path =
            "recompiled_pcode_directory_fixture_" + std::to_string(getpid());
        require(std::filesystem::create_directory(guest_directory_path),
                "could not create guest directory API fixture");
        write_guest_bytes(
            module, guest_file_name_address,
            reinterpret_cast<const uint8_t*>(guest_directory_path.c_str()),
            guest_directory_path.size() + 1);
        const uint32_t guest_directory_handle = invoke_import(
            module, 0xf00003c0,
            {guest_file_name_address, 0, 1, 0, 3, 0x02000003, 0});
        require(guest_directory_handle != UINT32_MAX,
                "CreateFileA could not open a directory with backup semantics");
        require(invoke_import(module, 0xf00003d0,
                              {guest_directory_handle, 0}) == 0,
                "GetFileSize did not return the directory handle size");
        require(invoke_import(
                    module, 0xf00003e0,
                    {guest_directory_handle, guest_file_buffer_address, 1,
                     guest_file_bytes_read_address, 0}) == 0 &&
                    invoke_import(module, 0xf0000240, {}) == 5,
                "ReadFile did not reject a directory handle with access denied");
        require(invoke_import(module, 0xf0000350,
                              {guest_directory_handle}) == 1,
                "CloseHandle did not close the guest directory");
        std::filesystem::remove(guest_directory_path);

        const std::string case_path_root =
            "CaseSensitiveFileFixture-" + std::to_string(getpid());
        const std::filesystem::path case_path_directory =
            std::filesystem::current_path() / case_path_root / "Pakfiles";
        std::filesystem::create_directories(case_path_directory);
        constexpr char case_path_file[] = "BOOTPERSISTENT.bff";
        constexpr char case_path_contents[] = "case-folded-path";
        {
            std::ofstream file(case_path_directory / case_path_file,
                               std::ios::binary | std::ios::trunc);
            require(static_cast<bool>(file),
                    "could not create mixed-case guest path fixture");
            file.write(case_path_contents, sizeof(case_path_contents) - 1);
            require(static_cast<bool>(file),
                    "could not write mixed-case guest path fixture");
        }
        const std::string case_guest_path =
            "C:\\" + case_path_root + "\\pakfiles\\bootpersistent.bff";
        constexpr uint32_t case_guest_path_address = 0x00032eb0;
        write_guest_bytes(
            module, case_guest_path_address,
            reinterpret_cast<const uint8_t*>(case_guest_path.c_str()),
            case_guest_path.size() + 1);
        const uint32_t case_guest_file_handle = invoke_import(
            module, 0xf00003c0,
            {case_guest_path_address, 0x80000000, 1, 0, 3, 0x80, 0});
        require(case_guest_file_handle != UINT32_MAX &&
                    invoke_import(module, 0xf00003d0,
                                  {case_guest_file_handle, 0}) ==
                        sizeof(case_path_contents) - 1 &&
                    invoke_import(module, 0xf0000350,
                                  {case_guest_file_handle}) == 1,
                "CreateFileA did not resolve Windows-style case-insensitive path components");
        std::filesystem::remove_all(case_path_directory.parent_path());
        require(invoke_import(module, 0xf0000040, {}) ==
                    static_cast<uint32_t>(syscall(SYS_gettid)),
                "GetCurrentThreadId returned the wrong thread id");
        const auto tick_millis = [] {
            return static_cast<uint32_t>(std::chrono::duration_cast<
                std::chrono::milliseconds>(
                    std::chrono::steady_clock::now().time_since_epoch()).count());
        };
        const uint32_t tick_before = tick_millis();
        const uint32_t tick_count = invoke_import(module, 0xf0000050, {});
        const uint32_t tick_after = tick_millis();
        require(static_cast<uint32_t>(tick_count - tick_before) <=
                    static_cast<uint32_t>(tick_after - tick_before),
                "GetTickCount returned a value outside the call interval");

        constexpr uint32_t performance_value_address = 0x00032100;
        const auto performance_now = [] {
            return static_cast<uint64_t>(std::chrono::duration_cast<
                std::chrono::nanoseconds>(
                    std::chrono::steady_clock::now().time_since_epoch()).count());
        };
        const uint64_t counter_before = performance_now();
        require(invoke_import(module, 0xf0000060,
                              {performance_value_address}) == 1,
                "QueryPerformanceCounter did not return TRUE");
        const uint64_t counter_after = performance_now();
        const uint64_t counter = read_guest_u64(
            module, "ram", performance_value_address);
        require(counter >= counter_before && counter <= counter_after,
                "QueryPerformanceCounter returned a value outside the call interval");
        require(invoke_import(module, 0xf0000070,
                              {performance_value_address}) == 1,
                "QueryPerformanceFrequency did not return TRUE");
        require(read_guest_u64(module, "ram", performance_value_address) ==
                    UINT64_C(1000000000),
                "QueryPerformanceFrequency did not match the nanosecond counter");
        constexpr uint32_t startup_info_address = 0x00032140;
        (void)invoke_import(module, 0xf0000080, {startup_info_address});
        require(read_guest_u32(module, "ram", startup_info_address) == 68,
                "GetStartupInfoA returned an invalid structure size");
        for (uint32_t offset = 4; offset < 68; offset += 4)
            require(read_guest_u32(module, "ram", startup_info_address + offset) == 0,
                    "GetStartupInfoA populated an unsupported process field");
        require(invoke_import(module, 0xf0000090, {}) == 0x00010000,
                "GetProcessHeap returned the wrong guest heap handle");
        write_guest_u32(module, "ram", 0x10000000, 0xdeadbeef);
        const uint32_t first_allocation = invoke_import(
            module, 0xf00000a0, {0x00010000, 0x8, 16});
        require(first_allocation == 0x10000000 &&
                    (first_allocation & 0xf) == 0,
                "HeapAlloc did not return an aligned guest range");
        require(read_guest_u32(module, "ram", first_allocation) == 0,
                "HeapAlloc ignored HEAP_ZERO_MEMORY");
        require(invoke_import(module, 0xf00002f0,
                              {0x00010000, 0, first_allocation}) == 16,
                "HeapSize did not report the aligned live allocation size");
        write_guest_u32(module, "ram", first_allocation, 0x12345678);
        require(invoke_import(module, 0xf0000470,
                              {0x00010000, 0x10, first_allocation, 32}) == 0 &&
                    read_guest_u32(module, "ram", first_allocation) ==
                        0x12345678 &&
                    invoke_import(module, 0xf00002f0,
                                  {0x00010000, 0, first_allocation}) == 16,
                "in-place-only HeapReAlloc did not preserve the original block on failure");
        const uint32_t resized_allocation = invoke_import(
            module, 0xf0000470,
            {0x00010000, 0x8, first_allocation, 32});
        require(resized_allocation != 0 &&
                    resized_allocation != first_allocation &&
                    read_guest_u32(module, "ram", resized_allocation) ==
                        0x12345678 &&
                    invoke_import(module, 0xf00002f0,
                                  {0x00010000, 0, resized_allocation}) == 32,
                "HeapReAlloc did not move and preserve a growing allocation");
        std::array<uint8_t, 16> zeroed_reallocation_tail{};
        require(module.read_guest("ram", resized_allocation + 16,
                                  zeroed_reallocation_tail.size(),
                                  zeroed_reallocation_tail.data()) &&
                    zeroed_reallocation_tail == std::array<uint8_t, 16>{},
                "HEAP_ZERO_MEMORY did not clear the expanded HeapReAlloc range");
        const uint32_t second_allocation = invoke_import(
            module, 0xf00000a0, {0x00010000, 0, 32});
        require(second_allocation > first_allocation &&
                    (second_allocation & 0xf) == 0,
                "HeapAlloc did not advance its aligned guest range");
        require(invoke_import(module, 0xf00002f0,
                              {0x00010000, 0, second_allocation}) == 32,
                "HeapSize did not report the second live allocation size");
        require(invoke_import(module, 0xf00000c0,
                              {0x00010000, 0, resized_allocation}) == 1 &&
                    invoke_import(module, 0xf00000c0,
                                  {0x00010000, 0, second_allocation}) == 1,
                "HeapFree did not release tracked guest allocations");
        const uint32_t private_heap = invoke_import(
            module, 0xf00000d0, {0, 0, 0});
        require(private_heap == 0x00010004,
                "HeapCreate did not return a unique guest heap handle");
        const uint32_t private_allocation = invoke_import(
            module, 0xf00000a0, {private_heap, 0, 32});
        require(invoke_import(module, 0xf00000c0,
                              {private_heap, 0, private_allocation}) == 1,
                "private guest heap allocation could not be freed");
        constexpr uint32_t dynamic_api_name_address = 0x00032300;
        constexpr char dynamic_api_name[] = "GetModuleHandleA";
        require(module.write_guest("ram", dynamic_api_name_address,
                                   sizeof(dynamic_api_name) - 1,
                                   reinterpret_cast<const uint8_t*>(
                                       dynamic_api_name)) &&
                    module.write_guest("ram", dynamic_api_name_address +
                                                   sizeof(dynamic_api_name) - 1,
                                       1, reinterpret_cast<const uint8_t*>(
                                              dynamic_api_name +
                                              sizeof(dynamic_api_name) - 1)),
                "could not write GetModuleHandleA lookup name");
        const uint32_t get_module_handle_a = invoke_import(
            module, 0xf00000e0, {0xe0000000, dynamic_api_name_address});
        require(get_module_handle_a == 0xd0000000,
                "GetProcAddress did not create a dynamic import trap");
        require(invoke_import(module, 0xf00000e0,
                              {0xe0000000, image.image_base + 0x2242}) ==
                    0xf0000020,
                "GetProcAddress did not resolve an existing import trap");
        require(invoke_import(module, get_module_handle_a, {0}) ==
                    image.image_base,
                "GetModuleHandleA(NULL) did not return the PE ImageBase");
        require(invoke_import(module, get_module_handle_a,
                              {image.image_base + 0x2de0}) == 0xe0000000,
                "GetModuleHandleA did not resolve an imported module name");
        uint32_t dynamic_api_string_address = 0x00034000;
        const auto resolve_kernel32_api = [&](const char* name) {
            const size_t length = std::strlen(name) + 1;
            const auto* bytes = reinterpret_cast<const uint8_t*>(name);
            for (size_t offset = 0; offset < length; offset += 16) {
                const size_t chunk = std::min<size_t>(16, length - offset);
                require(module.write_guest("ram",
                                           dynamic_api_string_address + offset,
                                           chunk, bytes + offset),
                        std::string("could not write ") + name +
                            " lookup name");
            }
            const uint32_t address = invoke_import(
                module, 0xf00000e0,
                {0xe0000000, dynamic_api_string_address});
            dynamic_api_string_address +=
                static_cast<uint32_t>((length + 15) & ~size_t(15));
            require(address != 0,
                    std::string("GetProcAddress did not resolve ") + name);
            return address;
        };
        const uint32_t get_module_handle_w =
            resolve_kernel32_api("GetModuleHandleW");
        constexpr uint32_t wide_module_name_address = 0x00035400;
        constexpr char16_t kernel32_module_name[] = u"KERNEL32.DLL";
        constexpr char16_t missing_wide_module_name[] = u"missing.dll";
        static_assert(sizeof(char16_t) == 2);
        write_guest_bytes(
            module, wide_module_name_address,
            reinterpret_cast<const uint8_t*>(kernel32_module_name),
            sizeof(kernel32_module_name));
        require(invoke_import(module, get_module_handle_w, {0}) ==
                        image.image_base &&
                    invoke_import(module, get_module_handle_w,
                                  {wide_module_name_address}) == 0xe0000000,
                "GetModuleHandleW did not resolve the image and imported module");
        write_guest_bytes(
            module, wide_module_name_address,
            reinterpret_cast<const uint8_t*>(missing_wide_module_name),
            sizeof(missing_wide_module_name));
        require(invoke_import(module, get_module_handle_w,
                              {wide_module_name_address}) == 0,
                "GetModuleHandleW resolved a module absent from the PE imports");
        const uint32_t get_current_directory_api =
            resolve_kernel32_api("GetCurrentDirectoryA");
        const uint32_t set_current_directory_api =
            resolve_kernel32_api("SetCurrentDirectoryA");
        constexpr uint32_t current_directory_address = 0x00032c00;
        constexpr uint32_t current_directory_input_address = 0x00035000;
        constexpr char guest_root_directory[] = "C:\\";
        const std::string expected_current_directory = guest_root_directory;
        const uint32_t required_current_directory_size =
            static_cast<uint32_t>(expected_current_directory.size() + 1);
        require(invoke_import(module, get_current_directory_api,
                              {260, current_directory_address}) ==
                    expected_current_directory.size(),
                "GetCurrentDirectoryA returned the wrong path length");
        std::vector<uint8_t> current_directory_bytes(
            expected_current_directory.size() + 1);
        for (size_t offset = 0; offset < current_directory_bytes.size();
             offset += 16) {
            const size_t size = std::min<size_t>(
                16, current_directory_bytes.size() - offset);
            require(module.read_guest("ram", current_directory_address + offset,
                                      size,
                                      current_directory_bytes.data() + offset),
                    "could not read GetCurrentDirectoryA output");
        }
        require(std::string(current_directory_bytes.begin(),
                            current_directory_bytes.end() - 1) ==
                        expected_current_directory &&
                    current_directory_bytes.back() == 0 &&
                    invoke_import(module, get_current_directory_api, {0, 0}) ==
                        required_current_directory_size &&
                    invoke_import(module, get_current_directory_api,
                                  {1, current_directory_address}) ==
                        required_current_directory_size,
                "GetCurrentDirectoryA did not preserve required-size semantics");

        const std::string cwd_fixture_name =
            "recompiled_pcode_cwd_fixture_" + std::to_string(getpid());
        const std::filesystem::path cwd_fixture_host_path =
            std::filesystem::current_path() / cwd_fixture_name;
        std::filesystem::create_directories(cwd_fixture_host_path);
        const std::string absolute_cwd_fixture_path =
            "C:\\" + cwd_fixture_name;
        write_guest_bytes(
            module, current_directory_input_address,
            reinterpret_cast<const uint8_t*>(absolute_cwd_fixture_path.c_str()),
            absolute_cwd_fixture_path.size() + 1);
        require(invoke_import(module, set_current_directory_api,
                              {current_directory_input_address}) == 1,
                "SetCurrentDirectoryA could not set an absolute guest path");
        const std::string changed_guest_directory = absolute_cwd_fixture_path;
        require(invoke_import(module, get_current_directory_api,
                              {260, current_directory_address}) ==
                    changed_guest_directory.size(),
                "GetCurrentDirectoryA did not observe the new guest directory");

        constexpr char relative_guest_file_name[] = "relative-file.dat";
        constexpr char relative_guest_file_contents[] = "guest-cwd";
        {
            std::ofstream file(cwd_fixture_host_path /
                                   relative_guest_file_name,
                               std::ios::binary | std::ios::trunc);
            require(static_cast<bool>(file),
                    "could not create relative guest file fixture");
            file.write(relative_guest_file_contents,
                       sizeof(relative_guest_file_contents) - 1);
            require(static_cast<bool>(file),
                    "could not write relative guest file fixture");
        }
        constexpr uint32_t relative_guest_file_name_address = 0x00035100;
        write_guest_bytes(
            module, relative_guest_file_name_address,
            reinterpret_cast<const uint8_t*>(relative_guest_file_name),
            sizeof(relative_guest_file_name));
        const uint32_t relative_guest_file_handle = invoke_import(
            module, 0xf00003c0,
            {relative_guest_file_name_address, 0x80000000, 1, 0, 3, 0x80, 0});
        require(relative_guest_file_handle != UINT32_MAX &&
                    invoke_import(module, 0xf0000350,
                                  {relative_guest_file_handle}) == 1,
                "CreateFileA did not resolve a path from the guest directory");

        constexpr char missing_guest_directory[] = "missing-guest-directory";
        write_guest_bytes(
            module, current_directory_input_address,
            reinterpret_cast<const uint8_t*>(missing_guest_directory),
            sizeof(missing_guest_directory));
        require(invoke_import(module, set_current_directory_api,
                              {current_directory_input_address}) == 0 &&
                    invoke_import(module, 0xf0000240, {}) == 3,
                "SetCurrentDirectoryA did not report a missing directory");
        constexpr char unsupported_guest_drive[] = "D:\\";
        write_guest_bytes(
            module, current_directory_input_address,
            reinterpret_cast<const uint8_t*>(unsupported_guest_drive),
            sizeof(unsupported_guest_drive));
        require(invoke_import(module, set_current_directory_api,
                              {current_directory_input_address}) == 0 &&
                    invoke_import(module, 0xf0000240, {}) == 15,
                "SetCurrentDirectoryA accepted an unsupported drive");
        constexpr char escaping_guest_path[] = "C:\\..\\..";
        write_guest_bytes(
            module, current_directory_input_address,
            reinterpret_cast<const uint8_t*>(escaping_guest_path),
            sizeof(escaping_guest_path));
        require(invoke_import(module, set_current_directory_api,
                              {current_directory_input_address}) == 0 &&
                    invoke_import(module, 0xf0000240, {}) == 5,
                "SetCurrentDirectoryA allowed a path outside the guest root");

        constexpr char guest_root_path[] = "C:\\";
        write_guest_bytes(
            module, current_directory_input_address,
            reinterpret_cast<const uint8_t*>(guest_root_path),
            sizeof(guest_root_path));
        require(invoke_import(module, set_current_directory_api,
                              {current_directory_input_address}) == 1 &&
                    invoke_import(module, get_current_directory_api,
                                  {260, current_directory_address}) ==
                        expected_current_directory.size(),
                "SetCurrentDirectoryA did not restore the guest root");

        const uint32_t delete_file_api = resolve_kernel32_api("DeleteFileA");
        const uint32_t delete_file_last_error_api =
            resolve_kernel32_api("GetLastError");
        constexpr uint32_t delete_file_path_address = 0x00035200;
        const std::string delete_file_name =
            "delete-file-fixture-" + std::to_string(getpid()) + ".dat";
        const std::filesystem::path delete_file_host_path =
            std::filesystem::current_path() / delete_file_name;
        {
            std::ofstream file(delete_file_host_path,
                               std::ios::binary | std::ios::trunc);
            require(static_cast<bool>(file),
                    "could not create DeleteFileA fixture");
            file << "delete me";
            require(static_cast<bool>(file),
                    "could not write DeleteFileA fixture");
        }
        write_guest_bytes(
            module, delete_file_path_address,
            reinterpret_cast<const uint8_t*>(delete_file_name.c_str()),
            delete_file_name.size() + 1);
        require(invoke_import(module, delete_file_api,
                              {delete_file_path_address}) == 1 &&
                    !std::filesystem::exists(delete_file_host_path),
                "DeleteFileA did not delete a guest-root file");

        constexpr char missing_delete_file[] = "missing-delete-file-fixture";
        write_guest_bytes(
            module, delete_file_path_address,
            reinterpret_cast<const uint8_t*>(missing_delete_file),
            sizeof(missing_delete_file));
        require(invoke_import(module, delete_file_api,
                              {delete_file_path_address}) == 0 &&
                    invoke_import(module, delete_file_last_error_api, {}) == 2,
                "DeleteFileA did not report ERROR_FILE_NOT_FOUND");

        const std::string read_only_delete_file_name =
            "delete-file-read-only-" + std::to_string(getpid()) + ".dat";
        const std::filesystem::path read_only_delete_file_host_path =
            std::filesystem::current_path() / read_only_delete_file_name;
        {
            std::ofstream file(read_only_delete_file_host_path,
                               std::ios::binary | std::ios::trunc);
            require(static_cast<bool>(file),
                    "could not create read-only DeleteFileA fixture");
            file << "read only";
        }
        std::error_code permissions_error;
        std::filesystem::permissions(
            read_only_delete_file_host_path,
            std::filesystem::perms::owner_read |
                std::filesystem::perms::group_read |
                std::filesystem::perms::others_read,
            std::filesystem::perm_options::replace, permissions_error);
        require(!permissions_error,
                "could not mark DeleteFileA fixture read-only");
        write_guest_bytes(
            module, delete_file_path_address,
            reinterpret_cast<const uint8_t*>(read_only_delete_file_name.c_str()),
            read_only_delete_file_name.size() + 1);
        require(invoke_import(module, delete_file_api,
                              {delete_file_path_address}) == 0 &&
                    invoke_import(module, delete_file_last_error_api, {}) == 5 &&
                    std::filesystem::exists(read_only_delete_file_host_path),
                "DeleteFileA did not deny deletion of a read-only file");
        std::filesystem::permissions(
            read_only_delete_file_host_path,
            std::filesystem::perms::owner_all,
            std::filesystem::perm_options::add, permissions_error);
        require(!permissions_error,
                "could not restore DeleteFileA fixture permissions");
        std::filesystem::remove(read_only_delete_file_host_path, permissions_error);
        require(!permissions_error,
                "could not remove read-only DeleteFileA fixture");

        const std::string symlink_target_name =
            "delete-file-symlink-target-" + std::to_string(getpid()) + ".dat";
        const std::string symlink_name =
            "delete-file-symlink-" + std::to_string(getpid()) + ".dat";
        const std::filesystem::path symlink_target_path =
            std::filesystem::current_path() / symlink_target_name;
        const std::filesystem::path symlink_path =
            std::filesystem::current_path() / symlink_name;
        {
            std::ofstream file(symlink_target_path,
                               std::ios::binary | std::ios::trunc);
            require(static_cast<bool>(file),
                    "could not create DeleteFileA symlink target");
            file << "keep target";
        }
        std::filesystem::create_symlink(symlink_target_path, symlink_path);
        write_guest_bytes(
            module, delete_file_path_address,
            reinterpret_cast<const uint8_t*>(symlink_name.c_str()),
            symlink_name.size() + 1);
        require(invoke_import(module, delete_file_api,
                              {delete_file_path_address}) == 1 &&
                    !std::filesystem::exists(symlink_path) &&
                    std::filesystem::exists(symlink_target_path),
                "DeleteFileA did not remove only the guest symlink");
        std::filesystem::remove(symlink_target_path, permissions_error);
        require(!permissions_error,
                "could not remove DeleteFileA symlink target fixture");

        constexpr char escaping_delete_file[] = "C:\\..\\outside-delete-file";
        write_guest_bytes(
            module, delete_file_path_address,
            reinterpret_cast<const uint8_t*>(escaping_delete_file),
            sizeof(escaping_delete_file));
        require(invoke_import(module, delete_file_api,
                              {delete_file_path_address}) == 0 &&
                    invoke_import(module, delete_file_last_error_api, {}) == 5,
                "DeleteFileA allowed a path outside the guest root");
        std::filesystem::remove_all(cwd_fixture_host_path);
        const uint32_t create_thread_api = resolve_kernel32_api("CreateThread");
        const uint32_t suspend_thread_api = resolve_kernel32_api("SuspendThread");
        const uint32_t resume_thread_api = resolve_kernel32_api("ResumeThread");
        const uint32_t exit_code_thread_api =
            resolve_kernel32_api("GetExitCodeThread");
        const uint32_t thread_priority_api =
            resolve_kernel32_api("SetThreadPriority");
        const uint32_t get_thread_priority_api =
            resolve_kernel32_api("GetThreadPriority");
        const uint32_t thread_ideal_processor_api =
            resolve_kernel32_api("SetThreadIdealProcessor");
        const uint32_t get_last_error_api = resolve_kernel32_api("GetLastError");
        const uint32_t set_last_error_api = resolve_kernel32_api("SetLastError");
        const uint32_t output_debug_string_api =
            resolve_kernel32_api("OutputDebugStringA");
        constexpr char debug_string[] = "P-code debug output fixture";
        constexpr uint32_t debug_string_address = 0x00035500;
        write_guest_bytes(
            module, debug_string_address,
            reinterpret_cast<const uint8_t*>(debug_string),
            sizeof(debug_string));
        require(invoke_import(module, output_debug_string_api,
                              {debug_string_address}) == 0,
                "OutputDebugStringA did not complete with no debugger attached");
        const uint32_t sleep_ex_api = resolve_kernel32_api("SleepEx");
        require(invoke_import(module, sleep_ex_api, {0, 1}) == 0 &&
                    invoke_import(module, sleep_ex_api, {1, 0}) == 0,
                "SleepEx did not return zero after its timeout");
        const uint32_t interlocked_exchange_api =
            resolve_kernel32_api("InterlockedExchange");
        write_guest_u32(module, "ram", interlocked_operand_address,
                        0x80000000);
        require(invoke_import(module, interlocked_exchange_api,
                              {interlocked_operand_address, 7}) ==
                    0x80000000 &&
                    read_guest_u32(module, "ram",
                                   interlocked_operand_address) == 7,
                "InterlockedExchange did not return the prior value and store the replacement");
        const uint32_t wait_thread_api =
            resolve_kernel32_api("WaitForSingleObject");
        const uint32_t close_thread_api = resolve_kernel32_api("CloseHandle");
        const uint32_t exit_thread_api = resolve_kernel32_api("ExitThread");
        constexpr uint32_t thread_id_address = 0x00034200;
        constexpr uint32_t thread_exit_code_address = 0x00034204;
        write_guest_u32(module, "ram", 0x00034208, exit_thread_api);
        write_guest_u32(module, "ram", 0x0003420c, 0);
        const uint32_t guest_thread = invoke_import(
            module, create_thread_api,
            {0, 0, 0x0040c000, 0x12345678, 0x4, thread_id_address});
        require(guest_thread != 0 &&
                    read_guest_u32(module, "ram", thread_id_address) != 0 &&
                    invoke_import(module, wait_thread_api,
                                  {guest_thread, 0}) == 0x102 &&
                    invoke_import(module, exit_code_thread_api,
                                  {guest_thread, thread_exit_code_address}) == 1 &&
                    read_guest_u32(module, "ram", thread_exit_code_address) ==
                        259,
                "CreateThread did not preserve a suspended guest thread");
        require(invoke_import(module, thread_priority_api,
                              {guest_thread, 2}) == 1 &&
                    invoke_import(module, get_thread_priority_api,
                                  {guest_thread}) == 2 &&
                    invoke_import(module, suspend_thread_api,
                                  {guest_thread}) == 1 &&
                    invoke_import(module, resume_thread_api,
                                  {guest_thread}) == 2 &&
                    read_guest_u32(module, "ram", thread_exit_code_address) ==
                        259 &&
                    invoke_import(module, resume_thread_api,
                                  {guest_thread}) == 1 &&
                    invoke_import(module, exit_code_thread_api,
                                  {guest_thread, thread_exit_code_address}) == 1 &&
                    read_guest_u32(module, "ram", thread_exit_code_address) ==
                        0xbeef &&
                    invoke_import(module, wait_thread_api,
                                  {guest_thread, UINT32_MAX}) == 0,
                "guest thread resume, return, wait or cleanup failed");
        require(invoke_import(module, thread_ideal_processor_api,
                              {guest_thread, 32}) == 0 &&
                    invoke_import(module, thread_ideal_processor_api,
                                  {guest_thread, 1}) == 0 &&
                    invoke_import(module, thread_ideal_processor_api,
                                  {guest_thread, 32}) == 1 &&
                    invoke_import(module, thread_ideal_processor_api,
                                  {guest_thread, 0}) == 1,
                "SetThreadIdealProcessor did not query and update guest thread state");
        require(invoke_import(module, thread_ideal_processor_api,
                              {UINT32_MAX, 0}) == UINT32_MAX &&
                    invoke_import(module, get_last_error_api, {}) == 6,
                "SetThreadIdealProcessor accepted an invalid thread handle");
        (void)invoke_import(module, set_last_error_api, {0});
        require(invoke_import(module, thread_ideal_processor_api,
                              {guest_thread, 33}) == UINT32_MAX &&
                    invoke_import(module, get_last_error_api, {}) == 87,
                "SetThreadIdealProcessor accepted an invalid processor index");
        (void)invoke_import(module, set_last_error_api, {0});
        require(invoke_import(module, thread_ideal_processor_api,
                              {UINT32_MAX - 1, 3}) == 0 &&
                    invoke_import(module, thread_ideal_processor_api,
                                  {UINT32_MAX - 1, 32}) == 3 &&
                    invoke_import(module, thread_ideal_processor_api,
                                  {UINT32_MAX - 1, 0}) == 3,
                "SetThreadIdealProcessor did not track the current guest thread");
        require(invoke_import(module, close_thread_api, {guest_thread}) == 1,
                "completed guest thread handle could not be closed");
        constexpr uint32_t exit_thread_id_address = 0x00034210;
        const uint32_t exiting_guest_thread = invoke_import(
            module, create_thread_api,
            {0, 0, 0x0040c100, 0x12345678, 0x4, exit_thread_id_address});
        require(exiting_guest_thread != 0 &&
                    invoke_import(module, resume_thread_api,
                                  {exiting_guest_thread}) == 1 &&
                    invoke_import(module, exit_code_thread_api,
                                  {exiting_guest_thread,
                                   thread_exit_code_address}) == 1 &&
                    read_guest_u32(module, "ram", thread_exit_code_address) ==
                        0xbeef &&
                    read_guest_u32(module, "ram", 0x0003420c) == 0 &&
                    invoke_import(module, wait_thread_api,
                                  {exiting_guest_thread, UINT32_MAX}) == 0 &&
                    invoke_import(module, close_thread_api,
                                  {exiting_guest_thread}) == 1,
                "ExitThread did not stop guest execution with its requested code");
        constexpr char missing_module[] = "missing.dll";
        require(module.write_guest("ram", 0x00032300, sizeof(missing_module),
                                   reinterpret_cast<const uint8_t*>(missing_module)),
                "could not write missing module name");
        require(invoke_import(module, get_module_handle_a,
                              {0x00032300}) == 0,
                "GetModuleHandleA resolved a module absent from the PE imports");
        const uint32_t tls_index = invoke_import(module, 0xf00000f0, {});
        require(tls_index == 0 &&
                    invoke_import(module, 0xf0000100, {tls_index}) == 0,
                "TlsAlloc or initial TlsGetValue returned an invalid value");
        require(invoke_import(module, 0xf0000110,
                              {tls_index, 0x12345678}) == 1 &&
                    invoke_import(module, 0xf0000100, {tls_index}) ==
                        0x12345678,
                "TlsSetValue did not store the guest thread value");
        require(invoke_import(module, 0xf0000120, {tls_index}) == 1 &&
                    invoke_import(module, 0xf0000100, {tls_index}) == 0,
                "TlsFree did not clear and release the TLS slot");
        require(invoke_import(module, 0xf00000f0, {}) == tls_index,
                "TlsAlloc did not reuse a freed TLS index");
        constexpr uint32_t wrapper_stack = 0x00032500;
        write_guest_u32(module, "ram", wrapper_stack, 0x00401000);
        write_guest_u32(module, "ram", wrapper_stack + 4, 0x12345678);
        write_guest_u32(module, "register", 0x10, wrapper_stack);
        require(module.call(0x00401100) == 0,
                "import-backed TlsAlloc wrapper failed: " + module.last_error());
        require(read_guest_u32(module, "register", 0) == 1 &&
                    read_guest_u32(module, "register", 0x10) ==
                        wrapper_stack + 8,
                "TlsAlloc wrapper did not return its index and clean one argument");
        constexpr uint32_t critical_section_address = 0x00032400;
        require(invoke_import(module, 0xf0000130,
                              {critical_section_address, 0x400}) == 1,
                "InitializeCriticalSectionAndSpinCount did not return TRUE");
        require(read_guest_u32(module, "ram", critical_section_address) == 0 &&
                    read_guest_u32(module, "ram", critical_section_address + 4) ==
                        UINT32_MAX &&
                    read_guest_u32(module, "ram", critical_section_address + 8) == 0 &&
                    read_guest_u32(module, "ram", critical_section_address + 12) == 0 &&
                    read_guest_u32(module, "ram", critical_section_address + 16) == 0 &&
                    read_guest_u32(module, "ram", critical_section_address + 20) ==
                        0x400,
                "critical section fields or spin count are incorrect");
        (void)invoke_import(module, 0xf0000150,
                            {critical_section_address});
        require(read_guest_u32(module, "ram", critical_section_address + 4) == 0 &&
                    read_guest_u32(module, "ram", critical_section_address + 8) == 1 &&
                    read_guest_u32(module, "ram", critical_section_address + 12) != 0,
                "EnterCriticalSection did not acquire the guest lock");
        require(invoke_import(module, 0xf0000170,
                              {critical_section_address}) == 1 &&
                    read_guest_u32(module, "ram", critical_section_address + 4) == 1 &&
                    read_guest_u32(module, "ram", critical_section_address + 8) == 2,
                "TryEnterCriticalSection did not recurse for the guest thread");
        (void)invoke_import(module, 0xf0000160,
                            {critical_section_address});
        (void)invoke_import(module, 0xf0000160,
                            {critical_section_address});
        require(read_guest_u32(module, "ram", critical_section_address + 4) ==
                    UINT32_MAX &&
                    read_guest_u32(module, "ram", critical_section_address + 8) == 0,
                "LeaveCriticalSection did not release the final recursion");
        require(invoke_import(module, 0xf00001a0,
                              {critical_section_address, 0x800}) == 0x400 &&
                    read_guest_u32(module, "ram", critical_section_address + 20) ==
                        0x800,
                "SetCriticalSectionSpinCount did not return and set the spin count");
        (void)invoke_import(module, 0xf0000180,
                            {critical_section_address});
        require(read_guest_u32(module, "ram", critical_section_address) == 0 &&
                    read_guest_u32(module, "ram", critical_section_address + 4) == 0,
                "DeleteCriticalSection did not clear its guest structure");
        (void)invoke_import(module, 0xf0000190,
                            {critical_section_address});
        require(read_guest_u32(module, "ram", critical_section_address + 4) ==
                    UINT32_MAX &&
                    read_guest_u32(module, "ram", critical_section_address + 20) == 0,
                "InitializeCriticalSection did not initialize the x86 structure");
        constexpr uint32_t interlocked_value_address = 0x00032600;
        write_guest_u32(module, "ram", interlocked_value_address, 41);
        require(invoke_import(module, 0xf0000140,
                              {interlocked_value_address}) == 42 &&
                    read_guest_u32(module, "ram", interlocked_value_address) == 42,
                "InterlockedIncrement did not return and store the incremented value");
        write_guest_u32(module, "ram", interlocked_value_address, UINT32_MAX);
        require(invoke_import(module, 0xf0000140,
                              {interlocked_value_address}) == 0 &&
                    read_guest_u32(module, "ram", interlocked_value_address) == 0,
                "InterlockedIncrement did not wrap as a 32-bit x86 value");
        write_guest_u32(module, "ram", interlocked_value_address, 41);
        require(invoke_import(module, 0xf00002c0,
                              {interlocked_value_address}) == 40 &&
                    read_guest_u32(module, "ram", interlocked_value_address) == 40,
                "InterlockedDecrement did not return and store the decremented value");
        write_guest_u32(module, "ram", interlocked_value_address, 0);
        require(invoke_import(module, 0xf00002c0,
                              {interlocked_value_address}) == UINT32_MAX &&
                    read_guest_u32(module, "ram", interlocked_value_address) == UINT32_MAX,
                "InterlockedDecrement did not wrap as a 32-bit x86 value");
        require(invoke_import(module, 0xf00001b0,
                              {static_cast<uint32_t>(-10)}) == 0x00020000 &&
                    invoke_import(module, 0xf00001b0,
                                  {static_cast<uint32_t>(-11)}) == 0x00020004 &&
                    invoke_import(module, 0xf00001b0,
                                  {static_cast<uint32_t>(-12)}) == 0x00020008 &&
                    invoke_import(module, 0xf00001b0, {0}) == 0,
                "GetStdHandle did not return its guest standard-stream handles");
        require(invoke_import(module, 0xf00001c0, {0x00020000}) == 2 &&
                    invoke_import(module, 0xf00001c0, {0x00020004}) == 2 &&
                    invoke_import(module, 0xf00001c0, {0x00020008}) == 2 &&
                    invoke_import(module, 0xf00001c0, {0x12345678}) == 0,
                "GetFileType did not classify guest console handles");
        require(invoke_import(module, 0xf00001d0, {0x40}) == 0x40,
                "SetHandleCount did not return the requested compatibility value");
        constexpr char expected_command_line[] = "SHIFT.exe";
        const uint32_t command_line = invoke_import(module, 0xf00001e0, {});
        std::array<uint8_t, sizeof(expected_command_line)> command_line_bytes{};
        require(command_line == 0x00031000 &&
                    module.read_guest("ram", command_line,
                                      command_line_bytes.size(),
                                      command_line_bytes.data()) &&
                    std::equal(command_line_bytes.begin(),
                               command_line_bytes.end(),
                               expected_command_line),
                "GetCommandLineA did not return the static guest command line");
        constexpr uint32_t environment_w = 0xf00001f0;
        constexpr uint32_t free_environment_w = 0xf0000200;
        constexpr uint32_t environment_a = 0xf0000210;
        constexpr uint32_t free_environment_a = 0xf0000220;
        const uint32_t environment_w_address =
            invoke_import(module, environment_w, {});
        std::array<uint8_t, 4> environment_w_bytes{};
        require(environment_w_address == 0x00031020 &&
                    module.read_guest("ram", environment_w_address,
                                      environment_w_bytes.size(),
                                      environment_w_bytes.data()) &&
                    environment_w_bytes ==
                        std::array<uint8_t, 4>{0, 0, 0, 0} &&
                    invoke_import(module, free_environment_w,
                                  {environment_w_address}) == 1,
                "wide environment block was not empty and freeable");
        const uint32_t environment_a_address =
            invoke_import(module, environment_a, {});
        std::array<uint8_t, 2> environment_a_bytes{};
        require(environment_a_address == 0x00031010 &&
                    module.read_guest("ram", environment_a_address,
                                      environment_a_bytes.size(),
                                      environment_a_bytes.data()) &&
                    environment_a_bytes == std::array<uint8_t, 2>{0, 0} &&
                    invoke_import(module, free_environment_a,
                                  {environment_a_address}) == 1,
                "ANSI environment block was not empty and freeable");
        constexpr uint32_t wide_char_to_multi_byte = 0xf0000230;
        constexpr uint32_t converted_environment_address = 0x00032080;
        const std::vector<uint32_t> empty_environment_conversion = {
            0, 0, environment_w_address, 1, 0, 0, 0, 0};
        require(invoke_import(module, wide_char_to_multi_byte,
                              empty_environment_conversion) == 1 &&
                    invoke_import(module, wide_char_to_multi_byte,
                                  {0, 0, environment_w_address, 1,
                                   converted_environment_address, 1, 0, 0}) == 1 &&
                    read_guest_u32(module, "ram",
                                   converted_environment_address) == 0,
                "WideCharToMultiByte did not size and copy the empty CRT environment");
        constexpr uint32_t get_last_error = 0xf0000240;
        constexpr uint32_t set_last_error = 0xf0000250;
        require(invoke_import(module, get_last_error, {}) == 0,
                "GetLastError did not start at zero");
        (void)invoke_import(module, set_last_error, {0x1234});
        require(invoke_import(module, get_last_error, {}) == 0x1234,
                "SetLastError did not store the guest thread value");
        (void)invoke_import(module, set_last_error, {0});
        require(invoke_import(module, get_last_error, {}) == 0,
                "GetLastError and SetLastError did not preserve guest thread state");
        require(invoke_import(module, 0xf00002f0,
                              {0x00010000, 0, first_allocation}) == UINT32_MAX &&
                    invoke_import(module, get_last_error, {}) == 87,
                "HeapSize did not reject a freed allocation and set ERROR_INVALID_PARAMETER");
        constexpr uint32_t missing_environment_name = 0x00032d20;
        constexpr uint32_t missing_environment_output = 0x00032d40;
        constexpr char missing_environment_variable[] = "MISSING_ENV";
        require(module.write_guest(
                    "ram", missing_environment_name,
                    sizeof(missing_environment_variable),
                    reinterpret_cast<const uint8_t*>(
                        missing_environment_variable)),
                "could not write missing environment variable name");
        write_guest_u32(module, "ram", missing_environment_output,
                        0x11223344);
        require(invoke_import(module, 0xf0000330,
                              {missing_environment_name,
                               missing_environment_output, 4}) == 0 &&
                    invoke_import(module, get_last_error, {}) == 203 &&
                    read_guest_u32(module, "ram",
                                   missing_environment_output) == 0x11223344,
                "GetEnvironmentVariableA did not report an absent variable without writing the buffer");
        constexpr uint32_t environment_name_address = 0x00032d60;
        constexpr uint32_t environment_value_address = 0x00032d70;
        constexpr char environment_name[] = "X";
        constexpr char environment_value[] = "1.02";
        require(module.write_guest(
                    "ram", environment_name_address,
                    sizeof(environment_name),
                    reinterpret_cast<const uint8_t*>(environment_name)) &&
                    module.write_guest(
                        "ram", environment_value_address,
                        sizeof(environment_value),
                        reinterpret_cast<const uint8_t*>(environment_value)) &&
                    invoke_import(module, 0xf0000340,
                                  {environment_name_address,
                                   environment_value_address}) == 1,
                "SetEnvironmentVariableA did not store the guest variable");
        std::array<uint8_t, sizeof(environment_value)> environment_value_read{};
        require(invoke_import(module, 0xf0000330,
                              {environment_name_address,
                               missing_environment_output,
                               environment_value_read.size()}) ==
                        sizeof(environment_value) - 1 &&
                    module.read_guest("ram", missing_environment_output,
                                      environment_value_read.size(),
                                      environment_value_read.data()) &&
                    environment_value_read ==
                        std::array<uint8_t, sizeof(environment_value)>{
                            '1', '.', '0', '2', 0},
                "GetEnvironmentVariableA did not retrieve a stored value");
        const uint32_t environment_a_snapshot =
            invoke_import(module, environment_a, {});
        std::array<uint8_t, 8> expected_environment_a = {
            'X', '=', '1', '.', '0', '2', 0, 0};
        std::array<uint8_t, 8> environment_a_snapshot_bytes{};
        require(module.read_guest("ram", environment_a_snapshot,
                                  environment_a_snapshot_bytes.size(),
                                  environment_a_snapshot_bytes.data()) &&
                    environment_a_snapshot_bytes == expected_environment_a &&
                    invoke_import(module, free_environment_a,
                                  {environment_a_snapshot}) == 1,
                "GetEnvironmentStringsA did not snapshot the guest variable");
        const uint32_t environment_w_snapshot =
            invoke_import(module, environment_w, {});
        constexpr std::array<uint8_t, 16> expected_environment_w = {
            'X', 0, '=', 0, '1', 0, '.', 0, '0', 0, '2', 0, 0, 0, 0, 0};
        std::array<uint8_t, 16> environment_w_snapshot_bytes{};
        require(module.read_guest("ram", environment_w_snapshot,
                                  environment_w_snapshot_bytes.size(),
                                  environment_w_snapshot_bytes.data()) &&
                    environment_w_snapshot_bytes == expected_environment_w &&
                    invoke_import(module, free_environment_w,
                                  {environment_w_snapshot}) == 1,
                "GetEnvironmentStringsW did not snapshot the guest variable");
        require(invoke_import(module, 0xf0000340,
                              {environment_name_address, 0}) == 1 &&
                    invoke_import(module, 0xf0000330,
                                  {environment_name_address,
                                   missing_environment_output,
                                   environment_value_read.size()}) == 0 &&
                    invoke_import(module, get_last_error, {}) == 203,
                "SetEnvironmentVariableA did not remove the guest variable");
        constexpr uint32_t create_mutex = 0xf0000300;
        constexpr uint32_t mutex_name_address = 0x00032d00;
        constexpr char mutex_name[] = "ShiftMutex";
        require(module.write_guest(
                    "ram", mutex_name_address, sizeof(mutex_name),
                    reinterpret_cast<const uint8_t*>(mutex_name)),
                "could not write the named-mutex fixture string");
        const uint32_t named_mutex =
            invoke_import(module, create_mutex,
                          {0, 0, mutex_name_address});
        require(named_mutex == 0x00030000 &&
                    invoke_import(module, create_mutex,
                                  {0, 1, mutex_name_address}) == named_mutex &&
                    invoke_import(module, get_last_error, {}) == 183,
                "CreateMutexA did not reuse an existing named mutex");
        require(invoke_import(module, create_mutex, {0, 1, 0}) == 0x00030004,
                "CreateMutexA did not allocate an unnamed guest mutex handle");
        require(invoke_import(module, 0xf0000320, {0x00030004}) == 1 &&
                    invoke_import(module, 0xf0000310,
                                  {named_mutex, UINT32_MAX}) == 0 &&
                    invoke_import(module, 0xf0000310,
                                  {named_mutex, 0}) == 0 &&
                    invoke_import(module, 0xf0000320, {named_mutex}) == 1 &&
                    invoke_import(module, 0xf0000320, {named_mutex}) == 1,
                "single-thread WaitForSingleObject/ReleaseMutex did not track recursive ownership");
        require(invoke_import(module, 0xf0000320, {named_mutex}) == 0 &&
                    invoke_import(module, get_last_error, {}) == 288,
                "ReleaseMutex did not reject a mutex the guest thread did not own");
        require(invoke_import(module, 0xf0000310,
                              {0x12345678, UINT32_MAX}) == UINT32_MAX &&
                    invoke_import(module, get_last_error, {}) == 6,
                "WaitForSingleObject did not fail with ERROR_INVALID_HANDLE for an unknown object");
        require(invoke_import(module, 0xf0000350, {0x00030004}) == 1 &&
                    invoke_import(module, 0xf0000350, {named_mutex}) == 1 &&
                    invoke_import(module, create_mutex,
                                  {0, 0, mutex_name_address}) == 0x00030008 &&
                    invoke_import(module, 0xf0000350, {0x00030008}) == 1 &&
                    invoke_import(module, 0xf0000350, {named_mutex}) == 0 &&
                    invoke_import(module, get_last_error, {}) == 6,
                "CloseHandle did not close mutex handles and release the named entry");
        require(invoke_import(module, 0xf0000260, {}) == 1252,
                "GetACP did not match the configured Windows ANSI profile");
        constexpr uint32_t set_unhandled_exception_filter = 0xf00002e0;
        require(invoke_import(module, set_unhandled_exception_filter,
                              {0x00915741}) == 0 &&
                    invoke_import(module, set_unhandled_exception_filter,
                                  {0x0091575a}) == 0x00915741 &&
                    invoke_import(module, set_unhandled_exception_filter,
                                  {0}) == 0x0091575a,
                "SetUnhandledExceptionFilter did not retain and return the prior guest filter");
        require(invoke_import(module, 0xf0000270, {1252}) == 1 &&
                    invoke_import(module, 0xf0000270, {437}) == 0,
                "IsValidCodePage did not enforce the configured code-page profile");
        constexpr uint32_t cpinfo_address = 0x00032180;
        require(invoke_import(module, 0xf0000280,
                              {1252, cpinfo_address}) == 1 &&
                    read_guest_u32(module, "ram", cpinfo_address) == 1,
                "GetCPInfo did not describe the configured single-byte code page");
        std::array<uint8_t, 16> cpinfo_tail{};
        require(module.read_guest("ram", cpinfo_address + 4,
                                  cpinfo_tail.size(), cpinfo_tail.data()) &&
                    cpinfo_tail[0] == '?' && cpinfo_tail[1] == 0 &&
                    std::all_of(cpinfo_tail.begin() + 2, cpinfo_tail.end(),
                                [](uint8_t byte) { return byte == 0; }) &&
                    invoke_import(module, 0xf0000280,
                                  {437, cpinfo_address}) == 0,
                "GetCPInfo returned unexpected defaults or accepted another code page");
        constexpr uint32_t empty_wide_string = 0x00032700;
        constexpr uint32_t empty_string_type = 0x00032710;
        write_guest_u32(module, "ram", empty_wide_string, 0);
        require(invoke_import(module, 0xf0000290,
                              {1, empty_wide_string, 1, empty_string_type}) == 1 &&
                    read_guest_u32(module, "ram", empty_string_type) == 0x20,
                "GetStringTypeW did not classify the empty CRT probe");
        constexpr uint32_t case_source_address = 0x00032a00;
        constexpr uint32_t lower_output_address = 0x00032a10;
        constexpr uint32_t upper_output_address = 0x00032a20;
        write_guest_u32(module, "ram", case_source_address, 0x000000c9);
        require(invoke_import(module, 0xf00002b0,
                              {0, 0x100, case_source_address, 1, 0, 0}) == 1 &&
                    invoke_import(module, 0xf00002b0,
                                  {0, 0x100, case_source_address, 1,
                                   lower_output_address, 1}) == 1 &&
                    read_guest_u32(module, "ram", lower_output_address) == 0xe9 &&
                    invoke_import(module, 0xf00002b0,
                                  {0, 0x200, lower_output_address, 1,
                                   upper_output_address, 1}) == 1 &&
                    read_guest_u32(module, "ram", upper_output_address) == 0xc9,
                "LCMapStringW did not map Windows-1252 case pairs");
        constexpr uint32_t multibyte_source_address = 0x00032800;
        constexpr uint32_t wide_output_address = 0x00032900;
        constexpr std::array<uint8_t, 4> cp1252_source = {0x41, 0x80, 0xe9, 0};
        require(module.write_guest("ram", multibyte_source_address,
                                   cp1252_source.size(), cp1252_source.data()),
                "could not write CP1252 conversion fixture");
        require(invoke_import(module, 0xf00002a0,
                              {1252, 1, multibyte_source_address, 4, 0, 0}) == 4 &&
                    invoke_import(module, 0xf00002a0,
                                  {1252, 1, multibyte_source_address, 4,
                                   wide_output_address, 4}) == 4,
                "MultiByteToWideChar did not size and convert CP1252 text");
        std::array<uint8_t, 8> wide_output{};
        require(module.read_guest("ram", wide_output_address,
                                  wide_output.size(), wide_output.data()) &&
                    wide_output == std::array<uint8_t, 8>{
                        0x41, 0, 0xac, 0x20, 0xe9, 0, 0, 0},
                "MultiByteToWideChar returned incorrect CP1252 codepoints");
        constexpr uint32_t multibyte_output_address = 0x00032920;
        require(invoke_import(module, wide_char_to_multi_byte,
                              {1252, 0, wide_output_address, 4, 0, 0, 0, 0}) == 4 &&
                    invoke_import(module, wide_char_to_multi_byte,
                                  {1252, 0, wide_output_address, 4,
                                   multibyte_output_address, 4, 0, 0}) == 4,
                "WideCharToMultiByte did not size and convert CP1252 text");
        std::array<uint8_t, 4> multibyte_output{};
        require(module.read_guest("ram", multibyte_output_address,
                                  multibyte_output.size(),
                                  multibyte_output.data()) &&
                    multibyte_output == cp1252_source,
                "WideCharToMultiByte did not round-trip CP1252 text");
        const uint32_t reused_allocation = invoke_import(
            module, 0xf00000a0, {0x00010000, 0, 16});
        require((reused_allocation == first_allocation ||
                 reused_allocation == resized_allocation ||
                 reused_allocation == second_allocation) &&
                    invoke_import(module, 0xf00002f0,
                                  {0x00010000, 0, reused_allocation}) == 16,
                "HeapAlloc did not reuse a compatible freed guest range");
        constexpr uint32_t version_info_address = 0x00032200;
        write_guest_u32(module, "ram", version_info_address, 148);
        require(invoke_import(module, 0xf00000b0,
                              {version_info_address}) == 1,
                "GetVersionExA did not return TRUE for OSVERSIONINFOA");
        require(read_guest_u32(module, "ram", version_info_address) == 148 &&
                    read_guest_u32(module, "ram", version_info_address + 4) == 5 &&
                    read_guest_u32(module, "ram", version_info_address + 8) == 1 &&
                    read_guest_u32(module, "ram", version_info_address + 12) == 2600 &&
                    read_guest_u32(module, "ram", version_info_address + 16) == 2,
                "GetVersionExA returned unexpected Windows XP profile fields");
        std::array<uint8_t, 15> service_pack{};
        require(module.read_guest("ram", version_info_address + 20,
                                  service_pack.size(), service_pack.data()),
                "could not read GetVersionExA service pack string");
        constexpr char expected_service_pack[] = "Service Pack 3";
        require(std::equal(service_pack.begin(), service_pack.end(),
                           expected_service_pack),
                "GetVersionExA returned an unexpected service pack string");
        write_guest_u32(module, "ram", version_info_address, 156);
        require(invoke_import(module, 0xf00000b0,
                              {version_info_address}) == 1 &&
                    read_guest_u32(module, "ram", version_info_address + 148) == 3 &&
                    read_guest_u32(module, "ram", version_info_address + 152) ==
                        0x00010000,
                "GetVersionExA did not fill OSVERSIONINFOEXA fields");

        shift::runtime::RecompiledPcodeModule get_version_ex_w_module(argv[1]);
        const auto get_version_ex_w_image =
            get_version_ex_w_module.load_pe32_image(
                get_version_ex_w_fixture_path);
        require(get_version_ex_w_image.import_function_count == 81,
                "GetVersionExW fixture imports were not parsed");
        constexpr uint32_t version_info_w_address = 0x00032300;
        write_guest_u32(get_version_ex_w_module, "ram",
                        version_info_w_address, 276);
        require(invoke_import(get_version_ex_w_module, 0xf00000b0,
                              {version_info_w_address}) == 1 &&
                    read_guest_u32(get_version_ex_w_module, "ram",
                                   version_info_w_address + 4) == 5 &&
                    read_guest_u32(get_version_ex_w_module, "ram",
                                   version_info_w_address + 8) == 1 &&
                    read_guest_u32(get_version_ex_w_module, "ram",
                                   version_info_w_address + 12) == 2600 &&
                    read_guest_u32(get_version_ex_w_module, "ram",
                                   version_info_w_address + 16) == 2,
                "GetVersionExW returned unexpected Windows XP profile fields");
        std::array<uint8_t, 16> service_pack_w_first{};
        std::array<uint8_t, 14> service_pack_w_last{};
        require(get_version_ex_w_module.read_guest(
                    "ram", version_info_w_address + 20,
                    service_pack_w_first.size(), service_pack_w_first.data()) &&
                    get_version_ex_w_module.read_guest(
                        "ram", version_info_w_address + 20 +
                                   service_pack_w_first.size(),
                        service_pack_w_last.size(), service_pack_w_last.data()),
                "could not read GetVersionExW service pack string");
        constexpr char expected_service_pack_w[] = "Service Pack 3";
        for (size_t index = 0; index < sizeof(expected_service_pack_w); ++index) {
            const size_t offset = index * 2;
            const uint8_t low = offset < service_pack_w_first.size()
                                    ? service_pack_w_first[offset]
                                    : service_pack_w_last[
                                          offset - service_pack_w_first.size()];
            const uint8_t high = offset + 1 < service_pack_w_first.size()
                                     ? service_pack_w_first[offset + 1]
                                     : service_pack_w_last[
                                           offset + 1 -
                                           service_pack_w_first.size()];
            require(low == static_cast<uint8_t>(expected_service_pack_w[index]) &&
                        high == 0,
                    "GetVersionExW returned an unexpected service pack string");
        }
        write_guest_u32(get_version_ex_w_module, "ram",
                        version_info_w_address, 284);
        require(invoke_import(get_version_ex_w_module, 0xf00000b0,
                              {version_info_w_address}) == 1 &&
                    read_guest_u32(get_version_ex_w_module, "ram",
                                   version_info_w_address + 276) == 3 &&
                    read_guest_u32(get_version_ex_w_module, "ram",
                                   version_info_w_address + 280) ==
                        0x00010000,
                "GetVersionExW did not fill OSVERSIONINFOEXW fields");
        require(module.dispatched_function_count() == 7,
                "direct Kernel32 calls changed the P-code function count");

        require(module.call(0x00405000) == 0 && module.last_error().empty(),
                "Sleep(1) import did not complete outside the guest scheduler: " +
                    module.last_error());
        require(module.dispatched_function_count() == 8,
                "P-code import caller was not dispatched");
        require(module.call(0x00407000) != 0,
                "null FILETIME output pointer unexpectedly succeeded");
        require(module.last_error().find("invalid output pointer") !=
                    std::string::npos,
                "invalid FILETIME output pointer did not fail closed");
        std::array<uint8_t, 4> esp_after_rejection{};
        require(module.read_guest("register", 0x10,
                                  esp_after_rejection.size(),
                                  esp_after_rejection.data()),
                "could not read ESP after invalid API call");
        require(esp_after_rejection ==
                    std::array<uint8_t, 4>{0x3c, 0x00, 0x03, 0x00},
                "invalid API call changed the guest stack pointer");
        require(module.dispatched_function_count() == 9,
                "invalid FILETIME caller was not dispatched");

        require(module.call_pe32_entry_point() == 0,
                "supplemental PE32 entry point did not run with an initialized guest stack: " +
                    module.last_error());
        const auto pending_entrypoint_state =
            module.guest_scheduler_snapshot();
        const auto& main_thread_recent_functions =
            pending_entrypoint_state.main_thread_recent_functions;
        require(!module.pe32_entry_point_complete() &&
                    pending_entrypoint_state.entry_point_started &&
                    !pending_entrypoint_state.entry_point_complete &&
                    pending_entrypoint_state.main_thread_started &&
                    !pending_entrypoint_state.main_thread_completed &&
                    !pending_entrypoint_state.main_thread_call_stack.empty() &&
                    pending_entrypoint_state.main_thread_call_stack.back() ==
                        pending_entrypoint_state.main_thread_current_function &&
                    !main_thread_recent_functions.empty() &&
                    main_thread_recent_functions.size() <= 64 &&
                    main_thread_recent_functions.back() == 0x004010a0 &&
                    read_guest_u32(module, "ram", 0x00032c10) == 0x1234 &&
                    read_guest_u32(module, "ram", 0x00032c14) != 0,
                "cooperative scheduler did not yield after resuming a guest worker");
        require(module.run_guest_threads() == 0 &&
                    module.pe32_entry_point_complete(),
                "guest scheduler pump did not resume the pending PE entry point: " +
                    module.last_error());
        const auto complete_entrypoint_state =
            module.guest_scheduler_snapshot();
        require(complete_entrypoint_state.entry_point_complete &&
                    complete_entrypoint_state.main_thread_completed,
                "guest scheduler snapshot did not report PE entry-point completion");
        require(read_guest_u32(module, "register", 0x110) == 0x7ffde000 &&
                    read_guest_u32(module, "ram", 0x7ffde000) == UINT32_MAX &&
                    read_guest_u32(module, "ram", 0x7ffde004) == 0x7ffdf000 &&
                    read_guest_u32(module, "ram", 0x7ffde008) == 0x7ff00000 &&
                    read_guest_u32(module, "ram", 0x7ffde018) == 0x7ffde000,
                "PE32 entry point did not receive the initialized x86 TEB/FS base");
        require(read_guest_u16(module, "register", 0x10a0) == 0x037f &&
                    read_guest_u16(module, "register", 0x10a2) == 0 &&
                    read_guest_u16(module, "register", 0x10a4) == 0xffff,
                "PE32 entry point did not receive FINIT x87 state");
        constexpr uint32_t convert_thread_to_fiber = 0xf00004d0;
        constexpr uint32_t is_thread_a_fiber = 0xf00004e0;
        constexpr uint32_t fiber_data = 0x12345678;
        const uint32_t current_fiber =
            invoke_import(module, 78, {fiber_data});
        require(current_fiber == 0x00070000 &&
                    read_guest_u32(module, "ram", 0x7ffde010) ==
                        current_fiber &&
                    read_guest_u32(module, "ram", current_fiber) == fiber_data &&
                    invoke_import(module, is_thread_a_fiber, {}) == 1,
                "ConvertThreadToFiber did not establish the current guest fiber and data pointer");
        require(invoke_import(module, convert_thread_to_fiber, {0}) == 0 &&
                    invoke_import(module, get_last_error, {}) == 1280 &&
                    read_guest_u32(module, "ram", 0x7ffde010) == current_fiber,
                "duplicate ConvertThreadToFiber did not fail with ERROR_ALREADY_FIBER");
        constexpr uint32_t local_time_address = 0x00033000;
        (void)invoke_import(module, 80, {local_time_address});
        const uint16_t local_year =
            read_guest_u16(module, "ram", local_time_address);
        const uint16_t local_month =
            read_guest_u16(module, "ram", local_time_address + 2);
        const uint16_t local_weekday =
            read_guest_u16(module, "ram", local_time_address + 4);
        const uint16_t local_day =
            read_guest_u16(module, "ram", local_time_address + 6);
        require(local_year >= 2020 && local_year <= 2100 &&
                    local_month >= 1 && local_month <= 12 &&
                    local_weekday <= 6 && local_day >= 1 && local_day <= 31,
                "GetLocalTime did not write a valid SYSTEMTIME date");
        constexpr uint32_t memory_status_address = 0x00033020;
        (void)invoke_import(module, 81, {memory_status_address});
        const uint32_t memory_status_length =
            read_guest_u32(module, "ram", memory_status_address);
        const uint32_t memory_load =
            read_guest_u32(module, "ram", memory_status_address + 4);
        const uint32_t total_physical =
            read_guest_u32(module, "ram", memory_status_address + 8);
        const uint32_t available_physical =
            read_guest_u32(module, "ram", memory_status_address + 12);
        const uint32_t total_page_file =
            read_guest_u32(module, "ram", memory_status_address + 16);
        const uint32_t available_page_file =
            read_guest_u32(module, "ram", memory_status_address + 20);
        const uint32_t total_virtual =
            read_guest_u32(module, "ram", memory_status_address + 24);
        const uint32_t available_virtual =
            read_guest_u32(module, "ram", memory_status_address + 28);
        require(memory_status_length == 32 && memory_load <= 100 &&
                    total_physical > 0 &&
                    total_physical >= available_physical &&
                    total_page_file > 0 &&
                    total_page_file >= available_page_file &&
                    total_virtual == 0x80000000 &&
                    available_virtual < total_virtual,
                "GlobalMemoryStatus wrote an invalid guest MEMORYSTATUS");
        std::array<uint8_t, 4> entry_point_marker{};
        constexpr std::array<uint8_t, 4> expected_entry_point_marker = {
            'S', 'U', 'P', 'P'};
        require(module.read_guest("ram", 0x00032c00,
                                  entry_point_marker.size(),
                                  entry_point_marker.data()) &&
                    entry_point_marker == expected_entry_point_marker,
                "supplemental PE32 entry point did not run its fixture body");
        std::array<uint8_t, 4> event_worker_marker{};
        constexpr std::array<uint8_t, 4> expected_event_worker_marker = {
            'E', 'V', 'N', 'T'};
        require(module.read_guest("ram", 0x00032c20,
                                  event_worker_marker.size(),
                                  event_worker_marker.data()) &&
                    event_worker_marker == expected_event_worker_marker &&
                    read_guest_u32(module, "ram", 0x00032c28) != 0,
                "alertable event wait did not resume after its guest worker signaled");
        require(module.unique_dispatched_function_count() == 13,
                "supplemental entry point or scheduled worker was not dispatched");
        require(module.call_pe32_entry_point() != 0 &&
                    module.last_error().find("already been invoked") !=
                        std::string::npos,
                "PE32 entry point was allowed to run more than once");

        bool duplicate_load_rejected = false;
        try {
            (void)module.load_pe32_image(argv[4]);
        } catch (const std::runtime_error& error) {
            duplicate_load_rejected =
                std::string(error.what()).find("already been attempted") !=
                std::string::npos;
        }
        require(duplicate_load_rejected,
                "a second PE32 image load was not rejected");
        require(!module.load_supplemental_module(argv[2]) &&
                    module.last_error().find("after execution starts") !=
                        std::string::npos,
                "supplemental P-code was allowed to load after execution started");

        require(!module.load_override_module(argv[3]) &&
                    module.last_error().find("after execution starts") !=
                        std::string::npos,
                "override P-code was allowed to load after execution starts");
        require(!module.read_guest("register", 0x2000, 1, value.data()),
                "out-of-range register read unexpectedly succeeded");
        require(module.call(0x00402000) != 0,
                "missing export call unexpectedly succeeded");
        require(module.last_error().find("no exported function rvi_deadbeef") !=
                    std::string::npos &&
                    module.last_error().find(
                        "called from guest function 0x00402000") !=
                        std::string::npos,
                "missing export did not identify the unresolved address and caller");
        require(setenv("SHIFT_TRACE_GUEST_CALLER", "0x00402100", 1) == 0,
                "could not enable unresolved guest target trace fixture");
        require(setenv("SHIFT_TRACE_GUEST_CALL_LIVE_LOG", "1", 1) == 0,
                "could not enable unresolved live guest target trace fixture");
        std::string unresolved_live_trace;
        {
            StderrCapture capture;
            shift::runtime::RecompiledPcodeModule unresolved_trace_module(
                argv[1]);
            (void)unresolved_trace_module.load_pe32_image(argv[4]);
            write_guest_u32(unresolved_trace_module, "register", 0x1c,
                            0x2468ace0);
            require(unresolved_trace_module.call(0x00402100) != 0,
                    "unresolved target trace fixture unexpectedly succeeded");
            require(unresolved_trace_module.last_error().find(
                        "target=0xdeadbeef") != std::string::npos &&
                        unresolved_trace_module.last_error().find(
                            "return=0x00402105") != std::string::npos &&
                        unresolved_trace_module.last_error().find(
                            "edi=0x2468ace0") != std::string::npos &&
                        unresolved_trace_module.last_error().find(
                            "completed=0") != std::string::npos,
                    "unresolved guest call trace missed its target or call site: " +
                        unresolved_trace_module.last_error());
            const auto snapshot =
                unresolved_trace_module.guest_scheduler_snapshot();
            require(snapshot.guest_call_trace.size() == 1 &&
                        !snapshot.guest_call_trace.front().target_resolved &&
                        !snapshot.guest_call_trace.front().completed &&
                        unresolved_trace_module.last_error().find(
                            "resolved=0") != std::string::npos,
                    "unresolved guest call trace did not distinguish an absent export");
            unresolved_live_trace = capture.text();
        }
        require(unresolved_live_trace.find(
                    "shift_guest_call_trace_unresolved:") != std::string::npos,
                "live guest call trace did not mark an unresolved target: " +
                    unresolved_live_trace);
        require(unsetenv("SHIFT_TRACE_GUEST_CALL_LIVE_LOG") == 0,
                "could not disable unresolved live guest target trace fixture");
        require(unsetenv("SHIFT_TRACE_GUEST_CALLER") == 0,
                "could not disable unresolved guest target trace fixture");
        require(module.call(0x00403000) != 0,
                "unhandled P-code userop unexpectedly succeeded");
        require(module.last_error().find("unhandled P-code userop index 7") !=
                    std::string::npos,
                "unhandled P-code userop did not fail with its index");
        require(module.last_error().find("in guest function 0x00403000") !=
                    std::string::npos,
                "unhandled P-code userop did not report its guest function");
        require(module.call(0x00409000) == 0,
                "single-thread x86 LOCK/UNLOCK userops did not succeed: " +
                    module.last_error());
        require(module.call(0x0040a000) == 0,
                "x86 RDTSC userop did not return virtual monotonic ticks: " +
                    module.last_error());
        require(module.call(0x0040b000) == 0,
                "x86 FCOS userop did not compute in binary80: " +
                    module.last_error());
        std::array<uint8_t, 10> fcos_bytes{};
        require(module.read_guest("ram", 0x11010, fcos_bytes.size(),
                                  fcos_bytes.data()),
                "x86 FCOS result was not written to guest memory");
        long double fcos_result = 0.0L;
        std::memcpy(&fcos_result, fcos_bytes.data(), fcos_bytes.size());
        require(std::fabs(fcos_result - std::cos(1.0L)) < 1e-18L,
                "x86 FCOS result differed from binary80 cos(1)");
        require(module.call(0x0040b100) == 0,
                "x86 FPTAN userop did not compute in binary80: " +
                    module.last_error());
        std::array<uint8_t, 10> fptan_bytes{};
        require(module.read_guest("ram", 0x11020, fptan_bytes.size(),
                                  fptan_bytes.data()),
                "x86 FPTAN result was not written to guest memory");
        long double fptan_result = 0.0L;
        std::memcpy(&fptan_result, fptan_bytes.data(), fptan_bytes.size());
        require(std::fabs(fptan_result - std::tan(1.0L)) < 1e-18L,
                "x86 FPTAN result differed from binary80 tan(1)");
        require(module.call(0x0040b200) == 0,
                "x86 LOG2 userop did not compute in binary80: " +
                    module.last_error());
        std::array<uint8_t, 10> log2_bytes{};
        require(module.read_guest("ram", 0x11070, log2_bytes.size(),
                                  log2_bytes.data()),
                "x86 LOG2 result was not written to guest memory");
        long double log2_result = 0.0L;
        std::memcpy(&log2_result, log2_bytes.data(), log2_bytes.size());
        require(std::fabs(log2_result - 1.0L) < 1e-18L,
                "x86 LOG2 result differed from binary80 log2(2)");
        require(module.call(0x0040b300) == 0,
                "x86 F2XM1 userop did not compute in binary80: " +
                    module.last_error());
        std::array<uint8_t, 10> f2xm1_bytes{};
        require(module.read_guest("ram", 0x11080, f2xm1_bytes.size(),
                                  f2xm1_bytes.data()),
                "x86 F2XM1 result was not written to guest memory");
        long double f2xm1_result = 0.0L;
        std::memcpy(&f2xm1_result, f2xm1_bytes.data(), f2xm1_bytes.size());
        require(std::fabs(f2xm1_result - (std::sqrt(2.0L) - 1.0L)) < 1e-18L,
                "x86 F2XM1 result differed from binary80 2^0.5 - 1");
        require(module.call(0x0040b400) == 0,
                "x86 FSCALE userop did not compute in binary80: " +
                    module.last_error());
        std::array<uint8_t, 10> fscale_bytes{};
        require(module.read_guest("ram", 0x11090, fscale_bytes.size(),
                                  fscale_bytes.data()),
                "x86 FSCALE result was not written to guest memory");
        long double fscale_result = 0.0L;
        std::memcpy(&fscale_result, fscale_bytes.data(), fscale_bytes.size());
        require(std::fabs(fscale_result - 12.0L) < 1e-18L,
                "x86 FSCALE result differed from binary80 3 * 2^2");
        require(module.call(0x0040b500) == 0,
                "x86 FPATAN userop did not compute in binary80: " +
                    module.last_error());
        std::array<uint8_t, 10> fpatan_bytes{};
        require(module.read_guest("ram", 0x110a0, fpatan_bytes.size(),
                                  fpatan_bytes.data()),
                "x86 FPATAN result was not written to guest memory");
        long double fpatan_result = 0.0L;
        std::memcpy(&fpatan_result, fpatan_bytes.data(), fpatan_bytes.size());
        require(std::fabs(fpatan_result - std::atan2(2.0L, 1.0L)) < 1e-18L,
                "x86 FPATAN result differed from binary80 atan2(ST1, ST0)");
        require(module.call(0x0040b600) == 0,
                "x86 FSIN userop did not compute in binary80: " +
                    module.last_error());
        std::array<uint8_t, 10> fsin_bytes{};
        require(module.read_guest("ram", 0x110b0, fsin_bytes.size(),
                                  fsin_bytes.data()),
                "x86 FSIN result was not written to guest memory");
        long double fsin_result = 0.0L;
        std::memcpy(&fsin_result, fsin_bytes.data(), fsin_bytes.size());
        require(std::fabs(fsin_result - std::sin(1.0L)) < 1e-18L,
                "x86 FSIN result differed from binary80 sin(1)");
        require(module.call(0x0040e000) == 0,
                "x86 MINPS userop did not process four packed lanes: " +
                    module.last_error());
        require(read_guest_u32(module, "ram", 0x11030) == 0x3f800000U &&
                    read_guest_u32(module, "ram", 0x11034) == 0xc0400000U &&
                    read_guest_u32(module, "ram", 0x11038) == 0x80000000U &&
                    read_guest_u32(module, "ram", 0x1103c) == 0x40800000U,
                "MINPS result did not select lane minima, source NaN, or signed zero");
        require(read_guest_u32(module, "ram", 0x11040) == 0x40800000U &&
                    read_guest_u32(module, "ram", 0x11044) == 0x7fc54321U &&
                    read_guest_u32(module, "ram", 0x11048) == 0x00000000U &&
                    read_guest_u32(module, "ram", 0x1104c) == 0x80000000U,
                "MINPS did not forward the second NaN or signed-zero operand");
        require(module.call(0x0040e100) == 0,
                "x86 MAXPS userop did not process four packed lanes: " +
                    module.last_error());
        require(read_guest_u32(module, "ram", 0x11050) == 0x40000000U &&
                    read_guest_u32(module, "ram", 0x11054) == 0xc0000000U &&
                    read_guest_u32(module, "ram", 0x11058) == 0x80000000U &&
                    read_guest_u32(module, "ram", 0x1105c) == 0x40800000U &&
                    read_guest_u32(module, "ram", 0x11060) == 0x40800000U &&
                    read_guest_u32(module, "ram", 0x11064) == 0x7fc54321U &&
                    read_guest_u32(module, "ram", 0x11068) == 0x00000000U &&
                    read_guest_u32(module, "ram", 0x1106c) == 0x80000000U,
                "MAXPS did not select lane maxima, source NaN, or signed zero");
        require(module.call(0x0040e200) != 0 &&
                    module.last_error().find(
                        "invalid x86 MINPS P-code userop signature") !=
                        std::string::npos,
                "MINPS accepted an invalid operand signature");
        require(module.call(0x00408000) == 0,
                "x86 CPUID P-code userops did not return readable guest results: " +
                    module.last_error());
        require(module.call(0x0040d000) != 0 &&
                    module.last_error().find("at 0x00000008 size 4") !=
                        std::string::npos &&
                    module.last_error().find("guest_stack=[0x0040d000]") !=
                        std::string::npos &&
                    module.last_error().find("guest_regs={EAX=") !=
                        std::string::npos &&
                    module.last_error().find("ZF=0x") !=
                        std::string::npos,
                "low-memory write error omitted its address, stack, or registers");

        shift::runtime::RecompiledPcodeModule exception_module(argv[1]);
        (void)exception_module.load_pe32_image(argv[5]);
        const uint32_t raise_exception_stub =
            read_guest_u32(exception_module, "ram", 0x00402c00);
        constexpr uint32_t thread_info_address = 0x00035000;
        constexpr uint32_t thread_name_address = 0x00035100;
        write_guest_u32(exception_module, "ram", thread_info_address, 0x1000);
        write_guest_u32(exception_module, "ram", thread_info_address + 4,
                        thread_name_address);
        write_guest_u32(exception_module, "ram", thread_info_address + 8,
                        UINT32_MAX);
        write_guest_u32(exception_module, "ram", thread_info_address + 12, 0);
        constexpr std::array<uint8_t, 11> thread_name = {
            'M', 'a', 'i', 'n', 'T', 'h', 'r', 'e', 'a', 'd', 0};
        write_guest_bytes(exception_module, thread_name_address,
                          thread_name.data(), thread_name.size());
        require(call_import(exception_module, raise_exception_stub,
                            {0x12345678, 0, 4, thread_info_address}) != 0 &&
                    exception_module.last_error().find(
                        "only supports the MSVC thread-name exception") !=
                        std::string::npos,
                "RaiseException accepted an unsupported exception code");
        require(invoke_import(exception_module, raise_exception_stub,
                              {0x406d1388, 0, 4, thread_info_address}) == 0,
                "MSVC thread-name RaiseException pattern was not handled: " +
                    exception_module.last_error());

        write_pe32_fixture(argv[5], false, false, true);
        shift::runtime::RecompiledPcodeModule unsupported_import_module(argv[1]);
        (void)unsupported_import_module.load_pe32_image(argv[5]);
        const uint32_t unsupported_import_stub =
            read_guest_u32(unsupported_import_module, "ram", 0x00402c00);
        require(call_import(unsupported_import_module,
                            unsupported_import_stub, {}) != 0 &&
                    unsupported_import_module.last_error().find(
                        "unimplemented PE import KERNEL32.dll!UnknownApi") !=
                        std::string::npos &&
                    unsupported_import_module.last_error().find(
                        "return_address=0x00401234") != std::string::npos,
                "unsupported import error omitted its guest return address");

        const uint32_t exit_process_api = resolve_kernel32_api("ExitProcess");
        require(call_import(module, exit_process_api, {1}) != 0 &&
                    module.last_error().find(
                        "ExitProcess terminated the guest process with code 1") !=
                        std::string::npos &&
                    module.last_error().find("guest EDI=0x") !=
                        std::string::npos,
                "ExitProcess returned to guest code instead of terminating it");

        std::filesystem::remove(get_version_ex_w_fixture_path);
        std::filesystem::remove(find_window_w_fixture_path);
        std::filesystem::remove(reg_open_key_ex_w_fixture_path);
        std::filesystem::remove(wsa_startup_fixture_path);
        std::filesystem::remove(stack_walk64_fixture_path);
        std::cout << "PASS: PE32 headers, sections and imports mapped; "
                     "observed Kernel32 startup services wrote outputs and "
                     "applied stdcall cleanup; unsupported imports failed closed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "recompiled P-code module check failed: " << error.what()
                  << '\n';
        return 1;
    }
}

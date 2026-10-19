#include "shift_recompiled_pcode_module.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
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
            "Kernel32 import dispatch failed at " +
                std::to_string(address) + " returned " +
                std::to_string(result) + ": " + module.last_error());
    require(read_guest_u32(module, "register", 0x10) ==
                stack_pointer + 4 + arguments.size() * 4,
            "Kernel32 import applied incorrect stdcall cleanup");
    return read_guest_u32(module, "register", 0);
}

void write_pe32_fixture(const std::string& path,
                        bool raise_exception_import = false,
                        bool time_get_time_import = false,
                        bool unknown_first_import = false) {
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
    write_import_name(0x680, "GetCurrentThreadId");
    write_import_name(0x6a0, "GetTickCount");
    write_import_name(0x6c0, "QueryPerformanceCounter");
    write_import_name(0x6e0, "QueryPerformanceFrequency");
    write_import_name(0x700, "GetStartupInfoA");
    write_import_name(0x720, "GetProcessHeap");
    write_import_name(0x740, "HeapAlloc");
    write_import_name(0x760, "GetVersionExA");
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
    write_import_name(0xe20, "GetFileSize");
    write_import_name(0xe40, "ReadFile");
    std::copy_n("imagehlp.dll", 13, bytes.begin() + 0xe60);
    write_import_name(0xe80, "SymSetOptions");
    write_import_name(0xea0, "SymInitialize");
    write_import_name(0xec0, "SymCleanup");
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

void write_system_parameters_info_pe32_fixture(const std::string& path) {
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
    std::copy_n("USER32.dll", 11, bytes.begin() + 0x480);
    std::copy_n("SystemParametersInfoA", 22, bytes.begin() + 0x492);
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

    write_u32(bytes, 0x400, 0x2040);
    write_u32(bytes, 0x40c, 0x2080);
    write_u32(bytes, 0x410, 0x2060);
    write_u32(bytes, 0x414, 0x2100);
    write_u32(bytes, 0x420, 0x2120);
    write_u32(bytes, 0x424, 0x2180);
    for (size_t index = 0; index < 3; ++index) {
        const uint32_t name_rva =
            static_cast<uint32_t>(0x2090 + index * 0x20);
        write_u32(bytes, 0x440 + index * 4, name_rva);
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

    std::ofstream file(path, std::ios::binary | std::ios::trunc);
    require(static_cast<bool>(file), "could not create D3D9 PE32 fixture");
    file.write(reinterpret_cast<const char*>(bytes.data()),
               static_cast<std::streamsize>(bytes.size()));
    require(static_cast<bool>(file), "could not write D3D9 PE32 fixture");
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 9) {
        std::cerr << "usage: shift_runtime_recompiled_pcode_module_check "
                     "MODULE SUPPLEMENT OVERRIDE PE32_FIXTURE_OUT "
                     "RAISE_EXCEPTION_PE32_OUT TIME_GET_TIME_PE32_OUT "
                     "SYSTEM_PARAMETERS_INFO_PE32_OUT D3D9_PE32_OUT\n";
        return 2;
    }
    try {
        write_pe32_fixture(argv[4]);
        write_pe32_fixture(argv[5], true);
        write_pe32_fixture(argv[6], false, true);
        write_system_parameters_info_pe32_fixture(argv[7]);
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

        require(setenv("SHIFT_TRACE_GUEST_CALLER", "0x00401000", 1) == 0,
                "could not enable guest caller trace fixture");
        {
            shift::runtime::RecompiledPcodeModule call_trace_module(argv[1]);
            require(call_trace_module.call(0x00401000) == 0,
                    "guest caller trace fixture call failed: " +
                        call_trace_module.last_error());
            const auto snapshot = call_trace_module.guest_scheduler_snapshot();
            require(snapshot.guest_call_trace_enabled &&
                        !snapshot.guest_call_trace_truncated &&
                        snapshot.guest_call_trace_caller == 0x00401000 &&
                        snapshot.guest_call_trace.size() == 1 &&
                        snapshot.guest_call_trace.front().caller == 0x00401000 &&
                        snapshot.guest_call_trace.front().function == 0x00685700,
                    "guest caller trace did not capture its nested P-code call");
        }
        require(unsetenv("SHIFT_TRACE_GUEST_CALLER") == 0,
                "could not disable guest caller trace fixture");

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
        require(d3d9_image.import_module_count == 2 &&
                    d3d9_image.import_function_count == 5,
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
        constexpr uint32_t create_directory_path_address = 0x00035000;
        constexpr char create_directory_path[] =
            "C:\\Documents and Settings\\SHIFT\\My Documents\\SHCreateDirectoryExFixture";
        write_guest_bytes(
            d3d9_module, create_directory_path_address,
            reinterpret_cast<const uint8_t*>(create_directory_path),
            sizeof(create_directory_path));
        const std::filesystem::path expected_created_directory =
            std::filesystem::current_path() /
            "Documents and Settings/SHIFT/My Documents/SHCreateDirectoryExFixture";
        require(invoke_import(d3d9_module, sh_create_directory,
                              {0, create_directory_path_address, 0}) == 0 &&
                    std::filesystem::is_directory(expected_created_directory) &&
                    invoke_import(d3d9_module, sh_create_directory,
                                  {0, create_directory_path_address, 0}) == 183,
                "SHCreateDirectoryExA did not create directories or report existing paths");
        constexpr char relative_create_directory_path[] = "relative-path";
        write_guest_bytes(
            d3d9_module, create_directory_path_address,
            reinterpret_cast<const uint8_t*>(relative_create_directory_path),
            sizeof(relative_create_directory_path));
        require(invoke_import(d3d9_module, sh_create_directory,
                              {0, create_directory_path_address, 0}) == 161,
                "SHCreateDirectoryExA accepted a relative path");
        constexpr char escaped_create_directory_path[] =
            "C:\\..\\outside-guest-root";
        write_guest_bytes(
            d3d9_module, create_directory_path_address,
            reinterpret_cast<const uint8_t*>(escaped_create_directory_path),
            sizeof(escaped_create_directory_path));
        require(invoke_import(d3d9_module, sh_create_directory,
                              {0, create_directory_path_address, 0}) == 5,
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
        require(invoke_import(module, 0xf0000350, {guest_file_handle}) == 1,
                "CloseHandle did not close the guest file");
        std::filesystem::remove(guest_file_path);
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
                    main_thread_recent_functions.back() ==
                        pending_entrypoint_state.main_thread_current_function &&
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
        require(module.dispatched_function_count() == 13,
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
        require(module.call(0x00408000) == 0,
                "x86 CPUID P-code userops did not return readable guest results: " +
                    module.last_error());
        require(module.call(0x0040d000) != 0 &&
                    module.last_error().find("at 0x00000008 size 4") !=
                        std::string::npos &&
                    module.last_error().find("guest_stack=[0x0040d000]") !=
                        std::string::npos &&
                    module.last_error().find("guest_regs={EAX=") !=
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

#include "shift_recompiled_pcode_module.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
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

uint32_t invoke_import(shift::runtime::RecompiledPcodeModule& module,
                       uint32_t address,
                       const std::vector<uint32_t>& arguments) {
    constexpr uint32_t stack_pointer = 0x00032000;
    write_guest_u32(module, "ram", stack_pointer, 0x00401234);
    for (size_t index = 0; index < arguments.size(); ++index)
        write_guest_u32(module, "ram", stack_pointer + 4 + index * 4,
                        arguments[index]);
    write_guest_u32(module, "register", 0x10, stack_pointer);
    const int result = module.call(address);
    require(result == 0,
            "Kernel32 import dispatch failed at " +
                std::to_string(address) + " returned " +
                std::to_string(result) + ": " + module.last_error());
    require(read_guest_u32(module, "register", 0x10) ==
                stack_pointer + 4 + arguments.size() * 4,
            "Kernel32 import applied incorrect stdcall cleanup");
    return read_guest_u32(module, "register", 0);
}

void write_pe32_fixture(const std::string& path) {
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
    const std::array<uint32_t, 71> import_thunks = {
        0x2200, 0x8000007b, 0x2240, 0x2260, 0x2280, 0x22a0, 0x22c0,
        0x22e0, 0x2300, 0x2320, 0x2340, 0x2360, 0x2380, 0x23a0,
        0x23c0, 0x23e0, 0x2400, 0x2420, 0x2440, 0x2460, 0x24a0,
        0x24c0, 0x24e0, 0x2500, 0x2520, 0x2540, 0x2560, 0x2580,
        0x25a0, 0x25c0, 0x25e0, 0x2600, 0x2640, 0x2680, 0x26a0,
        0x26c0, 0x2700, 0x2720, 0x2740, 0x2760, 0x2780, 0x27a0,
        0x27c0, 0x27e0, 0x2800, 0x2820, 0x2840, 0x2860, 0x2880,
        0x28a0, 0x28c0, 0x28e0, 0x2900, 0x2920, 0x2940, 0x2960, 0x2980,
        0x29a0, 0x29c0, 0x29e0, 0x2a00, 0x2a20, 0x2a40, 0x2ad0,
        0x2af0, 0x2b10, 0x2b30, 0x2b50, 0x2b70, 0x2b90, 0x2bb0};
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
    write_import_name(0x600, "Sleep");
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
    write_import_name(0x11c0, "timeEndPeriod");
    write_import_name(0x1188, "ConvertThreadToFiber");
    write_import_name(0x11ed, "IsThreadAFiber");
    write_import_name(0x1200, "GlobalMemoryStatus");
    write_import_name(0x1218, "GetLocalTime");

    std::ofstream file(path, std::ios::binary | std::ios::trunc);
    require(static_cast<bool>(file), "could not create PE32 fixture");
    file.write(reinterpret_cast<const char*>(bytes.data()),
               static_cast<std::streamsize>(bytes.size()));
    require(static_cast<bool>(file), "could not write PE32 fixture");
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "usage: shift_runtime_recompiled_pcode_module_check "
                     "MODULE SUPPLEMENT PE32_FIXTURE_OUT\n";
        return 2;
    }
    try {
        write_pe32_fixture(argv[3]);
        shift::runtime::RecompiledPcodeModule module(argv[1]);
        require(module.load_supplemental_module(argv[2]),
                "P-code supplement could not be loaded: " + module.last_error());
        const auto image = module.load_pe32_image(argv[3]);
        require(image.image_base == 0x00400000 &&
                    image.image_size == 0x3000 &&
                    image.entry_point == 0x00401020 &&
                    image.section_count == 2 &&
                    image.import_module_count == 3 &&
                    image.import_function_count == 80 &&
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
        for (uint32_t index = 0; index < 71; ++index) {
            const uint32_t iat_entry = read_guest_u32(
                module, "ram", 0x00402c00 + index * sizeof(uint32_t));
            require(iat_entry == 0xf0000000 + index * 0x10,
                    "Kernel32 IAT slot was not mapped to its guest trap");
        }
        require(read_guest_u32(module, "ram", 0x00402d20) == 0xf0000470 &&
                    read_guest_u32(module, "ram", 0x00402d24) == 0xf0000480 &&
                    read_guest_u32(module, "ram", 0x00402d28) == 0xf0000490,
                "ImageHlp IAT slots were not mapped to their guest traps");
        require(read_guest_u32(module, "ram", 0x00402d40) == 0xf00004a0 &&
                    read_guest_u32(module, "ram", 0x00402d44) == 0xf00004b0,
                "WinMM timer IAT slots were not mapped to their guest traps");
        require(read_guest_u32(module, "ram", 0x00402d30) == 0xf00004c0 &&
                    read_guest_u32(module, "ram", 0x00402d34) == 0xf00004d0 &&
                    read_guest_u32(module, "ram", 0x00402d38) == 0xf00004e0,
                "Kernel32 fiber IAT slots were not mapped to their guest traps");
        require(read_guest_u32(module, "ram", 0x00402d3c) == 0xf00004f0,
                "Kernel32 memory-status IAT slot was not mapped to its guest trap");
        require(invoke_import(module, 5, {}) ==
                    static_cast<uint32_t>(syscall(SYS_gettid)),
                "one-based P-code import ID did not route to its Kernel32 trap");
        constexpr uint32_t time_begin_period = 0xf00004a0;
        constexpr uint32_t time_end_period = 0xf00004b0;
        require(invoke_import(module, 75, {1}) == 0 &&
                    invoke_import(module, time_begin_period, {1}) == 0 &&
                    invoke_import(module, time_end_period, {2}) == 97 &&
                    invoke_import(module, 76, {1}) == 0 &&
                    invoke_import(module, time_end_period, {1}) == 0 &&
                    invoke_import(module, time_end_period, {1}) == 97 &&
                    invoke_import(module, time_begin_period, {0}) == 97,
                "WinMM timer requests did not enforce supported resolution and matching lifetimes");
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
        const std::string expected_module_path = argv[3];
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
        require(module.read_guest("register", 0, value.size(), value.data()),
                "could not read fixture EAX value");
        require(value == std::array<uint8_t, 4>{0x34, 0x12, 0, 0},
                "fixture did not preserve little-endian EAX bytes");
        require(module.read_guest("ram", 0x20000, value.size(), value.data()),
                "could not read fixture RAM write");
        require(value == std::array<uint8_t, 4>{0xd0, 0x99, 0xaa, 0},
                "nested P-code call wrote unexpected RAM bytes");

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
        require(invoke_import(module, 0xf0000470, {0x16}) == 0x16 &&
                    invoke_import(module, 0xf0000480,
                                  {UINT32_MAX, 0, 1}) == 1 &&
                    invoke_import(module, 0xf0000490, {UINT32_MAX}) == 1,
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
        const uint32_t second_allocation = invoke_import(
            module, 0xf00000a0, {0x00010000, 0, 32});
        require(second_allocation > first_allocation &&
                    (second_allocation & 0xf) == 0,
                "HeapAlloc did not advance its aligned guest range");
        require(invoke_import(module, 0xf00002f0,
                              {0x00010000, 0, second_allocation}) == 32,
                "HeapSize did not report the second live allocation size");
        require(invoke_import(module, 0xf00000c0,
                              {0x00010000, 0, first_allocation}) == 1 &&
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
        require(invoke_import(module, 0xf00000a0,
                              {0x00010000, 0, 16}) == first_allocation,
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
        require(module.dispatched_function_count() == 5,
                "direct Kernel32 calls changed the P-code function count");

        require(module.call(0x00405000) != 0,
                "unimplemented import trap unexpectedly succeeded");
        require(module.last_error().find(
                    "unimplemented PE import KERNEL32.dll!Sleep") !=
                    std::string::npos,
                "import trap did not report its DLL and function name");
        require(module.dispatched_function_count() == 6,
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
        require(module.dispatched_function_count() == 7,
                "invalid FILETIME caller was not dispatched");

        require(module.call_pe32_entry_point() == 0,
                "supplemental PE32 entry point did not run with an initialized guest stack: " +
                    module.last_error());
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
        constexpr uint32_t convert_thread_to_fiber = 0xf00004c0;
        constexpr uint32_t is_thread_a_fiber = 0xf00004d0;
        constexpr uint32_t fiber_data = 0x12345678;
        const uint32_t current_fiber =
            invoke_import(module, 77, {fiber_data});
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
        (void)invoke_import(module, 79, {local_time_address});
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
        (void)invoke_import(module, 80, {memory_status_address});
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
        require(module.dispatched_function_count() == 8,
                "supplemental P-code function was not dispatched exactly once");
        require(module.call_pe32_entry_point() != 0 &&
                    module.last_error().find("already been invoked") !=
                        std::string::npos,
                "PE32 entry point was allowed to run more than once");

        bool duplicate_load_rejected = false;
        try {
            (void)module.load_pe32_image(argv[3]);
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

        require(!module.read_guest("register", 0x2000, 1, value.data()),
                "out-of-range register read unexpectedly succeeded");
        require(module.call(0x00402000) != 0,
                "missing export call unexpectedly succeeded");
        require(module.last_error().find("no exported function rvi_deadbeef") !=
                    std::string::npos,
                "missing export did not fail with the unresolved guest address");
        require(module.call(0x00403000) != 0,
                "unhandled P-code userop unexpectedly succeeded");
        require(module.last_error().find("unhandled P-code userop index 7") !=
                    std::string::npos,
                "unhandled P-code userop did not fail with its index");
        require(module.call(0x00409000) == 0,
                "single-thread x86 LOCK/UNLOCK userops did not succeed: " +
                    module.last_error());
        require(module.call(0x0040a000) == 0,
                "x86 RDTSC userop did not return virtual monotonic ticks: " +
                    module.last_error());
        require(module.call(0x00408000) == 0,
                "x86 CPUID P-code userops did not return readable guest results: " +
                    module.last_error());

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

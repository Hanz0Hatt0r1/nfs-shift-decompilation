#include "shift_recompiled_pcode_module.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
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

void write_pe32_fixture(const std::string& path) {
    constexpr size_t file_size = 0x600;
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
    write_u32(bytes, optional_offset + 16, 0x1010);
    write_u32(bytes, optional_offset + 28, 0x00400000);
    write_u32(bytes, optional_offset + 32, 0x1000);
    write_u32(bytes, optional_offset + 36, 0x200);
    write_u32(bytes, optional_offset + 56, 0x3000);
    write_u32(bytes, optional_offset + 60, 0x200);
    write_u32(bytes, optional_offset + 92, 16);
    write_u32(bytes, optional_offset + 104, 0x2000);
    write_u32(bytes, optional_offset + 108, 40);

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
    write_u32(bytes, import_section_offset + 8, 0x200);
    write_u32(bytes, import_section_offset + 12, 0x2000);
    write_u32(bytes, import_section_offset + 16, 0x200);
    write_u32(bytes, import_section_offset + 20, 0x400);
    std::fill(bytes.begin() + 0x200, bytes.begin() + 0x400, 0x90);
    bytes[0x200] = 'P';
    bytes[0x201] = '3';
    bytes[0x202] = '2';
    bytes[0x203] = '!';

    write_u32(bytes, 0x400, 0x2060);
    write_u32(bytes, 0x40c, 0x2040);
    write_u32(bytes, 0x410, 0x2080);
    std::copy_n("KERNEL32.dll", 12, bytes.begin() + 0x440);
    write_u32(bytes, 0x460, 0x20a0);
    write_u32(bytes, 0x464, 0x8000007b);
    write_u32(bytes, 0x468, 0x20b0);
    write_u32(bytes, 0x480, 0x20a0);
    write_u32(bytes, 0x484, 0x8000007b);
    write_u32(bytes, 0x488, 0x20b0);
    write_u16(bytes, 0x4a0, 0);
    std::copy_n("Sleep", 6, bytes.begin() + 0x4a2);
    write_u16(bytes, 0x4b0, 0);
    constexpr char time_api_name[] = "GetSystemTimeAsFileTime";
    std::copy_n(time_api_name, sizeof(time_api_name), bytes.begin() + 0x4b2);

    std::ofstream file(path, std::ios::binary | std::ios::trunc);
    require(static_cast<bool>(file), "could not create PE32 fixture");
    file.write(reinterpret_cast<const char*>(bytes.data()),
               static_cast<std::streamsize>(bytes.size()));
    require(static_cast<bool>(file), "could not write PE32 fixture");
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: shift_runtime_recompiled_pcode_module_check "
                     "MODULE PE32_FIXTURE_OUT\n";
        return 2;
    }
    try {
        write_pe32_fixture(argv[2]);
        shift::runtime::RecompiledPcodeModule module(argv[1]);
        const auto image = module.load_pe32_image(argv[2]);
        require(image.image_base == 0x00400000 &&
                    image.image_size == 0x3000 &&
                    image.entry_point == 0x00401010 &&
                    image.section_count == 2 &&
                    image.import_module_count == 1 &&
                    image.import_function_count == 3 &&
                    image.import_stub_base == 0xf0000000,
                "PE32 loader returned unexpected image metadata");

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
        require(module.read_guest("ram", 0x00402080, value.size(), value.data()),
                "could not read imported function IAT entry");
        require(value == std::array<uint8_t, 4>{0, 0, 0, 0xf0},
                "named import IAT entry was not mapped to its guest trap");
        require(module.read_guest("ram", 0x00402084, value.size(), value.data()),
                "could not read ordinal IAT entry");
        require(value == std::array<uint8_t, 4>{0x10, 0, 0, 0xf0},
                "ordinal import IAT entry was not mapped to its guest trap");
        require(module.read_guest("ram", 0x00402088, value.size(),
                                  value.data()),
                "could not read GetSystemTimeAsFileTime IAT entry");
        require(value == std::array<uint8_t, 4>{0x20, 0, 0, 0xf0},
                "GetSystemTimeAsFileTime IAT entry was not mapped to its guest trap");

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

        require(module.read_guest("register", 0, value.size(), value.data()),
                "could not read fixture EAX value");
        require(value == std::array<uint8_t, 4>{0x34, 0x12, 0, 0},
                "fixture did not preserve little-endian EAX bytes");
        require(module.read_guest("ram", 0x20000, value.size(), value.data()),
                "could not read fixture RAM write");
        require(value == std::array<uint8_t, 4>{0xd0, 0x99, 0xaa, 0},
                "nested P-code call wrote unexpected RAM bytes");

        bool duplicate_load_rejected = false;
        try {
            (void)module.load_pe32_image(argv[2]);
        } catch (const std::runtime_error& error) {
            duplicate_load_rejected =
                std::string(error.what()).find("already been attempted") !=
                std::string::npos;
        }
        require(duplicate_load_rejected,
                "a second PE32 image load was not rejected");

        require(!module.read_guest("register", 0x1000, 1, value.data()),
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

        std::cout << "PASS: PE32 headers, sections and imports mapped; "
                     "GetSystemTimeAsFileTime wrote FILETIME and applied "
                     "stdcall cleanup; unsupported imports failed closed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "recompiled P-code module check failed: " << error.what()
                  << '\n';
        return 1;
    }
}

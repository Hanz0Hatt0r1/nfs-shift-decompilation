#include "shift_recompiled_pcode_module.hpp"

#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: shift_runtime_recompiled_pcode_module_check MODULE\n";
        return 2;
    }
    try {
        shift::runtime::RecompiledPcodeModule module(argv[1]);
        require(module.call(0x00401000) == 0,
                "fixture P-code entry call failed: " + module.last_error());
        require(module.dispatched_function_count() == 2,
                "nested P-code function was not dispatched");

        std::array<uint8_t, 4> value{};
        require(module.read_guest("register", 0, value.size(), value.data()),
                "could not read fixture EAX value");
        require(value == std::array<uint8_t, 4>{0x34, 0x12, 0, 0},
                "fixture did not preserve little-endian EAX bytes");
        require(module.read_guest("ram", 0x20000, value.size(), value.data()),
                "could not read fixture RAM write");
        require(value == std::array<uint8_t, 4>{0xd0, 0x99, 0xaa, 0},
                "nested P-code call wrote unexpected RAM bytes");

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

        std::cout << "PASS: P-code module loaded; 2 functions dispatched; "
                     "register/RAM callbacks and fail-closed lookup verified\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "recompiled P-code module check failed: " << error.what()
                  << '\n';
        return 1;
    }
}

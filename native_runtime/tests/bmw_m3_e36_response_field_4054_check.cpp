#include "shift_bmw_m3_e36_response_field_4054.hpp"

#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>

namespace {

using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

std::uint32_t f32_bits(float value) {
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

}  // namespace

int main() {
    try {
        const auto setup = derive_bmw_m3_e36_response_field_4054();
        require(f32_bits(setup.wheel_fl_z) == 0xbfaccccdu,
                "BMW VDF Wheel FL Offset Z f32 bits mismatch");
        require(f32_bits(setup.wheel_rl_z) == 0x3faccccdu,
                "BMW VDF Wheel RL Offset Z f32 bits mismatch");
        require(f32_bits(setup.value) == 0x402ccccdu,
                "PC FUN_0076b280 HDVehicle+0x4054 f32 bits mismatch");

        std::cout
            << "{\"format\":\"" << kBmwM3E36ResponseField4054Format << "\","
            << "\"ready\":true,"
            << "\"vdf_fl_z_bits\":\"0xbfaccccd\","
            << "\"vdf_rl_z_bits\":\"0x3faccccd\","
            << "\"response_4054_bits\":\"0x402ccccd\","
            << "\"retail_x87_fabs_store\":true,"
            << "\"setup_fixed\":true}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

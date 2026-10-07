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
        const float response = selected_bmw_m3_e36_response_field_4054();
        require(f32_bits(response) == kBmwM3E36ResponseField4054Bits,
                "selected BMW M3 E36 +0x4054 f32 bits mismatch");
        require(kBmwM3E36WheelFlZBits == 0xbfaccccdu &&
                    kBmwM3E36WheelRlZBits == 0x3faccccdu,
                "selected BMW M3 E36 wheel Z source bits drifted");

        std::cout
            << "{\"format\":\"" << kBmwM3E36ResponseField4054Format << "\","
            << "\"ready\":true,"
            << "\"wheel_fl_z_bits\":\"0xbfaccccd\","
            << "\"wheel_rl_z_bits\":\"0x3faccccd\","
            << "\"response_field_4054_bits\":\"0x402ccccd\","
            << "\"setup_fixed\":true,"
            << "\"external_provider_override_allowed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

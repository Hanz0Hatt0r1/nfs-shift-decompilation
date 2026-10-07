#include "shift_bmw_m3_e36_response_field_4054.hpp"

#include <cmath>
#include <cstring>
#include <stdexcept>

namespace shift::runtime::physics {
namespace {

float f32_from_bits(std::uint32_t bits) {
    float value = 0.0f;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

}  // namespace

float selected_bmw_m3_e36_response_field_4054() {
    const float fl_z = f32_from_bits(kBmwM3E36WheelFlZBits);
    const float rl_z = f32_from_bits(kBmwM3E36WheelRlZBits);

    // Retail loads the two f32 resource values into x87, so perform the
    // subtraction after widening and narrow only at the visible f32 store.
    const double difference =
        static_cast<double>(fl_z) - static_cast<double>(rl_z);
    const float result = static_cast<float>(std::fabs(difference));
    std::uint32_t result_bits = 0u;
    std::memcpy(&result_bits, &result, sizeof(result_bits));
    if (result_bits != kBmwM3E36ResponseField4054Bits) {
        throw std::runtime_error(
            "selected BMW M3 E36 +0x4054 resource derivation drifted");
    }
    return result;
}

}  // namespace shift::runtime::physics

#include "shift_bmw_m3_e36_response_field_4054.hpp"

#include <cmath>
#include <cstdint>
#include <cstring>
#include <stdexcept>

namespace shift::runtime::physics {
namespace {

float f32_from_bits(std::uint32_t bits) {
    float value = 0.0f;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

float retail_abs_difference_to_f32(float lhs, float rhs) {
#if defined(__i386__) || defined(__x86_64__)
    unsigned short old_control = 0u;
    const unsigned short retail_control = 0x027fu;
    float output = 0.0f;
    asm volatile("fnstcw %0" : "=m"(old_control));
    asm volatile("fldcw %0" : : "m"(retail_control));
    // FUN_0076b280 promotes the selected VDF f32 components to x87, subtracts
    // them, applies FABS, then stores HDVehicle+0x4054 as f32.
    asm volatile(
        "flds %[lhs]; fsubs %[rhs]; fabs; fstps %[out]"
        : [out] "=m"(output)
        : [lhs] "m"(lhs), [rhs] "m"(rhs));
    asm volatile("fldcw %0" : : "m"(old_control));
    return output;
#else
    throw std::runtime_error(
        "BMW M3 E36 HDVehicle+0x4054 retail producer requires x87-capable x86 host");
#endif
}

}  // namespace

BmwM3E36ResponseField4054 derive_bmw_m3_e36_response_field_4054() {
    // vehicles/physics/vehicles/bmw_m3_e36.vdf, decoded SHA-256
    // f4c925bc6799439a12906d0aed9b73e22052cb46f7fbd4ea6f48409b9776a082.
    // Use exact parsed f32 bits instead of host decimal parsing.
    const float wheel_fl_z = f32_from_bits(0xbfaccccdu); // -1.35f
    const float wheel_rl_z = f32_from_bits(0x3faccccdu); // +1.35f
    const float value = retail_abs_difference_to_f32(wheel_fl_z, wheel_rl_z);
    if (!std::isfinite(value)) {
        throw std::runtime_error(
            "BMW M3 E36 HDVehicle+0x4054 setup derivation produced non-finite value");
    }
    return BmwM3E36ResponseField4054{wheel_fl_z, wheel_rl_z, value};
}

}  // namespace shift::runtime::physics

#include "shift_fun_007682c0_machine_magnitude.hpp"

#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

using namespace shift::runtime::physics;

std::uint32_t bits(float value) {
    std::uint32_t out = 0u;
    std::memcpy(&out, &value, sizeof(out));
    return out;
}

}  // namespace

int main() {
    try {
#if !defined(__i386__) && !defined(__x86_64__)
        std::cout
            << "{\"format\":\"" << kFun007682c0MachineMagnitudeFormat << "\","
            << "\"ready\":false,\"unsupported_host\":true}\n";
        return 0;
#else
        if (fun_007682c0_pc_x87_speed3d_f32(3.0, 4.0, 12.0) != 13.0f) {
            throw std::runtime_error("PC x87 3D magnitude regression");
        }
        if (fun_0075ada0_pc_x87_planar_speed_f32(3.0, 4.0) != 5.0f) {
            throw std::runtime_error("PC x87 planar magnitude regression");
        }

        // This pair distinguishes the actual FUN_0075ada0 f64->f32 input
        // narrowing and f32 squared-radicand checkpoint from a host-double
        // sqrt shortcut. The expected PC-machine result is one f32 ULP lower.
        constexpr double kRoundingX = 9665.11344839468;
        constexpr double kRoundingZ = 20054.686391437765;
        const float planar =
            fun_0075ada0_pc_x87_planar_speed_f32(kRoundingX, kRoundingZ);
        if (bits(planar) != 1185803358u) {
            throw std::runtime_error(
                "FUN_0075ada0 f32 checkpoint semantics were not preserved");
        }
        const float host_double_shortcut = static_cast<float>(
            std::sqrt(kRoundingX * kRoundingX + kRoundingZ * kRoundingZ));
        if (bits(host_double_shortcut) != 1185803359u ||
            bits(host_double_shortcut) == bits(planar)) {
            throw std::runtime_error(
                "rounding witness no longer distinguishes host-double shortcut");
        }

        const auto below = fun_007682c0_pc_machine_magnitude(3.0, 0.0, 0.0);
        if (below.speed_3d != 3.0f || below.speed_gate_open ||
            below.speed_factor != 0.0f) {
            throw std::runtime_error("FUN_007682c0 speed gate failed closed-path parity");
        }

        const auto middle = fun_007682c0_pc_machine_magnitude(12.5, 0.0, 0.0);
        if (!middle.speed_gate_open || middle.speed_3d != 12.5f ||
            middle.speed_factor != 0.5f) {
            throw std::runtime_error("FUN_007682c0 speed-factor midpoint mismatch");
        }

        const auto high = fun_007682c0_pc_machine_magnitude(30.0, 0.0, 0.0);
        if (!high.speed_gate_open || high.speed_factor != 1.0f) {
            throw std::runtime_error("FUN_007682c0 speed-factor clamp mismatch");
        }

        bool nonfinite_rejected = false;
        try {
            (void)fun_007682c0_pc_x87_speed3d_f32(
                std::numeric_limits<double>::quiet_NaN(), 0.0, 0.0);
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        if (!nonfinite_rejected) {
            throw std::runtime_error("FUN_007682c0 non-finite input failed open");
        }

        std::cout
            << "{\"format\":\"" << kFun007682c0MachineMagnitudeFormat << "\","
            << "\"ready\":true,"
            << "\"retail_x87_control_word\":639,"
            << "\"pc_cisqrt_resolved_to_fsqrt\":true,"
            << "\"speed3d_f64_inputs\":true,"
            << "\"speed3d_f32_store_checkpoint\":true,"
            << "\"planar_f64_to_f32_input_narrowing\":true,"
            << "\"planar_squared_f32_checkpoint\":true,"
            << "\"planar_sqrt_f32_checkpoint\":true,"
            << "\"speed_factor_f32_checkpoint\":true,"
            << "\"host_std_sqrt_used_for_retail_path\":false,"
            << "\"fun_007595d0_response_complete\":false}\n";
        return 0;
#endif
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

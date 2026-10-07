#include "shift_fun_007682c0_machine_effect.hpp"
#include "shift_fun_00770e80_motion_read_machine_input_provider_chain.hpp"
#include "shift_body_record_adapter.hpp"

#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using namespace shift::runtime::physics;

void write_f64(std::vector<std::uint8_t>& bytes, std::size_t offset, double value) {
    std::uint64_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    if (offset + sizeof(bits) > bytes.size()) {
        throw std::runtime_error("test BODY write out of range");
    }
    for (std::size_t byte = 0u; byte < sizeof(bits); ++byte) {
        bytes[offset + byte] = static_cast<std::uint8_t>(
            (bits >> (byte * 8u)) & 0xffu);
    }
}

double read_f64(const std::vector<std::uint8_t>& bytes, std::size_t offset) {
    std::uint64_t bits = 0u;
    for (std::size_t byte = 0u; byte < sizeof(bits); ++byte) {
        bits |= static_cast<std::uint64_t>(bytes[offset + byte]) << (byte * 8u);
    }
    double value = 0.0;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

float f32_from_bits(std::uint32_t bits) {
    float value = 0.0f;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

std::uint32_t f32_bits(float value) {
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

std::vector<std::uint8_t> make_body(double vx, double vy, double vz) {
    std::vector<std::uint8_t> bytes(kBodyRecordSize, 0u);
    write_f64(bytes, 0x20u, 0.1);
    write_f64(bytes, 0x50u, 7.0);
    write_f64(bytes, 0x78u, vx);
    write_f64(bytes, 0x80u, vy);
    write_f64(bytes, 0x88u, vz);
    write_f64(bytes, 0x120u, 1000.0);
    return bytes;
}

Fun007682c0MachineInput make_input() {
    Fun007682c0MachineInput input{};
    input.caller_gate_open = true;
    input.steering = 1.2f;
    input.load_terms = {3000.0, 3000.0, 3000.0, 3000.0};
    input.projection_field_x = 2.0f;
    input.projection_field_z = 1.0f;
    input.response_field_4054 = 2.0f;
    input.angle_mode = 2;
    return input;
}

ContactOuterKernelInput make_contact_outer_input() {
    ContactOuterKernelInput input{};
    input.planar_delta = {10.0, 0.0, 0.0};
    input.previous_distance_state = 8.0;
    input.distance_filter_cap = 1.0;
    input.speed_x = 20.0;
    input.speed_z = 0.0;
    input.surface_scalar = 10.0;
    input.base_scalar = 4.0;
    input.projected_scalar = 1.0;
    input.alignment_scalar = 0.5;
    input.param_3 = 2.0;
    return input;
}

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main() {
    try {
        auto body = make_body(6.0, 0.0, 8.0);
        const auto input = make_input();
        const auto result = execute_fun_007682c0_machine_effect(input, body);

        require(result.caller_gate_open, "caller gate did not open");
        require(result.speed_gate_open, "speed gate did not open");
        require(result.x87_fsqrt_used, "x87 FSQRT path not reported");
        require(result.speed_3d == 10.0f, "3D speed mismatch");
        require(result.planar_speed == 10.0f, "planar speed mismatch");
        require(std::abs(result.speed_factor - (1.0f / 3.0f)) < 1e-6f,
                "speed factor mismatch");
        require(result.caller_scale == 1.0f, "caller load scale clamp mismatch");
        require(result.planar_geometry_valid, "planar geometry unexpectedly invalid");
        require(std::abs(result.reciprocal_like - 0.1f) < 1e-5f,
                "planar reciprocal mismatch");
        require(std::isfinite(result.response) && result.response > 0.0f,
                "response was not a finite positive retail effect");
        require(result.effect.gate_open,
                "native FUN_007682c0 effect gate did not open");
        require(std::isfinite(result.effect.accumulator_y_delta) &&
                    result.effect.accumulator_y_delta > 0.0,
                "native FUN_007682c0 delta was not produced");

        // FUN_0075ada0 uses a strict |projection| > 0.001f test. Equality must
        // keep the geometry valid but select the FLT_MAX/zero-reciprocal path.
        auto threshold_body = make_body(6.0, 0.0, 0.0);
        auto threshold_input = input;
        threshold_input.projection_field_x = 0.0f;
        threshold_input.projection_field_z = f32_from_bits(0x3a83126fu);
        const auto threshold_result =
            execute_fun_007682c0_machine_effect(threshold_input, threshold_body);
        require(threshold_result.planar_geometry_valid &&
                    threshold_result.reciprocal_like == 0.0f,
                "FUN_0075ada0 projection equality did not take near-zero path");

        // This vector distinguishes the two PC FUN_007595d0 f32 term spills
        // from a single f64 sum followed by one f32 spill. The exact PC result
        // is 0x492fbfb1; the collapsed form would produce 0x492fbfb0.
        auto rounding_body = make_body(6.5, 0.0, 0.0);
        write_f64(rounding_body, 0x20u, -500.0);
        write_f64(rounding_body, 0x120u, 100000.0);
        auto rounding_input = input;
        rounding_input.steering = 1.0f;
        rounding_input.load_terms = {1000000.0, 1000000.0, 1000000.0, 1000000.0};
        rounding_input.projection_field_x = 0.0f;
        rounding_input.projection_field_z = 65.0f;
        rounding_input.response_field_4054 = 1.0f;
        rounding_input.angle_mode = 2;
        const auto rounding_result =
            execute_fun_007682c0_machine_effect(rounding_input, rounding_body);
        require(rounding_result.speed_factor == f32_from_bits(0x3dcccccdu),
                "FUN_007682c0 0.1 speed-factor checkpoint mismatch");
        require(rounding_result.reciprocal_like == -10.0f,
                "FUN_0075ada0 rounding-vector reciprocal mismatch");
        require(f32_bits(rounding_result.response) == 0x492fbfb1u,
                "FUN_007595d0 independent f32 response-term spills regressed");

        auto signed_zero_input = rounding_input;
        signed_zero_input.response_field_4054 = -1.0f;
        const auto signed_zero_result =
            execute_fun_007682c0_machine_effect(signed_zero_input, rounding_body);
        require(signed_zero_result.response == 0.0f &&
                    std::signbit(signed_zero_result.response),
                "FUN_007595d0 signed-zero return checkpoint regressed");

        auto closed_input = input;
        closed_input.caller_gate_open = false;
        const auto caller_closed =
            execute_fun_007682c0_machine_effect(closed_input, body);
        require(!caller_closed.effect.gate_open &&
                    caller_closed.effect.accumulator_y_delta == 0.0,
                "closed caller gate produced an effect");

        auto low_speed_body = make_body(2.0, 1.0, 2.0);
        const auto speed_closed =
            execute_fun_007682c0_machine_effect(input, low_speed_body);
        require(!speed_closed.speed_gate_open &&
                    !speed_closed.effect.gate_open &&
                    speed_closed.effect.accumulator_y_delta == 0.0,
                "low speed gate produced an effect");

        bool malformed_rejected = false;
        try {
            (void)execute_fun_007682c0_machine_effect(
                input,
                std::vector<std::uint8_t>(kBodyRecordSize - 1u, 0u));
        } catch (const std::invalid_argument&) {
            malformed_rejected = true;
        }
        require(malformed_rejected, "malformed BODY record failed open");

        bool nonfinite_rejected = false;
        try {
            auto invalid = input;
            invalid.steering = std::numeric_limits<float>::quiet_NaN();
            (void)execute_fun_007682c0_machine_effect(invalid, body);
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        require(nonfinite_rejected, "non-finite raw input failed open");

        // Enter the real composed pass chain and stop at the first half-step.
        // By that point the raw input must have been converted to a native
        // effect and applied to BODY0 +0x50.
        bool stopped_after_pass = false;
        bool half_step_saw_delta = false;
        try {
            (void)execute_fun_00770e80_motion_read_machine_input_provider_chain(
                0.5,
                body,
                [&](std::size_t) {
                    Fun0076d100MotionReadMachineInputProviderCallbacks callbacks{};
                    callbacks.contact_factor = [] {};
                    callbacks.wheel_update = [] {};
                    callbacks.contact_response = [] {};
                    callbacks.contact_outer_input_provider = [] {
                        return make_contact_outer_input();
                    };
                    callbacks.motion_read_input_provider = [input] { return input; };
                    return callbacks;
                },
                [&](std::size_t pass_index,
                    double,
                    const std::vector<std::uint8_t>& current_body_bytes)
                    -> Fun00765470MachineScalarHalfStepInput {
                    if (pass_index == 0u) {
                        half_step_saw_delta =
                            read_f64(current_body_bytes, 0x50u) != 7.0;
                    }
                    throw std::runtime_error("s6-stop-after-machine-effect");
                },
                [](std::size_t) {});
        } catch (const std::runtime_error& exc) {
            stopped_after_pass =
                std::string(exc.what()) == "s6-stop-after-machine-effect";
        }
        require(stopped_after_pass && half_step_saw_delta,
                "half-step did not observe native FUN_007682c0 BODY0 delta");

        std::cout
            << "{\"format\":\"" << kNativeFun007682c0MachineEffectFormat << "\","
            << "\"ready\":true,"
            << "\"retail_x87_fsqrt\":true,"
            << "\"retail_x87_control_word_0x027f\":true,"
            << "\"host_std_sqrt_used\":false,"
            << "\"planar_projection_equal_0_001_near_zero\":true,"
            << "\"response_independent_f32_term_spills\":true,"
            << "\"response_signed_zero_preserved\":true,"
            << "\"body0_inputs_internal\":true,"
            << "\"effect_arithmetic_internal\":true,"
            << "\"body0_delta_before_half_step\":true}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

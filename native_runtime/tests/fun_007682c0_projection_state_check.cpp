#include "shift_fun_007682c0_projection_state.hpp"

#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
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
        Fun007682c0MachineInput legacy{};
        legacy.caller_gate_open = true;
        legacy.steering = 0.25f;
        legacy.load_terms = {-101.0, -102.0, -103.0, -104.0};
        legacy.projection_field_x = 123.0f;
        legacy.projection_field_z = -456.0f;
        legacy.response_field_4054 = 7.0f;
        legacy.angle_mode = 2;

        const Fun007682c0ExternalMachineInput external = legacy;
        const Fun007682c0DerivedProjectionState initial{};
        constexpr float derived_steering = -1.25f;
        const Fun00765c40LoadTerms derived_load_terms{11.0, 22.0, 33.0, 44.0};
        const auto composed = compose_fun_007682c0_machine_input(
            external,
            derived_steering,
            derived_load_terms,
            initial);
        require(composed.caller_gate_open && composed.steering == derived_steering,
                "derived steering was not consumed by production composition");
        require(composed.steering != legacy.steering,
                "legacy external steering leaked into production composition");
        require(composed.load_terms == derived_load_terms &&
                    composed.load_terms != legacy.load_terms,
                "FUN_00765c40 load-term ownership was not consumed");
        require(composed.angle_mode == kSelectedSessionPlayerDifficulty &&
                    composed.angle_mode == 1 &&
                    composed.angle_mode != legacy.angle_mode,
                "legacy external angle mode leaked into selected-session composition");
        require(f32_bits(composed.response_field_4054) ==
                    kBmwM3E36ResponseField4054Bits &&
                    composed.response_field_4054 != legacy.response_field_4054,
                "legacy external +0x4054 leaked into selected BMW composition");
        require(composed.projection_field_x == 0.0f &&
                    composed.projection_field_z == 0.0f,
                "legacy projection fields leaked into production composition");

        const auto derived = derive_fun_007682c0_projection_state(
            10.0,
            -3.0,
            10.5,
            -2.75,
            0.25);
        require(derived.field_x == 2.0f && derived.field_z == 1.0f,
                "PC projection-state delta/dt formula mismatch");

        const auto rounded = derive_fun_007682c0_projection_state(
            0.0,
            0.0,
            1.0,
            -1.0,
            3.0);
        require(f32_bits(rounded.field_x) == 0x3eaaaaabu &&
                    f32_bits(rounded.field_z) == 0xbeaaaaabu,
                "PC projection-state f32 store checkpoint mismatch");

        const auto second_input = compose_fun_007682c0_machine_input(
            external,
            derived_steering,
            derived_load_terms,
            rounded);
        require(f32_bits(second_input.projection_field_x) == 0x3eaaaaabu &&
                    f32_bits(second_input.projection_field_z) == 0xbeaaaaabu,
                "derived projection state was not consumed by next input");
        require(second_input.steering == derived_steering,
                "derived steering changed while composing next input");
        require(second_input.load_terms == derived_load_terms,
                "typed FUN_00765c40 load terms changed between compositions");
        require(second_input.angle_mode == kSelectedSessionPlayerDifficulty,
                "selected-session angle mode changed between compositions");
        require(f32_bits(second_input.response_field_4054) ==
                    kBmwM3E36ResponseField4054Bits,
                "selected BMW setup response changed between compositions");

        bool nonfinite_load_rejected = false;
        try {
            Fun00765c40LoadTerms invalid = derived_load_terms;
            invalid[2] = std::numeric_limits<double>::infinity();
            (void)compose_fun_007682c0_machine_input(
                external,
                derived_steering,
                invalid,
                initial);
        } catch (const std::invalid_argument&) {
            nonfinite_load_rejected = true;
        }
        require(nonfinite_load_rejected,
                "non-finite FUN_00765c40 load term failed open");

        bool zero_dt_rejected = false;
        try {
            (void)derive_fun_007682c0_projection_state(0.0, 0.0, 1.0, 1.0, 0.0);
        } catch (const std::invalid_argument&) {
            zero_dt_rejected = true;
        }
        require(zero_dt_rejected, "zero outer timestep failed open");

        bool nonfinite_rejected = false;
        try {
            (void)derive_fun_007682c0_projection_state(
                0.0,
                0.0,
                std::numeric_limits<double>::infinity(),
                1.0,
                1.0);
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        require(nonfinite_rejected, "non-finite BODY0 velocity failed open");

        std::cout
            << "{\"format\":\"" << kFun007682c0DerivedProjectionStateFormat << "\","
            << "\"ready\":true,"
            << "\"initial_fields_zero\":true,"
            << "\"legacy_steering_provider_value_ignored\":true,"
            << "\"legacy_load_term_provider_values_ignored\":true,"
            << "\"fun_00765c40_load_terms_consumed\":true,"
            << "\"legacy_response_4054_provider_value_ignored\":true,"
            << "\"legacy_angle_mode_provider_value_ignored\":true,"
            << "\"selected_session_angle_mode\":1,"
            << "\"legacy_projection_provider_values_ignored\":true,"
            << "\"post_outer_delta_over_dt\":true,"
            << "\"f32_store_checkpoint\":true}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

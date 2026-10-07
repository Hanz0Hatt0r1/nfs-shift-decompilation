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
        const Fun007560c0MotionReadGateSetup setup_open{true};
        const Fun007560c0MotionReadGateSetup setup_closed{false};
        const Fun007682c0DerivedProjectionState initial{};
        constexpr float derived_steering = -1.25f;
        const Fun00765c40LoadTerms derived_load_terms{11.0, 22.0, 33.0, 44.0};
        const auto composed = compose_fun_007682c0_machine_input(
            setup_open,
            derived_steering,
            derived_load_terms,
            initial);
        require(composed.caller_gate_open && composed.steering == derived_steering,
                "FUN_007560c0 setup gate was not consumed by composition");
        require(composed.load_terms == derived_load_terms,
                "FUN_00765c40 load-term ownership was not consumed");
        require(composed.angle_mode == kBmwNativeSilverstonePlayerDifficulty,
                "selected native Player Difficulty was not consumed as DAT_00c128cc");
        require(f32_bits(composed.response_field_4054) ==
                    kBmwM3E36ResponseField4054Bits,
                "selected BMW +0x4054 was not consumed");
        require(composed.projection_field_x == 0.0f &&
                    composed.projection_field_z == 0.0f,
                "initial projection state drift");

        const auto closed = compose_fun_007682c0_machine_input(
            setup_closed,
            derived_steering,
            derived_load_terms,
            initial);
        require(!closed.caller_gate_open,
                "FUN_007560c0 setup gate ownership drift");
        require(closed.angle_mode == kBmwNativeSilverstonePlayerDifficulty,
                "selected Player Difficulty changed with caller gate");

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
            setup_open,
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
        require(second_input.caller_gate_open,
                "FUN_007560c0 setup gate changed between compositions");
        require(second_input.angle_mode == kBmwNativeSilverstonePlayerDifficulty,
                "selected Player Difficulty changed between compositions");
        require(f32_bits(second_input.response_field_4054) ==
                    kBmwM3E36ResponseField4054Bits,
                "selected BMW setup response changed between compositions");

        bool nonfinite_load_rejected = false;
        try {
            Fun00765c40LoadTerms invalid = derived_load_terms;
            invalid[2] = std::numeric_limits<double>::infinity();
            (void)compose_fun_007682c0_machine_input(
                setup_open,
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
            << "\"fun_007560c0_setup_gate_consumed\":true,"
            << "\"fun_00765c40_load_terms_consumed\":true,"
            << "\"selected_player_difficulty\":"
            << kBmwNativeSilverstonePlayerDifficulty << ","
            << "\"late_raw_input_provider_required\":false,"
            << "\"post_outer_delta_over_dt\":true,"
            << "\"f32_store_checkpoint\":true}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

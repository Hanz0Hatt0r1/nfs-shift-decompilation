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
        legacy.load_terms = {1.0, 2.0, 3.0, 4.0};
        legacy.projection_field_x = 123.0f;
        legacy.projection_field_z = -456.0f;
        legacy.response_field_4054 = 7.0f;
        legacy.angle_mode = 2;

        const Fun007682c0ExternalMachineInput external = legacy;
        const Fun007682c0DerivedProjectionState initial{};
        constexpr float derived_steering = -1.25f;
        const auto composed = compose_fun_007682c0_machine_input(
            external,
            derived_steering,
            initial);
        require(composed.caller_gate_open && composed.steering == derived_steering,
                "derived steering was not consumed by production composition");
        require(composed.steering != legacy.steering,
                "legacy external steering leaked into production composition");
        require(composed.load_terms == legacy.load_terms &&
                    composed.response_field_4054 == 7.0f &&
                    composed.angle_mode == 2,
                "external machine input payload mismatch");
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
            rounded);
        require(f32_bits(second_input.projection_field_x) == 0x3eaaaaabu &&
                    f32_bits(second_input.projection_field_z) == 0xbeaaaaabu,
                "derived projection state was not consumed by next input");
        require(second_input.steering == derived_steering,
                "derived steering changed while composing next input");

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
            << "\"legacy_projection_provider_values_ignored\":true,"
            << "\"post_outer_delta_over_dt\":true,"
            << "\"f32_store_checkpoint\":true}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

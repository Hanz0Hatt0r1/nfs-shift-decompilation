#include "shift_contact_outer_kernel.hpp"

#include <cmath>
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

}  // namespace

int main() {
    try {
        ContactOuterSessionInput session{};
        session.planar_delta = {3.0, 0.0, 4.0};
        session.surface_scalar = 5.0;
        session.base_scalar = 10.0;
        session.projected_scalar = 2.0;
        session.alignment_scalar = 0.75;
        session.param_3 = 0.25;

        constexpr double previous_distance_state = 8.0;
        constexpr double outer_channel_b = 1.0 / 180.0;
        const auto external = compose_fun_007675f0_external_input(
            session,
            previous_distance_state,
            outer_channel_b);

        const double expected_cap =
            static_cast<double>(static_cast<float>(outer_channel_b));
        require(
            external.previous_distance_state == previous_distance_state,
            "FUN_007675f0 previous distance state changed during outer-channel join");
        require(
            external.distance_filter_cap == expected_cap,
            "FUN_007675f0 cap did not preserve PC f64-to-f32 narrowing");
        require(
            external.distance_filter_cap != outer_channel_b,
            "FUN_007675f0 cap bypassed PC f32 store/reload narrowing");
        require(
            external.planar_delta == session.planar_delta &&
                external.surface_scalar == session.surface_scalar &&
                external.base_scalar == session.base_scalar &&
                external.projected_scalar == session.projected_scalar &&
                external.alignment_scalar == session.alignment_scalar &&
                external.param_3 == session.param_3,
            "FUN_007675f0 outer-channel composition changed unrelated fields");

        bool non_finite_rejected = false;
        try {
            (void)compose_fun_007675f0_external_input(
                session,
                previous_distance_state,
                std::numeric_limits<double>::infinity());
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        require(
            non_finite_rejected,
            "non-finite FUN_00770e80 channel B was accepted");

        std::cout
            << "{\"format\":\"" << kFun007675f0OuterChannelBOwnershipFormat << "\","
            << "\"ready\":true,"
            << "\"receiver_offset\":\"0xa0\","
            << "\"body_offset_claimed\":false,"
            << "\"f64_to_f32_narrowing_preserved\":true,"
            << "\"production_provider_field_removed\":true,"
            << "\"remaining_production_fields\":6,"
            << "\"external_provider_count_reduced\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

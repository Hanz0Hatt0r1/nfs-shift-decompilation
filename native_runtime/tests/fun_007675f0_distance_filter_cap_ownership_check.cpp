#include "shift_contact_outer_kernel.hpp"
#include "shift_fun_007675f0_distance_filter_cap_setup.hpp"

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

void require_near(double actual, double expected, const char* message) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > 1e-12) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main() {
    try {
        Fun007675f0DistanceFilterCapSetup missing{};
        bool missing_rejected = false;
        try {
            validate_fun_007675f0_distance_filter_cap_setup(missing);
        } catch (const std::invalid_argument&) {
            missing_rejected = true;
        }
        require(missing_rejected,
                "FUN_007675f0 missing distance-filter-cap setup failed open");

        Fun007675f0DistanceFilterCapSetup non_finite{};
        non_finite.ready = true;
        non_finite.distance_filter_cap =
            std::numeric_limits<double>::quiet_NaN();
        bool non_finite_rejected = false;
        try {
            validate_fun_007675f0_distance_filter_cap_setup(non_finite);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        require(non_finite_rejected,
                "FUN_007675f0 non-finite distance-filter-cap setup failed open");

        ContactOuterKernelInput legacy{};
        legacy.planar_delta = {10.0, 0.0, 0.0};
        legacy.previous_distance_state = 2.0;
        legacy.distance_filter_cap = 91.0;
        legacy.surface_scalar = 10.0;
        legacy.base_scalar = 4.0;
        legacy.projected_scalar = 1.0;
        legacy.alignment_scalar = 0.5;
        legacy.param_3 = 2.0;

        const ContactOuterSessionInput session_input{legacy};
        require(session_input.compatibility_distance_filter_cap_seed_present &&
                    session_input.compatibility_distance_filter_cap_seed == 91.0,
                "legacy distance-filter-cap compatibility seed was not preserved");

        // Production composition must use setup-owned HDVehicle+0xa0, not the
        // historical per-pass value carried only by the compatibility seed.
        const auto resolved = compose_fun_007675f0_external_input(
            session_input,
            3.0,
            7.5);
        require_near(resolved.previous_distance_state, 3.0,
                     "session-owned previous state was not composed");
        require_near(resolved.distance_filter_cap, 7.5,
                     "setup-owned HDVehicle+0xa0 cap was not composed");
        require(resolved.distance_filter_cap !=
                    session_input.compatibility_distance_filter_cap_seed,
                "legacy per-pass cap leaked into production composition");

        const auto kernel_input = compose_fun_007675f0_input(
            resolved,
            Fun007675f0BodyMotion{20.0, 0.0});
        require_near(kernel_input.distance_filter_cap, 7.5,
                     "setup-owned cap drifted before FUN_00783a30");

        const double expected = execute_fun_00783a30_distance_filter(
            3.0,
            10.0,
            7.5,
            kContactDistanceFilterResponse);
        const auto result = execute_fun_007675f0_outer_arithmetic(kernel_input);
        require_near(result.filtered_distance_state, expected,
                     "FUN_007675f0 did not consume setup-owned cap");

        require(kFun007675f0DistanceFilterCapOffset == 0xa0u,
                "FUN_007675f0 distance-filter-cap source offset drift");

        std::cout
            << "{\"format\":\"" << kFun007675f0DistanceFilterCapOwnershipFormat << "\","
            << "\"ready\":true,"
            << "\"owner\":\"HDVehicle+0xa0\","
            << "\"per_pass_provider_field_present\":false,"
            << "\"setup_seed_fail_closed\":true,"
            << "\"legacy_seed_is_compatibility_only\":true,"
            << "\"xbox360_crosscheck_present\":true,"
            << "\"upstream_initializer_proven\":false,"
            << "\"external_provider_count_reduced\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

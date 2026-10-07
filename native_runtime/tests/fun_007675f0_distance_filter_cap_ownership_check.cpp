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
        require(kFun007675f0DistanceFilterCapOffset == 0xa0u,
                "FUN_007675f0 filter-cap source offset drift");

        bool missing_rejected = false;
        try {
            validate_fun_007675f0_distance_filter_cap_setup({});
        } catch (const std::invalid_argument&) {
            missing_rejected = true;
        }
        require(missing_rejected,
                "FUN_007675f0 missing filter-cap setup failed open");

        Fun007675f0DistanceFilterCapSetup nonfinite{};
        nonfinite.ready = true;
        nonfinite.distance_filter_cap =
            std::numeric_limits<double>::quiet_NaN();
        bool nonfinite_rejected = false;
        try {
            validate_fun_007675f0_distance_filter_cap_setup(nonfinite);
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        require(nonfinite_rejected,
                "FUN_007675f0 non-finite filter-cap setup failed open");

        Fun007675f0DistanceFilterCapSetup setup{};
        setup.ready = true;
        setup.distance_filter_cap = 7.25;
        validate_fun_007675f0_distance_filter_cap_setup(setup);

        ContactOuterKernelInput legacy{};
        legacy.planar_delta = {10.0, 0.0, 0.0};
        legacy.previous_distance_state = 91.0;
        legacy.distance_filter_cap = 123.5;
        legacy.surface_scalar = 10.0;
        legacy.base_scalar = 4.0;
        legacy.projected_scalar = 1.0;
        legacy.alignment_scalar = 0.5;
        legacy.param_3 = 2.0;
        const ContactOuterSessionInput session_input{legacy};
        require(session_input.compatibility_distance_filter_cap_seed_present &&
                    session_input.compatibility_distance_filter_cap_seed == 123.5,
                "legacy filter-cap compatibility seed was not preserved");

        const auto resolved = compose_fun_007675f0_external_input(
            session_input,
            2.0,
            setup.distance_filter_cap);
        require_near(resolved.previous_distance_state, 2.0,
                     "session distance state composition drift");
        require_near(resolved.distance_filter_cap, 7.25,
                     "setup-owned filter cap did not override legacy per-pass seed");

        SurfaceProbeNode production_node{};
        production_node.point = {0.0, 0.0, 0.0};
        production_node.normal = {0.0, 1.0, 0.0};
        production_node.distance = 1.0;
        production_node.radius = 1.0;

        ContactOuterSessionInput production{};
        production.surface_probe_node = &production_node;
        production.base_scalar = 4.0;
        production.projected_scalar = 1.0;
        production.alignment_scalar = 0.5;
        const auto production_resolved = compose_fun_007675f0_external_input(
            production,
            3.0,
            setup.distance_filter_cap);
        require(production_resolved.surface_probe_node == &production_node,
                "Phase 732 node boundary did not preserve Phase 731 production input");
        require_near(production_resolved.distance_filter_cap, 7.25,
                     "production payload altered setup-owned filter cap");

        std::cout
            << "{\"format\":\"" << kFun007675f0DistanceFilterCapOwnershipFormat << "\","
            << "\"ready\":true,"
            << "\"source_offset\":\"HDVehicle+0xa0\","
            << "\"setup_seed_fail_closed\":true,"
            << "\"legacy_seed_compatibility_only\":true,"
            << "\"production_per_pass_field_present\":false,"
            << "\"remaining_production_fields\":6,"
            << "\"external_provider_count_reduced\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

#include "shift_contact_outer_kernel.hpp"

#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {

using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void require_near(double actual, double expected, double tolerance, const char* message) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > tolerance) {
        throw std::runtime_error(message);
    }
}

void put_f64(std::vector<std::uint8_t>& bytes, std::size_t offset, double value) {
    std::uint64_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    if (offset + sizeof(bits) > bytes.size()) {
        throw std::runtime_error("fixture BODY write out of range");
    }
    for (std::size_t byte = 0u; byte < sizeof(bits); ++byte) {
        bytes[offset + byte] = static_cast<std::uint8_t>(
            (bits >> (byte * 8u)) & 0xffu);
    }
}

}  // namespace

int main() {
    try {
        std::vector<std::uint8_t> body(0x170u, 0u);
        // Values deliberately require an f64 -> f32 spill before FUN_00759210.
        put_f64(body, kFun007675f0Body0PositionXOffset, 0.10000000074505806);
        put_f64(body, kFun007675f0Body0PositionYOffset, 0.0);
        put_f64(body, kFun007675f0Body0PositionZOffset, 0.0);
        put_f64(body, kFun007675f0Body0SpeedXOffset, 4.0);
        put_f64(body, kFun007675f0Body0SpeedZOffset, 6.0);

        const auto body_state = derive_fun_007675f0_body0_probe_state(body);
        const double expected_query_x =
            static_cast<double>(static_cast<float>(0.10000000074505806));
        require_near(
            body_state.query_point[0], expected_query_x, 0.0,
            "BODY0 query-point f32 spill mismatch");
        require_near(body_state.query_point[1], 0.0, 0.0,
                     "BODY0 query-point Y mismatch");
        require_near(body_state.query_point[2], 0.0, 0.0,
                     "BODY0 query-point Z mismatch");
        require_near(body_state.motion.speed_x, 4.0, 0.0,
                     "BODY0 speed X mismatch");
        require_near(body_state.motion.speed_z, 6.0, 0.0,
                     "BODY0 speed Z mismatch");

        // With normal +Z, FUN_007ade70 produces horizontal direction +X.
        // The probe therefore returns node.point + direction*radius.
        SurfaceProbeNode node{};
        node.point = {0.0, 0.0, -1.0};
        node.normal = {0.0, 0.0, 1.0};
        node.distance = 1.0;
        node.radius = 2.0;

        ContactOuterSessionInput session{};
        session.surface_probe_node = &node;
        session.base_scalar = 4.0;
        session.projected_scalar = 1.0;
        session.alignment_scalar = 0.5;
        session.param_3 = 2.0;

        const auto external = compose_fun_007675f0_external_input(
            session,
            3.0,
            7.25);
        require(external.surface_probe_node == &node,
                "surface-probe node was not preserved through session composition");

        const auto resolved = resolve_fun_007675f0_surface_probe_input(
            external,
            body_state);
        const float query_x = static_cast<float>(body_state.query_point[0]);
        const float expected_dx = static_cast<float>(2.0f - query_x);
        require_near(
            resolved.planar_delta[0],
            static_cast<double>(expected_dx),
            0.0,
            "FUN_00759210-derived planar X mismatch");
        require_near(resolved.planar_delta[1], 0.0, 0.0,
                     "FUN_00759210-derived planar Y mismatch");
        require_near(resolved.planar_delta[2], -1.0, 0.0,
                     "FUN_00759210-derived planar Z mismatch");
        require_near(resolved.surface_scalar, 2.0, 0.0,
                     "FUN_00759210 returned scalar handoff mismatch");
        require_near(resolved.previous_distance_state, 3.0, 0.0,
                     "distance state drift across surface-probe join");
        require_near(resolved.distance_filter_cap, 7.25, 0.0,
                     "distance filter cap drift across surface-probe join");

        const auto kernel_input = compose_fun_007675f0_input(
            resolved,
            body_state.motion);
        const auto kernel_result = execute_fun_007675f0_outer_arithmetic(kernel_input);
        require(kernel_result.distance > 0.0,
                "surface-probe join produced a zero planar distance");
        require_near(
            kernel_result.gap,
            kernel_result.filtered_distance_state -
                (resolved.surface_scalar - kContactGapOffset),
            1e-12,
            "FUN_007675f0 gap did not consume filtered +0x4080 state");

        // Historical fixtures are still allowed to provide a precomputed
        // planar/scalar pair without a node pointer.
        ContactOuterSessionInput legacy{};
        legacy.compatibility_planar_surface_present = true;
        legacy.compatibility_planar_delta = {3.0, 0.0, 4.0};
        legacy.compatibility_surface_scalar = 9.0;
        legacy.base_scalar = 4.0;
        legacy.projected_scalar = 1.0;
        legacy.alignment_scalar = 0.5;
        legacy.param_3 = 2.0;
        const auto legacy_external = compose_fun_007675f0_external_input(
            legacy,
            2.0,
            1.0);
        const auto legacy_resolved = resolve_fun_007675f0_surface_probe_input(
            legacy_external,
            body_state);
        require_near(legacy_resolved.planar_delta[0], 3.0, 0.0,
                     "legacy planar X compatibility drift");
        require_near(legacy_resolved.planar_delta[2], 4.0, 0.0,
                     "legacy planar Z compatibility drift");
        require_near(legacy_resolved.surface_scalar, 9.0, 0.0,
                     "legacy surface scalar compatibility drift");

        std::cout
            << "{\"format\":\"" << kFun007675f0SurfaceProbeJoinFormat << "\","
            << "\"ready\":true,"
            << "\"pc_probe_function\":\"FUN_00759210\","
            << "\"body_query_point_f32_spill\":true,"
            << "\"planar_delta_derived_natively\":true,"
            << "\"surface_scalar_derived_natively\":true,"
            << "\"gap_uses_filtered_distance_state\":true,"
            << "\"remaining_production_fields\":5,"
            << "\"node_refresh_provider_internalized\":false,"
            << "\"external_provider_count_reduced\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

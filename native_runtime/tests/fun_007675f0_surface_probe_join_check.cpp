#include "shift_body_record_adapter.hpp"
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
    for (std::size_t byte = 0u; byte < sizeof(bits); ++byte) {
        bytes[offset + byte] =
            static_cast<std::uint8_t>((bits >> (byte * 8u)) & 0xffu);
    }
}

}  // namespace

int main() {
    try {
        std::vector<std::uint8_t> body(kBodyRecordSize, 0u);
        put_f64(body, kFun007675f0Body0PositionXOffset, 10.12500003);
        put_f64(body, kFun007675f0Body0PositionYOffset, 1.0);
        put_f64(body, kFun007675f0Body0PositionZOffset, 20.25);
        put_f64(body, kFun007675f0Body0SpeedXOffset, 20.0);
        put_f64(body, kFun007675f0Body0SpeedZOffset, 0.0);

        const auto query = derive_fun_007675f0_body0_probe_query_position(body);
        require_near(
            query[0],
            static_cast<double>(static_cast<float>(10.12500003)),
            0.0,
            "BODY0 X did not preserve PC f64-to-f32 query spill");
        require_near(query[1], 1.0, 0.0,
                     "BODY0 Y query spill mismatch");
        require_near(query[2], 20.25, 0.0,
                     "BODY0 Z query spill mismatch");

        SurfaceProbeNode node{};
        node.point = {20.0, 0.0, 30.0};
        node.normal = {0.0, 1.0, 0.0};
        node.distance = 1.0;
        node.radius = 2.0;

        const auto joined = execute_fun_007675f0_surface_probe_join(query, node);
        require_near(joined.probe.point[0], 22.0, 0.0,
                     "FUN_00759210 returned point X mismatch");
        require_near(joined.probe.point[2], 30.0, 0.0,
                     "FUN_00759210 returned point Z mismatch");
        require_near(joined.surface_scalar, 2.0, 0.0,
                     "FUN_00759210 scalar output was not reused by FUN_007675f0");

        const double expected_dx = static_cast<double>(static_cast<float>(
            static_cast<float>(22.0) - static_cast<float>(query[0])));
        const double expected_dy = static_cast<double>(static_cast<float>(
            static_cast<float>(0.0) - static_cast<float>(query[1])));
        const double expected_dz = static_cast<double>(static_cast<float>(
            static_cast<float>(30.0) - static_cast<float>(query[2])));
        require_near(joined.planar_delta[0], expected_dx, 0.0,
                     "PC float32 returned-point minus BODY X join mismatch");
        require_near(joined.planar_delta[1], expected_dy, 0.0,
                     "PC float32 returned-point minus BODY Y join mismatch");
        require_near(joined.planar_delta[2], expected_dz, 0.0,
                     "PC float32 returned-point minus BODY Z join mismatch");

        ContactOuterSessionInput production{};
        production.surface_probe_node = &node;
        // Phase 732 predates the FUN_00759c90 caller join. Keep only that later
        // scalar on its explicit compatibility lane while testing the node join.
        production.compatibility_projected_scalar_present = true;
        production.compatibility_projected_scalar = 1.0;
        auto external = compose_fun_007675f0_external_input(
            production,
            3.0,
            1.0);
        external = resolve_fun_007675f0_surface_probe_outputs(external, query);
        require(external.surface_probe_node == &node,
                "surface-probe node boundary changed during resolution");
        require_near(external.planar_delta[0], expected_dx, 0.0,
                     "production planar delta was not derived from probe");
        require_near(external.surface_scalar, 2.0, 0.0,
                     "production surface scalar was not derived from probe");

        ContactOuterSessionInput missing_node{};
        missing_node.compatibility_projected_scalar_present = true;
        missing_node.compatibility_projected_scalar = 1.0;
        bool missing_node_rejected = false;
        try {
            (void)compose_fun_007675f0_external_input(missing_node, 3.0, 1.0);
        } catch (const std::invalid_argument&) {
            missing_node_rejected = true;
        }
        require(missing_node_rejected,
                "production contact-outer payload accepted missing surface-probe node");

        ContactOuterKernelInput legacy{};
        legacy.planar_delta = {9.0, 0.0, 8.0};
        legacy.previous_distance_state = 3.0;
        legacy.distance_filter_cap = 1.0;
        legacy.speed_x = 20.0;
        legacy.speed_z = 0.0;
        legacy.surface_scalar = 7.0;
        legacy.base_scalar = 4.0;
        legacy.projected_scalar = 1.0;
        legacy.alignment_scalar = 0.5;
        legacy.param_3 = 2.0;
        const ContactOuterSessionInput compatibility{legacy};
        const auto compatibility_external = compose_fun_007675f0_external_input(
            compatibility,
            3.0,
            1.0);
        require(compatibility_external.surface_probe_node == nullptr,
                "legacy compatibility unexpectedly invented a surface-probe node");
        require_near(compatibility_external.planar_delta[0], 9.0, 0.0,
                     "legacy planar delta compatibility drift");
        require_near(compatibility_external.surface_scalar, 7.0, 0.0,
                     "legacy surface scalar compatibility drift");

        std::cout
            << "{\"format\":\"" << kFun007675f0SurfaceProbeJoinFormat << "\","
            << "\"ready\":true,"
            << "\"pc_caller\":\"FUN_007675f0\","
            << "\"probe\":\"FUN_00759210\","
            << "\"body_position_f32_spill\":true,"
            << "\"planar_delta_internal\":true,"
            << "\"surface_scalar_internal\":true,"
            << "\"production_node_boundary_required\":true,"
            << "\"remaining_production_fields\":5,"
            << "\"external_provider_count_reduced\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

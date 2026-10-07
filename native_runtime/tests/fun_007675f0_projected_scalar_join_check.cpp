#include "shift_contact_outer_kernel.hpp"
#include "shift_fun_007675f0_projected_scalar.hpp"

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
        bytes[offset + byte] = static_cast<std::uint8_t>(
            (bits >> (byte * 8u)) & 0xffu);
    }
}

}  // namespace

int main() {
    try {
        require(kWheelForceAggregateRecordCount == 3u,
                "FUN_00759c90 record count drift");
        require(kWheelForceAggregateRecordBaseOffset == 0x7f0u,
                "FUN_00759c90 record base drift");
        require(kWheelForceAggregateRecordStride == 0xa80u,
                "FUN_00759c90 byte stride drift");
        require(kWheelForceAggregateVectorAOffset == 0xb0u &&
                    kWheelForceAggregateVectorBOffset == 0x98u &&
                    kWheelForceAggregatePointOffset == 0xf8u,
                "FUN_00759c90 record field geometry drift");

        std::array<WheelForceAggregateRecord, kWheelForceAggregateRecordCount> records{};
        records[0].scalar_at_base = 1.0;
        records[0].vector_a = {10.0, 0.0, 5.0};
        records[0].scalar_at_minus_8 = 0.0;
        records[0].vector_b = {0.0, 0.0, 0.0};
        records[0].point = {2.0, 0.0, 3.0};
        records[1].point = {1.0, 0.0, 1.0};
        records[2].point = {1.0, 0.0, 1.0};

        const WheelForceAggregateVector3d body_position{1.0, 0.0, 1.0};
        const auto aggregate =
            execute_fun_00759c90_vector_outputs(records, body_position);
        require_near(aggregate.total[0], 10.0, 0.0,
                     "FUN_00759c90 total X mismatch");
        require_near(aggregate.total[1], 0.0, 0.0,
                     "FUN_00759c90 total Y mismatch");
        require_near(aggregate.total[2], 5.0, 0.0,
                     "FUN_00759c90 total Z mismatch");
        require_near(aggregate.cross_total[0], 0.0, 0.0,
                     "FUN_00759c90 cross X mismatch");
        require_near(aggregate.cross_total[1], 15.0, 0.0,
                     "FUN_00759c90 cross Y mismatch");
        require_near(aggregate.cross_total[2], 0.0, 0.0,
                     "FUN_00759c90 cross Z mismatch");

        const auto joined = execute_fun_007675f0_projected_scalar_join(
            records,
            body_position,
            ContactOuterVector3d{3.0, 0.0, 4.0});
        require_near(joined.planar_direction[0], 0.6, 1e-6,
                     "projected-scalar planar direction X mismatch");
        require_near(joined.planar_direction[2], 0.8, 1e-6,
                     "projected-scalar planar direction Z mismatch");
        require_near(joined.aggregate_x, 10.0, 0.0,
                     "FUN_00759c90 caller X f32 spill mismatch");
        require_near(joined.aggregate_z, 5.0, 0.0,
                     "FUN_00759c90 caller Z f32 spill mismatch");
        require_near(joined.projected_scalar, 10.0, 1e-6,
                     "FUN_007675f0 projected scalar mismatch");

        std::vector<std::uint8_t> body(kBodyRecordSize, 0u);
        constexpr double kExactX = 1.0000000001;
        put_f64(body, body_record_offset::kOrigin[0], kExactX);
        put_f64(body, body_record_offset::kOrigin[1], -2.0);
        put_f64(body, body_record_offset::kOrigin[2], 3.0);
        const auto decoded_position = derive_fun_00759c90_body0_position(body);
        require_near(decoded_position[0], kExactX, 0.0,
                     "FUN_00759c90 BODY0 X was incorrectly narrowed to f32");
        require_near(decoded_position[1], -2.0, 0.0,
                     "FUN_00759c90 BODY0 Y mismatch");
        require_near(decoded_position[2], 3.0, 0.0,
                     "FUN_00759c90 BODY0 Z mismatch");

        SurfaceProbeNode node{};
        node.point = {0.0, 0.0, 0.0};
        node.normal = {0.0, 1.0, 0.0};
        node.radius = 1.0;
        ContactOuterSessionInput production{};
        production.surface_probe_node = &node;
        production.fun_00759c90_records = records;
        production.fun_00759c90_records_present = true;
        const auto external = compose_fun_007675f0_external_input(
            production, 2.0, 1.0);
        require(external.fun_00759c90_records_present,
                "production FUN_00759c90 record boundary was dropped");
        require(!external.compatibility_projected_scalar_present,
                "production record boundary unexpectedly selected compatibility scalar");

        ContactOuterSessionInput missing_records{};
        missing_records.surface_probe_node = &node;
        bool missing_records_rejected = false;
        try {
            (void)compose_fun_007675f0_external_input(missing_records, 2.0, 1.0);
        } catch (const std::invalid_argument&) {
            missing_records_rejected = true;
        }
        require(missing_records_rejected,
                "production contact-outer input accepted missing FUN_00759c90 records");

        std::cout
            << "{\"format\":\"" << kFun007675f0ProjectedScalarJoinFormat << "\","
            << "\"ready\":true,"
            << "\"pc_caller\":\"FUN_007675f0\","
            << "\"aggregate\":\"FUN_00759c90\","
            << "\"xbox_caller\":\"sub_825939F0\","
            << "\"xbox_aggregate\":\"sub_825899C0\","
            << "\"record_count\":3,"
            << "\"record_stride_bytes\":2688,"
            << "\"projected_scalar_internal\":true,"
            << "\"production_scalar_field_present\":false,"
            << "\"top_level_provider_count_reduced\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

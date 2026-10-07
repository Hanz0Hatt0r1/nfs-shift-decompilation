#include "shift_fun_007618f0_wheel_body_origin_ownership.hpp"

#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
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

void write_f64_le(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    double value) {
    std::uint64_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    for (std::size_t byte = 0u; byte < sizeof(bits); ++byte) {
        bytes[offset + byte] = static_cast<std::uint8_t>(
            (bits >> (byte * 8u)) & 0xffu);
    }
}

void write_origin(
    std::vector<std::uint8_t>& body_bytes,
    std::size_t body_index,
    double x,
    double y,
    double z) {
    const std::size_t base = body_index * kBodyRecordSize;
    write_f64_le(body_bytes, base + body_record_offset::kOrigin[0], x);
    write_f64_le(body_bytes, base + body_record_offset::kOrigin[1], y);
    write_f64_le(body_bytes, base + body_record_offset::kOrigin[2], z);
}

}  // namespace

int main() {
    try {
        require(kFun007618f0HdVehicleWheelPointer0820 == 0x820u,
                "FUN_007618f0 first HDVehicle wheel pointer offset drift");
        require(kFun007618f0HdVehicleWheelPointer12a0 == 0x12a0u,
                "FUN_007618f0 second HDVehicle wheel pointer offset drift");
        require(kBodyRecordSize == 0x170u,
                "persistent BODY record stride drift");

        const auto& topology = bmw_m3_e36_retail_wheel_spindle_body_topology();
        require(topology.body_count == 11u,
                "selected BMW BODY count drift");
        require(topology.wheel_body_indices[0] == 3u,
                "selected BMW FL wheel BODY index drift");
        require(topology.wheel_body_indices[1] == 4u,
                "selected BMW FR wheel BODY index drift");

        std::vector<std::uint8_t> bodies(
            topology.body_count * kBodyRecordSize,
            0u);
        write_origin(bodies, 3u, 10.0, 20.0, 30.0);
        write_origin(bodies, 4u, 14.0, 24.0, 34.0);

        Fun007618f0RemainingSourceInput remaining{};
        remaining.source_scalar_0338 = 5.0;
        remaining.source_vec_0918 = {1.0, 2.0, 3.0};

        const auto owned = compose_fun_007618f0_input_from_current_bmw_wheel_bodies(
            bodies,
            remaining);
        require(owned.fl_wheel_body_index == 3u,
                "FL wheel BODY ownership mismatch");
        require(owned.fr_wheel_body_index == 4u,
                "FR wheel BODY ownership mismatch");
        require_near(owned.fl_wheel_body_origin[0], 10.0, 0.0,
                     "FL wheel BODY origin X mismatch");
        require_near(owned.fr_wheel_body_origin[2], 34.0, 0.0,
                     "FR wheel BODY origin Z mismatch");

        const auto produced = execute_fun_007618f0_local_sample_producer(
            owned.producer_input);
        require_near(produced.pointer_midpoint[0], 12.0, 0.0,
                     "owned wheel BODY midpoint X mismatch");
        require_near(produced.pointer_midpoint[1], 22.0, 0.0,
                     "owned wheel BODY midpoint Y mismatch");
        require_near(produced.pointer_midpoint[2], 32.0, 0.0,
                     "owned wheel BODY midpoint Z mismatch");
        require_near(produced.local_base[0], 12.0, 0.0,
                     "owned local base X mismatch");
        require_near(produced.local_base[1], -5.0, 0.0,
                     "remaining source scalar join mismatch");
        require_near(produced.local_base[2], 32.0, 0.0,
                     "owned local base Z mismatch");
        require_near(produced.local_sample_3938[0], 13.0, 0.0,
                     "owned local sample X mismatch");
        require_near(produced.local_sample_3938[1], -3.0, 0.0,
                     "owned local sample Y mismatch");
        require_near(produced.local_sample_3938[2], 35.0, 0.0,
                     "owned local sample Z mismatch");

        bool cardinality_rejected = false;
        try {
            std::vector<std::uint8_t> short_buffer(
                10u * kBodyRecordSize,
                0u);
            (void)compose_fun_007618f0_input_from_current_bmw_wheel_bodies(
                short_buffer,
                remaining);
        } catch (const std::invalid_argument&) {
            cardinality_rejected = true;
        }
        require(cardinality_rejected,
                "selected BMW BODY cardinality mismatch was accepted");

        bool nonfinite_rejected = false;
        try {
            write_origin(
                bodies,
                3u,
                std::numeric_limits<double>::infinity(),
                20.0,
                30.0);
            (void)compose_fun_007618f0_input_from_current_bmw_wheel_bodies(
                bodies,
                remaining);
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        require(nonfinite_rejected,
                "non-finite wheel BODY origin was accepted");

        std::cout
            << "{\"format\":\"" << kFun007618f0WheelBodyOriginOwnershipFormat << "\","
            << "\"ready\":true,"
            << "\"hdvehicle_pointer_offsets\":[\"0x820\",\"0x12a0\"],"
            << "\"wheel_slots\":[\"FL\",\"FR\"],"
            << "\"wheel_body_indices\":[3,4],"
            << "\"body_record_stride\":\"0x170\","
            << "\"body_origin_offsets\":[\"0x0\",\"0x8\",\"0x10\"],"
            << "\"external_wheel_origin_vectors_remaining\":false,"
            << "\"remaining_source_fields\":[\"source+0x338\",\"source+0x918\"],"
            << "\"top_level_provider_count_reduced\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

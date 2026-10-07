#include "shift_fun_00765c40_selected_bmw_world_position.hpp"

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>

using namespace shift::runtime::physics;

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void put_f64(
    std::vector<std::uint8_t>& bytes,
    std::size_t body_index,
    std::size_t body_offset,
    double value) {
    const std::size_t offset = body_index * kBodyRecordSize + body_offset;
    if (offset + sizeof(value) > bytes.size()) {
        throw std::runtime_error("Phase739 f64 write out of range");
    }
    std::uint64_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    for (std::size_t byte = 0u; byte < sizeof(bits); ++byte) {
        bytes[offset + byte] =
            static_cast<std::uint8_t>((bits >> (byte * 8u)) & 0xffu);
    }
}

void put_f32(
    std::vector<std::uint8_t>& bytes,
    std::size_t body_index,
    std::size_t body_offset,
    float value) {
    const std::size_t offset = body_index * kBodyRecordSize + body_offset;
    if (offset + sizeof(value) > bytes.size()) {
        throw std::runtime_error("Phase739 f32 write out of range");
    }
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    for (std::size_t byte = 0u; byte < sizeof(bits); ++byte) {
        bytes[offset + byte] =
            static_cast<std::uint8_t>((bits >> (byte * 8u)) & 0xffu);
    }
}

void put_origin(
    std::vector<std::uint8_t>& bytes,
    std::size_t body_index,
    double x,
    double y,
    double z) {
    put_f64(bytes, body_index, body_record_offset::kOrigin[0], x);
    put_f64(bytes, body_index, body_record_offset::kOrigin[1], y);
    put_f64(bytes, body_index, body_record_offset::kOrigin[2], z);
}

std::vector<std::uint8_t> make_selected_bmw_body_bytes() {
    std::vector<std::uint8_t> bytes(
        kBmwM3E36RetailBodyCount * kBodyRecordSize,
        0u);
    put_origin(bytes, 0u, 100.0, 200.0, 300.0);
    put_origin(bytes, 3u, 10.0, 20.0, 30.0);
    put_origin(bytes, 4u, 14.0, 24.0, 34.0);
    put_f32(bytes, 0u, body_record_offset::kBasis[0], 1.0f);
    put_f32(bytes, 0u, body_record_offset::kBasis[4], 1.0f);
    put_f32(bytes, 0u, body_record_offset::kBasis[8], 1.0f);
    return bytes;
}

bool near(double actual, double expected) {
    return std::abs(actual - expected) <= 1e-12;
}

}  // namespace

int main() {
    try {
        auto bytes = make_selected_bmw_body_bytes();
        require(fun_00765c40_selected_bmw_body_domain(bytes),
                "Phase739 selected BMW BODY domain not recognized");

        const auto selected_source = selected_bmw_m3_e36_fun_007618f0_source();
        const auto first = execute_fun_00765c40_selected_bmw_world_position(bytes);
        require(first.wheel_ownership.fl_wheel_body_index == 3u &&
                    first.wheel_ownership.fr_wheel_body_index == 4u,
                "Phase739 BMW wheel BODY indices drift");
        require(first.wheel_ownership.fl_wheel_body_origin ==
                    CollisionQueryVector3d{10.0, 20.0, 30.0} &&
                    first.wheel_ownership.fr_wheel_body_origin ==
                    CollisionQueryVector3d{14.0, 24.0, 34.0},
                "Phase739 current wheel BODY origins drift");

        const double expected_local_y =
            -selected_source.source_scalar_0338 +
            selected_source.source_vec_0918[1];
        require(near(first.local_sample.local_sample_3938[0], 12.0) &&
                    near(first.local_sample.local_sample_3938[1], expected_local_y) &&
                    near(first.local_sample.local_sample_3938[2], 31.5),
                "Phase739 Phase728 local sample composition mismatch");
        require(near(first.world_transform.world_position[0], 112.0) &&
                    near(first.world_transform.world_position[1], 200.0 + expected_local_y) &&
                    near(first.world_transform.world_position[2], 331.5),
                "Phase739 Phase727 world-position composition mismatch");

        // A second authoritative pass view with changed persistent BODY bytes
        // must produce a different answer. This is the property used by the
        // existing current_body_observer after pass 0's half-step.
        put_origin(bytes, 0u, 101.0, 202.0, 303.0);
        put_origin(bytes, 3u, 20.0, 30.0, 40.0);
        put_origin(bytes, 4u, 24.0, 34.0, 44.0);
        const auto second = execute_fun_00765c40_selected_bmw_world_position(bytes);
        require(second.wheel_ownership.fl_wheel_body_origin ==
                    CollisionQueryVector3d{20.0, 30.0, 40.0} &&
                    second.wheel_ownership.fr_wheel_body_origin ==
                    CollisionQueryVector3d{24.0, 34.0, 44.0},
                "Phase739 second-pass wheel BODY state was stale");
        require(near(second.world_transform.world_position[0], 123.0) &&
                    near(second.world_transform.world_position[1], 202.0 + expected_local_y + 10.0) &&
                    near(second.world_transform.world_position[2], 344.5),
                "Phase739 second-pass world position did not follow current BODY state");
        require(first.world_transform.world_position !=
                    second.world_transform.world_position,
                "Phase739 pass-local world position incorrectly reused snapshot state");

        std::vector<std::uint8_t> generic_two_body(2u * kBodyRecordSize, 0u);
        require(!fun_00765c40_selected_bmw_body_domain(generic_two_body),
                "Phase739 generic fixture misidentified as selected BMW domain");
        bool rejected = false;
        try {
            (void)execute_fun_00765c40_selected_bmw_world_position(generic_two_body);
        } catch (const std::invalid_argument&) {
            rejected = true;
        }
        require(rejected, "Phase739 non-BMW BODY domain failed open");

        std::cout
            << "{\"format\":\"" << kFun00765c40SelectedBmwWorldPositionFormat
            << "\",\"ready\":true,\"selected_body_count\":"
            << kBmwM3E36RetailBodyCount
            << ",\"pass_local_body_state\":true}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

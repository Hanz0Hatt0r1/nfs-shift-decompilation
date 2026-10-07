#include "shift_fun_007618f0_local_sample_producer.hpp"
#include "shift_fun_00765c40_world_position_transform.hpp"

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

void require_close(double actual, double expected, double tolerance, const char* message) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > tolerance) {
        throw std::runtime_error(message);
    }
}

void put_u32(BodyRecordBytes& record, std::size_t offset, std::uint32_t value) {
    for (std::size_t byte = 0u; byte < sizeof(value); ++byte) {
        record[offset + byte] = static_cast<std::uint8_t>((value >> (byte * 8u)) & 0xffu);
    }
}

void put_u64(BodyRecordBytes& record, std::size_t offset, std::uint64_t value) {
    for (std::size_t byte = 0u; byte < sizeof(value); ++byte) {
        record[offset + byte] = static_cast<std::uint8_t>((value >> (byte * 8u)) & 0xffu);
    }
}

void put_f32(BodyRecordBytes& record, std::size_t offset, float value) {
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    put_u32(record, offset, bits);
}

void put_f64(BodyRecordBytes& record, std::size_t offset, double value) {
    std::uint64_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    put_u64(record, offset, bits);
}

BodyRecordBytes make_identity_body(const CollisionQueryVector3d& origin) {
    BodyRecordBytes body{};
    for (std::size_t i = 0u; i < 3u; ++i) {
        put_f64(body, body_record_offset::kOrigin[i], origin[i]);
    }
    const float identity[9] = {
        1.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f,
        0.0f, 0.0f, 1.0f};
    for (std::size_t i = 0u; i < 9u; ++i) {
        put_f32(body, body_record_offset::kBasis[i], identity[i]);
    }
    return body;
}

}  // namespace

int main() {
    try {
        Fun007618f0LocalSampleProducerInput input{};
        input.hdvehicle_pointer_vec_0820 = {2.0, 4.0, 6.0};
        input.hdvehicle_pointer_vec_12a0 = {6.0, 8.0, 10.0};
        input.source_scalar_0338 = 3.0;
        input.source_vec_0918 = {1.0, 2.0, 3.0};

        const auto result = execute_fun_007618f0_local_sample_producer(input);
        require_close(result.pointer_midpoint[0], 4.0, 0.0,
                      "FUN_007618f0 midpoint X mismatch");
        require_close(result.pointer_midpoint[1], 6.0, 0.0,
                      "FUN_007618f0 midpoint Y mismatch");
        require_close(result.pointer_midpoint[2], 8.0, 0.0,
                      "FUN_007618f0 midpoint Z mismatch");
        require_close(result.local_base[0], 4.0, 0.0,
                      "FUN_007618f0 local-base X mismatch");
        require_close(result.local_base[1], -3.0, 0.0,
                      "FUN_007618f0 local-base Y override mismatch");
        require_close(result.local_base[2], 8.0, 0.0,
                      "FUN_007618f0 local-base Z mismatch");
        require_close(result.local_sample_3938[0], 5.0, 0.0,
                      "FUN_007618f0 local sample X mismatch");
        require_close(result.local_sample_3938[1], -1.0, 0.0,
                      "FUN_007618f0 local sample Y mismatch");
        require_close(result.local_sample_3938[2], 11.0, 0.0,
                      "FUN_007618f0 local sample Z mismatch");

        // Compose the newly recovered source core with Phase 727's already
        // native final BODY0 transform. Identity basis makes the join explicit.
        const auto body = make_identity_body({100.0, 200.0, 300.0});
        const auto world = execute_fun_00765c40_world_position_transform(
            body,
            result.local_sample_3938);
        require_close(world.world_position[0], 105.0, 0.0,
                      "FUN_007618f0 -> FUN_00765c40 joined world X mismatch");
        require_close(world.world_position[1], 199.0, 0.0,
                      "FUN_007618f0 -> FUN_00765c40 joined world Y mismatch");
        require_close(world.world_position[2], 311.0, 0.0,
                      "FUN_007618f0 -> FUN_00765c40 joined world Z mismatch");

        bool nonfinite_pointer_rejected = false;
        try {
            auto invalid = input;
            invalid.hdvehicle_pointer_vec_0820[0] =
                std::numeric_limits<double>::quiet_NaN();
            (void)execute_fun_007618f0_local_sample_producer(invalid);
        } catch (const std::invalid_argument&) {
            nonfinite_pointer_rejected = true;
        }
        require(nonfinite_pointer_rejected,
                "non-finite FUN_007618f0 pointer vector failed open");

        bool nonfinite_source_rejected = false;
        try {
            auto invalid = input;
            invalid.source_scalar_0338 = std::numeric_limits<double>::infinity();
            (void)execute_fun_007618f0_local_sample_producer(invalid);
        } catch (const std::invalid_argument&) {
            nonfinite_source_rejected = true;
        }
        require(nonfinite_source_rejected,
                "non-finite FUN_007618f0 source scalar failed open");

        std::cout
            << "{\"format\":\"" << kFun007618f0LocalSampleProducerFormat << "\","
            << "\"ready\":true,"
            << "\"midpoint_scale\":0.5,"
            << "\"midpoint_y_replaced\":true,"
            << "\"source_scalar_0338_negated\":true,"
            << "\"source_vec_0918_added\":true,"
            << "\"phase727_transform_composes\":true,"
            << "\"input_storage_owners_joined\":false,"
            << "\"active_session_joined\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

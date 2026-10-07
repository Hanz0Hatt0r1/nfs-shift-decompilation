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

BodyRecordBytes make_body(
    const CollisionQueryVector3d& origin,
    const std::array<float, 9>& basis) {
    BodyRecordBytes body{};
    for (std::size_t i = 0u; i < 3u; ++i) {
        put_f64(body, body_record_offset::kOrigin[i], origin[i]);
    }
    for (std::size_t i = 0u; i < basis.size(); ++i) {
        put_f32(body, body_record_offset::kBasis[i], basis[i]);
    }
    return body;
}

}  // namespace

int main() {
    try {
        const std::array<float, 9> identity{
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f};
        const auto body = make_body({100.0, 200.0, 300.0}, identity);
        const auto identity_result = execute_fun_00765c40_world_position_transform(
            body,
            {1.5, -2.0, 4.0});
        require_close(identity_result.body_rotated_local[0], 1.5, 0.0,
                      "identity rotated X mismatch");
        require_close(identity_result.body_rotated_local[1], -2.0, 0.0,
                      "identity rotated Y mismatch");
        require_close(identity_result.body_rotated_local[2], 4.0, 0.0,
                      "identity rotated Z mismatch");
        require_close(identity_result.world_position[0], 101.5, 0.0,
                      "identity world X mismatch");
        require_close(identity_result.world_position[1], 198.0, 0.0,
                      "identity world Y mismatch");
        require_close(identity_result.world_position[2], 304.0, 0.0,
                      "identity world Z mismatch");

        const std::array<float, 9> basis{
            2.0f, 3.0f, 5.0f,
            7.0f, 11.0f, 13.0f,
            17.0f, 19.0f, 23.0f};
        const auto nontrivial_body = make_body({0.5, -1.0, 2.0}, basis);
        const auto result = execute_fun_00765c40_world_position_transform(
            nontrivial_body,
            {2.0, 4.0, 8.0});
        require_close(result.body_rotated_local[0], 56.0, 0.0,
                      "retail row-0 grouping/orientation mismatch");
        require_close(result.body_rotated_local[1], 162.0, 0.0,
                      "retail row-1 grouping/orientation mismatch");
        require_close(result.body_rotated_local[2], 294.0, 0.0,
                      "retail row-2 grouping/orientation mismatch");
        require_close(result.world_position[0], 56.5, 0.0,
                      "retail origin-add X mismatch");
        require_close(result.world_position[1], 161.0, 0.0,
                      "retail origin-add Y mismatch");
        require_close(result.world_position[2], 296.0, 0.0,
                      "retail origin-add Z mismatch");

        bool nonfinite_local_rejected = false;
        try {
            (void)execute_fun_00765c40_world_position_transform(
                body,
                {0.0, std::numeric_limits<double>::infinity(), 0.0});
        } catch (const std::invalid_argument&) {
            nonfinite_local_rejected = true;
        }
        require(nonfinite_local_rejected,
                "non-finite local sample position failed open");

        bool nonfinite_basis_rejected = false;
        try {
            auto invalid_body = body;
            put_f32(
                invalid_body,
                body_record_offset::kBasis[4],
                std::numeric_limits<float>::quiet_NaN());
            (void)execute_fun_00765c40_world_position_transform(
                invalid_body,
                {0.0, 0.0, 0.0});
        } catch (const std::invalid_argument&) {
            nonfinite_basis_rejected = true;
        }
        require(nonfinite_basis_rejected,
                "non-finite BODY0 basis failed open");

        std::cout
            << "{\"format\":\"" << kFun00765c40WorldPositionTransformFormat << "\","
            << "\"ready\":true,"
            << "\"body_origin_offsets\":[0,8,16],"
            << "\"body_basis_offset_hex\":\"0xd4\","
            << "\"local_sample_offset_hex\":\"0x3938\","
            << "\"matrix_shape\":\"3x3-f32-times-f64-vec3\","
            << "\"origin_add_native\":true,"
            << "\"local_sample_producer_internalized\":false,"
            << "\"per_pass_body_snapshot_joined\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

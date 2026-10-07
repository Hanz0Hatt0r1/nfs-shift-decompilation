#include "shift_fun_00765c40_world_position_transform.hpp"

#include <cmath>
#include <cstdint>
#include <cstring>
#include <stdexcept>

namespace shift::runtime::physics {
namespace {

std::uint32_t read_u32_le(const BodyRecordBytes& record, std::size_t offset) {
    if (offset > record.size() || record.size() - offset < sizeof(std::uint32_t)) {
        throw std::out_of_range("FUN_00765c40 BODY0 f32 read out of range");
    }
    std::uint32_t value = 0u;
    for (std::size_t byte = 0u; byte < sizeof(value); ++byte) {
        value |= static_cast<std::uint32_t>(record[offset + byte]) << (byte * 8u);
    }
    return value;
}

std::uint64_t read_u64_le(const BodyRecordBytes& record, std::size_t offset) {
    if (offset > record.size() || record.size() - offset < sizeof(std::uint64_t)) {
        throw std::out_of_range("FUN_00765c40 BODY0 f64 read out of range");
    }
    std::uint64_t value = 0u;
    for (std::size_t byte = 0u; byte < sizeof(value); ++byte) {
        value |= static_cast<std::uint64_t>(record[offset + byte]) << (byte * 8u);
    }
    return value;
}

float read_f32_le(const BodyRecordBytes& record, std::size_t offset) {
    const std::uint32_t bits = read_u32_le(record, offset);
    float value = 0.0f;
    std::memcpy(&value, &bits, sizeof(value));
    if (!std::isfinite(value)) {
        throw std::invalid_argument("FUN_00765c40 BODY0 basis must be finite");
    }
    return value;
}

double read_f64_le(const BodyRecordBytes& record, std::size_t offset) {
    const std::uint64_t bits = read_u64_le(record, offset);
    double value = 0.0;
    std::memcpy(&value, &bits, sizeof(value));
    if (!std::isfinite(value)) {
        throw std::invalid_argument("FUN_00765c40 BODY0 origin must be finite");
    }
    return value;
}

double retail_store_f64(long double value) {
    const double stored = static_cast<double>(value);
    if (!std::isfinite(stored)) {
        throw std::invalid_argument("FUN_00765c40 world-position transform overflowed f64");
    }
    return stored;
}

long double mul(float lhs, double rhs) {
    return static_cast<long double>(lhs) * static_cast<long double>(rhs);
}

}  // namespace

Fun00765c40WorldPositionTransformResult
execute_fun_00765c40_world_position_transform(
    const BodyRecordBytes& body0,
    const CollisionQueryVector3d& local_sample_position) {
    for (double value : local_sample_position) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "FUN_00765c40 local sample position must be finite");
        }
    }

    float basis[9]{};
    for (std::size_t index = 0u; index < body_record_offset::kBasis.size(); ++index) {
        basis[index] = read_f32_le(body0, body_record_offset::kBasis[index]);
    }

    double origin[3]{};
    for (std::size_t index = 0u; index < body_record_offset::kOrigin.size(); ++index) {
        origin[index] = read_f64_le(body0, body_record_offset::kOrigin[index]);
    }

    // Preserve the retail x87 instruction grouping rather than replacing it
    // with a generic matrix helper. FUN_007aefb0 evaluates row 0 as
    // (m01*y + m00*x) + m02*z, then rows 1/2 in x,y,z order, storing each row
    // to f64 before FUN_00753590 adds BODY0 origin.
    const long double row0 =
        (mul(basis[1], local_sample_position[1]) +
         mul(basis[0], local_sample_position[0])) +
        mul(basis[2], local_sample_position[2]);
    const long double row1 =
        (mul(basis[3], local_sample_position[0]) +
         mul(basis[4], local_sample_position[1])) +
        mul(basis[5], local_sample_position[2]);
    const long double row2 =
        (mul(basis[6], local_sample_position[0]) +
         mul(basis[7], local_sample_position[1])) +
        mul(basis[8], local_sample_position[2]);

    Fun00765c40WorldPositionTransformResult result{};
    result.body_rotated_local = {
        retail_store_f64(row0),
        retail_store_f64(row1),
        retail_store_f64(row2),
    };
    result.world_position = {
        retail_store_f64(
            static_cast<long double>(result.body_rotated_local[0]) +
            static_cast<long double>(origin[0])),
        retail_store_f64(
            static_cast<long double>(result.body_rotated_local[1]) +
            static_cast<long double>(origin[1])),
        retail_store_f64(
            static_cast<long double>(result.body_rotated_local[2]) +
            static_cast<long double>(origin[2])),
    };
    return result;
}

}  // namespace shift::runtime::physics

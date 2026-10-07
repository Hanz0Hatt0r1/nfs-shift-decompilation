#pragma once

#include "shift_body_frame_integration.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeBodyRecordAdapterFormat =
    "SHIFT.NativeBodyRecordAdapter/1";

inline constexpr std::size_t kBodyRecordSize = 0x170u;
static_assert(kBodyRecordSize == kBodyArraySourceStride);

namespace body_record_offset {
inline constexpr std::array<std::size_t, 3> kOrigin = {0x00u, 0x08u, 0x10u};
inline constexpr std::array<std::size_t, 3> kCrossVector = {0x18u, 0x20u, 0x28u};
inline constexpr std::array<std::size_t, 3> kPreparedVector = {0x30u, 0x38u, 0x40u};
inline constexpr std::array<std::size_t, 3> kAccumulatorA = {0x48u, 0x50u, 0x58u};
inline constexpr std::array<std::size_t, 3> kAccumulatorB = {0x60u, 0x68u, 0x70u};
inline constexpr std::array<std::size_t, 3> kMotionTriplet = {0x78u, 0x80u, 0x88u};
inline constexpr std::size_t kScalar0x90 = 0x90u;
inline constexpr std::array<std::size_t, 9> kSymmetricTensor = {
    0xb0u, 0xb4u, 0xb8u,
    0xbcu, 0xc0u, 0xc4u,
    0xc8u, 0xccu, 0xd0u,
};
inline constexpr std::array<std::size_t, 9> kBasis = {
    0xd4u, 0xd8u, 0xdcu,
    0xe0u, 0xe4u, 0xe8u,
    0xecu, 0xf0u, 0xf4u,
};
inline constexpr std::array<std::size_t, 3> kReciprocalCoefficients = {
    0x138u, 0x140u, 0x148u,
};
}  // namespace body_record_offset

using BodyRecordBytes = std::array<std::uint8_t, kBodyRecordSize>;

BodyFrameIntegrationState decode_fun_007bab70_body_record(
    const BodyRecordBytes& record);

BodyRecordBytes apply_fun_007bab70_result_to_body_record(
    const BodyRecordBytes& original,
    const BodyFrameIntegrationResult& result);

// Source-backed FUN_007682c0 application boundary. The PC retail source loads
// HDVehicle+0x33a0, which the BMW identity proof names as the chassis BODY
// pointer, and applies the visible scalar delta to BODY0 +0x50. The source
// performs an f32 read/add/store round-trip before widening back to f64; retain
// that narrowing here instead of substituting a host f64 add.
void apply_fun_007682c0_body0_accumulator_y_delta(
    std::vector<std::uint8_t>& body_bytes,
    double accumulator_y_delta);

std::vector<std::uint8_t> execute_fun_007b2270_body_buffer_with_basis_callback(
    const std::vector<std::uint8_t>& body_bytes,
    std::size_t body_count,
    double timestep,
    const BodyBasisRotationCallback& basis_rotation);

}  // namespace shift::runtime::physics

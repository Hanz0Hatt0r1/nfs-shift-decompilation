#include "shift_body_record_adapter.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>
#include <stdexcept>

namespace shift::runtime::physics {
namespace {

std::uint32_t read_u32_le(const BodyRecordBytes& record, std::size_t offset) {
    return static_cast<std::uint32_t>(record[offset]) |
           (static_cast<std::uint32_t>(record[offset + 1u]) << 8u) |
           (static_cast<std::uint32_t>(record[offset + 2u]) << 16u) |
           (static_cast<std::uint32_t>(record[offset + 3u]) << 24u);
}

std::uint64_t read_u64_le(const BodyRecordBytes& record, std::size_t offset) {
    std::uint64_t value = 0u;
    for (std::size_t byte = 0; byte < 8u; ++byte) {
        value |= static_cast<std::uint64_t>(record[offset + byte]) << (byte * 8u);
    }
    return value;
}

float read_f32_le(const BodyRecordBytes& record, std::size_t offset) {
    const std::uint32_t bits = read_u32_le(record, offset);
    float value = 0.0f;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

double read_f64_le(const BodyRecordBytes& record, std::size_t offset) {
    const std::uint64_t bits = read_u64_le(record, offset);
    double value = 0.0;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

void write_u32_le(BodyRecordBytes& record, std::size_t offset, std::uint32_t value) {
    for (std::size_t byte = 0; byte < 4u; ++byte) {
        record[offset + byte] =
            static_cast<std::uint8_t>((value >> (byte * 8u)) & 0xffu);
    }
}

void write_u64_le(BodyRecordBytes& record, std::size_t offset, std::uint64_t value) {
    for (std::size_t byte = 0; byte < 8u; ++byte) {
        record[offset + byte] =
            static_cast<std::uint8_t>((value >> (byte * 8u)) & 0xffu);
    }
}

void write_f32_le(BodyRecordBytes& record, std::size_t offset, float value) {
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    write_u32_le(record, offset, bits);
}

void write_f64_le(BodyRecordBytes& record, std::size_t offset, double value) {
    std::uint64_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    write_u64_le(record, offset, bits);
}

template <std::size_t N>
std::array<double, N> read_f64_array(
    const BodyRecordBytes& record,
    const std::array<std::size_t, N>& offsets) {
    std::array<double, N> result{};
    for (std::size_t index = 0; index < N; ++index) {
        result[index] = read_f64_le(record, offsets[index]);
    }
    return result;
}

template <std::size_t N>
std::array<float, N> read_f32_array(
    const BodyRecordBytes& record,
    const std::array<std::size_t, N>& offsets) {
    std::array<float, N> result{};
    for (std::size_t index = 0; index < N; ++index) {
        result[index] = read_f32_le(record, offsets[index]);
    }
    return result;
}

template <std::size_t N>
void write_f64_array(
    BodyRecordBytes& record,
    const std::array<std::size_t, N>& offsets,
    const std::array<double, N>& values) {
    for (std::size_t index = 0; index < N; ++index) {
        write_f64_le(record, offsets[index], values[index]);
    }
}

template <std::size_t N>
void write_f32_array(
    BodyRecordBytes& record,
    const std::array<std::size_t, N>& offsets,
    const std::array<float, N>& values) {
    for (std::size_t index = 0; index < N; ++index) {
        write_f32_le(record, offsets[index], values[index]);
    }
}

template <typename Range>
void require_finite_range(const Range& values, const char* label) {
    for (const auto value : values) {
        if (!std::isfinite(static_cast<double>(value))) {
            throw std::invalid_argument(label);
        }
    }
}

void require_finite_state_inputs(const BodyFrameIntegrationState& state) {
    require_finite_range(state.origin, "BODY origin contains non-finite value");
    require_finite_range(state.cross_vector, "BODY cross vector contains non-finite value");
    require_finite_range(state.prepared_vector, "BODY prepared vector contains non-finite value");
    require_finite_range(state.accumulators.angular, "BODY accumulator A contains non-finite value");
    require_finite_range(state.accumulators.linear, "BODY accumulator B contains non-finite value");
    require_finite_range(state.motion_triplet, "BODY motion triplet contains non-finite value");
    if (!std::isfinite(state.scalar_0x90)) {
        throw std::invalid_argument("BODY scalar +0x90 is non-finite");
    }
    require_finite_range(state.basis, "BODY basis contains non-finite value");
    require_finite_range(
        state.reciprocal_coefficients,
        "BODY reciprocal coefficients contain non-finite value");
}

void require_finite_writer_result(const BodyFrameIntegrationResult& result) {
    require_finite_range(result.state.origin, "BODY output origin contains non-finite value");
    require_finite_range(result.state.cross_vector, "BODY output cross vector contains non-finite value");
    require_finite_range(result.state.prepared_vector, "BODY output prepared vector contains non-finite value");
    require_finite_range(result.state.motion_triplet, "BODY output motion triplet contains non-finite value");
    require_finite_range(result.state.basis, "BODY output basis contains non-finite value");
    for (const auto& row : result.symmetric_tensor) {
        require_finite_range(row, "BODY output symmetric tensor contains non-finite value");
    }
}

BodyRecordBytes copy_record_from_buffer(
    const std::vector<std::uint8_t>& bytes,
    std::size_t base) {
    BodyRecordBytes record{};
    std::copy_n(bytes.begin() + static_cast<std::ptrdiff_t>(base),
                kBodyRecordSize,
                record.begin());
    return record;
}

void copy_record_to_buffer(
    std::vector<std::uint8_t>& bytes,
    std::size_t base,
    const BodyRecordBytes& record) {
    std::copy(record.begin(),
              record.end(),
              bytes.begin() + static_cast<std::ptrdiff_t>(base));
}

}  // namespace

BodyFrameIntegrationState decode_fun_007bab70_body_record(
    const BodyRecordBytes& record) {
    BodyFrameIntegrationState state{};
    state.origin = read_f64_array(record, body_record_offset::kOrigin);
    state.cross_vector = read_f64_array(record, body_record_offset::kCrossVector);
    state.prepared_vector = read_f64_array(record, body_record_offset::kPreparedVector);
    state.accumulators.angular =
        read_f64_array(record, body_record_offset::kAccumulatorA);
    state.accumulators.linear =
        read_f64_array(record, body_record_offset::kAccumulatorB);
    state.motion_triplet =
        read_f64_array(record, body_record_offset::kMotionTriplet);
    state.scalar_0x90 = read_f64_le(record, body_record_offset::kScalar0x90);
    state.basis = read_f32_array(record, body_record_offset::kBasis);
    state.reciprocal_coefficients =
        read_f64_array(record, body_record_offset::kReciprocalCoefficients);
    require_finite_state_inputs(state);
    return state;
}

BodyRecordBytes apply_fun_007bab70_result_to_body_record(
    const BodyRecordBytes& original,
    const BodyFrameIntegrationResult& result) {
    require_finite_writer_result(result);
    BodyRecordBytes record = original;
    write_f64_array(record, body_record_offset::kOrigin, result.state.origin);
    write_f64_array(record, body_record_offset::kCrossVector, result.state.cross_vector);
    write_f64_array(record, body_record_offset::kPreparedVector, result.state.prepared_vector);
    write_f64_array(record, body_record_offset::kMotionTriplet, result.state.motion_triplet);

    std::array<float, 9> tensor{};
    for (std::size_t row = 0; row < 3u; ++row) {
        for (std::size_t column = 0; column < 3u; ++column) {
            tensor[row * 3u + column] = result.symmetric_tensor[row][column];
        }
    }
    write_f32_array(record, body_record_offset::kSymmetricTensor, tensor);
    write_f32_array(record, body_record_offset::kBasis, result.state.basis);
    return record;
}

void apply_fun_007682c0_body0_accumulator_y_delta(
    std::vector<std::uint8_t>& body_bytes,
    double accumulator_y_delta) {
    if (!std::isfinite(accumulator_y_delta)) {
        throw std::invalid_argument(
            "FUN_007682c0 BODY0 accumulator delta must be finite");
    }
    if (body_bytes.size() < kBodyRecordSize ||
        body_bytes.size() % kBodyRecordSize != 0u) {
        throw std::invalid_argument(
            "FUN_007682c0 BODY0 accumulator writer requires exact BODY records");
    }

    auto record = copy_record_from_buffer(body_bytes, 0u);
    const std::size_t offset = body_record_offset::kAccumulatorA[1];
    const double current = read_f64_le(record, offset);
    if (!std::isfinite(current)) {
        throw std::invalid_argument(
            "FUN_007682c0 BODY0 accumulator +0x50 contains non-finite value");
    }

    // Exact source shape at PC SHIFT.exe.c:760242-760243:
    //   (double)((float)*(double *)(body + 0x50) + (float)delta)
    // Preserve both f32 narrowings and the f32 add before storing as f64.
    const float current_f32 = static_cast<float>(current);
    const float delta_f32 = static_cast<float>(accumulator_y_delta);
    const float next_f32 = current_f32 + delta_f32;
    if (!std::isfinite(static_cast<double>(current_f32)) ||
        !std::isfinite(static_cast<double>(delta_f32)) ||
        !std::isfinite(static_cast<double>(next_f32))) {
        throw std::invalid_argument(
            "FUN_007682c0 BODY0 accumulator f32 application overflowed");
    }

    write_f64_le(record, offset, static_cast<double>(next_f32));
    copy_record_to_buffer(body_bytes, 0u, record);
}

std::vector<std::uint8_t> execute_fun_007b2270_body_buffer_with_basis_callback(
    const std::vector<std::uint8_t>& body_bytes,
    std::size_t body_count,
    double timestep,
    const BodyBasisRotationCallback& basis_rotation) {
    if (!std::isfinite(timestep)) {
        throw std::invalid_argument("FUN_007b2270 timestep must be finite");
    }
    if (!basis_rotation) {
        throw std::invalid_argument("FUN_007b2270 requires a basis-rotation provider");
    }
    if (body_count > std::numeric_limits<std::size_t>::max() / kBodyRecordSize) {
        throw std::invalid_argument("FUN_007b2270 BODY count overflows byte domain");
    }
    const std::size_t expected_size = body_count * kBodyRecordSize;
    if (body_bytes.size() != expected_size) {
        throw std::invalid_argument("FUN_007b2270 BODY buffer size/count mismatch");
    }

    std::vector<std::uint8_t> output = body_bytes;
    for (std::size_t index = 0; index < body_count; ++index) {
        const std::size_t base = index * kBodyRecordSize;
        const auto record = copy_record_from_buffer(body_bytes, base);
        const auto state = decode_fun_007bab70_body_record(record);
        const auto pre_basis = advance_fun_007bab70_pre_basis(state, timestep);
        const auto basis_after_fun_007afdd0 =
            basis_rotation(pre_basis.state.basis, pre_basis.rotation_increment);
        const auto result = complete_fun_007bab70_post_basis(
            pre_basis,
            basis_after_fun_007afdd0,
            timestep);
        const auto updated = apply_fun_007bab70_result_to_body_record(record, result);
        copy_record_to_buffer(output, base, updated);
    }
    return output;
}

}  // namespace shift::runtime::physics

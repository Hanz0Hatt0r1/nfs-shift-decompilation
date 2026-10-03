#include "shift_body_record_adapter.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

namespace {

using namespace shift::runtime::physics;

void put_u32_le(BodyRecordBytes& record, std::size_t offset, std::uint32_t value) {
    for (std::size_t byte = 0; byte < 4u; ++byte) {
        record[offset + byte] =
            static_cast<std::uint8_t>((value >> (byte * 8u)) & 0xffu);
    }
}

void put_u64_le(BodyRecordBytes& record, std::size_t offset, std::uint64_t value) {
    for (std::size_t byte = 0; byte < 8u; ++byte) {
        record[offset + byte] =
            static_cast<std::uint8_t>((value >> (byte * 8u)) & 0xffu);
    }
}

void put_f32(BodyRecordBytes& record, std::size_t offset, float value) {
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    put_u32_le(record, offset, bits);
}

void put_f64(BodyRecordBytes& record, std::size_t offset, double value) {
    std::uint64_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    put_u64_le(record, offset, bits);
}

template <std::size_t N>
void put_f64_lane(
    BodyRecordBytes& record,
    const std::array<std::size_t, N>& offsets,
    const std::array<double, N>& values) {
    for (std::size_t index = 0; index < N; ++index) {
        put_f64(record, offsets[index], values[index]);
    }
}

template <std::size_t N>
void put_f32_lane(
    BodyRecordBytes& record,
    const std::array<std::size_t, N>& offsets,
    const std::array<float, N>& values) {
    for (std::size_t index = 0; index < N; ++index) {
        put_f32(record, offsets[index], values[index]);
    }
}

BodyRecordBytes make_record(double origin_x, double cross_x, std::uint8_t seed) {
    BodyRecordBytes record{};
    record.fill(seed);
    put_f64_lane(record, body_record_offset::kOrigin,
                 std::array<double, 3>{origin_x, 2.0, 3.0});
    put_f64_lane(record, body_record_offset::kCrossVector,
                 std::array<double, 3>{cross_x, 0.0, 0.0});
    put_f64_lane(record, body_record_offset::kPreparedVector,
                 std::array<double, 3>{10.0, 20.0, 30.0});
    put_f64_lane(record, body_record_offset::kAccumulatorA,
                 std::array<double, 3>{2.0, 4.0, 6.0});
    put_f64_lane(record, body_record_offset::kAccumulatorB,
                 std::array<double, 3>{1.0, 2.0, 3.0});
    put_f64_lane(record, body_record_offset::kMotionTriplet,
                 std::array<double, 3>{4.0, 5.0, 6.0});
    put_f64(record, body_record_offset::kScalar0x90, 0.5);
    put_f32_lane(record, body_record_offset::kBasis,
                 std::array<float, 9>{
                     1.0f, 0.0f, 0.0f,
                     0.0f, 1.0f, 0.0f,
                     0.0f, 0.0f, 1.0f});
    put_f64_lane(record, body_record_offset::kReciprocalCoefficients,
                 std::array<double, 3>{2.0, 3.0, 5.0});
    return record;
}

std::vector<std::uint8_t> join_records(
    const BodyRecordBytes& first,
    const BodyRecordBytes& second) {
    std::vector<std::uint8_t> bytes;
    bytes.reserve(kBodyRecordSize * 2u);
    bytes.insert(bytes.end(), first.begin(), first.end());
    bytes.insert(bytes.end(), second.begin(), second.end());
    return bytes;
}

BodyRecordBytes extract_record(
    const std::vector<std::uint8_t>& bytes,
    std::size_t index) {
    BodyRecordBytes record{};
    const auto begin = bytes.begin() +
        static_cast<std::ptrdiff_t>(index * kBodyRecordSize);
    std::copy_n(begin, kBodyRecordSize, record.begin());
    return record;
}

bool is_writer_byte(std::size_t index) {
    const auto covers = [index](const auto& offsets, std::size_t width) {
        for (const auto offset : offsets) {
            if (index >= offset && index < offset + width) {
                return true;
            }
        }
        return false;
    };
    return covers(body_record_offset::kOrigin, 8u) ||
           covers(body_record_offset::kCrossVector, 8u) ||
           covers(body_record_offset::kPreparedVector, 8u) ||
           covers(body_record_offset::kMotionTriplet, 8u) ||
           covers(body_record_offset::kSymmetricTensor, 4u) ||
           covers(body_record_offset::kBasis, 4u);
}

void require_close(double actual, double expected, const char* label) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > 1e-12) {
        throw std::runtime_error(label);
    }
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        constexpr double timestep = 0.25;
        const auto first = make_record(1.0, 1.0, 0x11u);
        const auto second = make_record(10.0, 2.0, 0x22u);
        const auto input = join_records(first, second);

        std::vector<double> callback_rotation_x;
        const auto output = execute_fun_007b2270_body_buffer_with_basis_callback(
            input,
            2u,
            timestep,
            [&callback_rotation_x](
                const ConstraintRefreshFrame3f& basis,
                const BodyFrameIntegrationVector3d& increment) {
                callback_rotation_x.push_back(increment[0]);
                return basis;
            });

        if (output.size() != input.size() || callback_rotation_x.size() != 2u) {
            throw std::runtime_error("FUN_007b2270 raw BODY count mismatch");
        }
        require_close(callback_rotation_x[0], 0.25, "BODY[0] callback order mismatch");
        require_close(callback_rotation_x[1], 0.50, "BODY[1] callback order mismatch");

        const auto first_output = extract_record(output, 0u);
        const auto second_output = extract_record(output, 1u);
        const auto first_state = decode_fun_007bab70_body_record(first_output);
        const auto second_state = decode_fun_007bab70_body_record(second_output);
        require_close(first_state.origin[0], 2.0, "BODY[0] origin write mismatch");
        require_close(second_state.origin[0], 11.0, "BODY[1] origin write mismatch");
        require_close(first_state.motion_triplet[0], 4.125, "BODY motion write mismatch");
        require_close(first_state.prepared_vector[0], 10.5, "BODY prepared write mismatch");
        require_close(first_state.cross_vector[0], 21.0, "BODY cross write mismatch");

        for (std::size_t index = 0; index < kBodyRecordSize; ++index) {
            if (!is_writer_byte(index) && first_output[index] != first[index]) {
                throw std::runtime_error("BODY[0] unrelated byte changed");
            }
            if (!is_writer_byte(index) && second_output[index] != second[index]) {
                throw std::runtime_error("BODY[1] unrelated byte changed");
            }
        }

        bool size_mismatch_rejected = false;
        try {
            (void)execute_fun_007b2270_body_buffer_with_basis_callback(
                input,
                3u,
                timestep,
                [](const ConstraintRefreshFrame3f& basis,
                   const BodyFrameIntegrationVector3d&) { return basis; });
        } catch (const std::invalid_argument&) {
            size_mismatch_rejected = true;
        }
        if (!size_mismatch_rejected) {
            throw std::runtime_error("BODY buffer size/count mismatch accepted");
        }

        bool non_finite_rejected = false;
        std::size_t provider_calls = 0u;
        try {
            auto bad = first;
            put_f64(bad, body_record_offset::kCrossVector[0],
                    std::numeric_limits<double>::quiet_NaN());
            std::vector<std::uint8_t> bad_bytes(bad.begin(), bad.end());
            (void)execute_fun_007b2270_body_buffer_with_basis_callback(
                bad_bytes,
                1u,
                timestep,
                [&provider_calls](const ConstraintRefreshFrame3f& basis,
                                  const BodyFrameIntegrationVector3d&) {
                    ++provider_calls;
                    return basis;
                });
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected || provider_calls != 0u) {
            throw std::runtime_error("non-finite raw BODY input reached provider");
        }

        bool missing_provider_rejected = false;
        try {
            (void)execute_fun_007b2270_body_buffer_with_basis_callback(
                input, 2u, timestep, BodyBasisRotationCallback{});
        } catch (const std::invalid_argument&) {
            missing_provider_rejected = true;
        }
        if (!missing_provider_rejected) {
            throw std::runtime_error("missing raw BODY basis provider accepted");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeBodyRecordAdapter/1\","
            << "\"ready\":true,"
            << "\"body_record_size\":" << kBodyRecordSize << ","
            << "\"body_count\":2,"
            << "\"little_endian_codec_proven\":true,"
            << "\"writer_mask_preserved\":true,"
            << "\"retail_iteration_order_proven\":true,"
            << "\"size_mismatch_rejected\":true,"
            << "\"non_finite_rejected\":true,"
            << "\"basis_rotation_arithmetic_external\":true,"
            << "\"render_frame_scheduler_proven\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}

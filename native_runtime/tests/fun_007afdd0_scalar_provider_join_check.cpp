#include "shift_fun_007afdd0_scalar_provider_join.hpp"

#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

namespace {

using namespace shift::runtime::physics;

void put_u32_le(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    std::uint32_t value) {
    for (std::size_t byte = 0; byte < 4u; ++byte) {
        bytes[offset + byte] = static_cast<std::uint8_t>(
            (value >> (byte * 8u)) & 0xffu);
    }
}

void put_u64_le(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    std::uint64_t value) {
    for (std::size_t byte = 0; byte < 8u; ++byte) {
        bytes[offset + byte] = static_cast<std::uint8_t>(
            (value >> (byte * 8u)) & 0xffu);
    }
}

void put_f32(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    float value) {
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    put_u32_le(bytes, offset, bits);
}

void put_f64(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    double value) {
    std::uint64_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    put_u64_le(bytes, offset, bits);
}

float get_f32(
    const std::vector<std::uint8_t>& bytes,
    std::size_t offset) {
    std::uint32_t bits = 0u;
    for (std::size_t byte = 0; byte < 4u; ++byte) {
        bits |= static_cast<std::uint32_t>(bytes[offset + byte]) << (byte * 8u);
    }
    float value = 0.0f;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

std::vector<std::uint8_t> make_body_buffer() {
    constexpr std::size_t body_count = 2u;
    std::vector<std::uint8_t> bytes(body_count * kBodyRecordSize, 0u);

    const std::array<float, 9> identity = {
        1.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f,
        0.0f, 0.0f, 1.0f,
    };
    for (std::size_t body = 0; body < body_count; ++body) {
        const std::size_t base = body * kBodyRecordSize;
        for (std::size_t index = 0; index < identity.size(); ++index) {
            put_f32(bytes, base + body_record_offset::kBasis[index], identity[index]);
        }
        bytes[base + 0x100u] = static_cast<std::uint8_t>(0xa0u + body);
    }

    // BODY 0 keeps zero rotation_increment. BODY 1 reaches (0,0,2) with dt=1.
    put_f64(
        bytes,
        kBodyRecordSize + body_record_offset::kCrossVector[2],
        2.0);
    return bytes;
}

void require_f32(float actual, float expected, const char* label) {
    if (!std::isfinite(actual) || actual != expected) {
        throw std::runtime_error(label);
    }
}

void require_basis(
    const std::vector<std::uint8_t>& bytes,
    std::size_t body,
    const std::array<float, 9>& expected,
    const char* label) {
    const std::size_t base = body * kBodyRecordSize;
    for (std::size_t index = 0; index < expected.size(); ++index) {
        require_f32(
            get_f32(bytes, base + body_record_offset::kBasis[index]),
            expected[index],
            label);
    }
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        const auto raw = make_body_buffer();
        std::vector<std::size_t> call_order;
        std::vector<BodyFrameIntegrationVector3d> observed_increments;

        const Fun007afdd0ScalarProvider provider =
            [&](std::size_t body_index,
                const ConstraintRefreshFrame3f&,
                const BodyFrameIntegrationVector3d& rotation_increment) {
                call_order.push_back(body_index);
                observed_increments.push_back(rotation_increment);
                Fun007afdd0ScalarBoundary scalars{};
                if (body_index == 0u) {
                    scalars.squared_magnitude_test = 0.0f;
                    scalars.sqrt_magnitude =
                        std::numeric_limits<float>::quiet_NaN();
                    scalars.sine = std::numeric_limits<float>::quiet_NaN();
                    scalars.cosine = std::numeric_limits<float>::quiet_NaN();
                    return scalars;
                }
                scalars.squared_magnitude_test = 4.0f;
                scalars.sqrt_magnitude = 2.0f;
                scalars.sine = 1.0f;
                scalars.cosine = 0.0f;
                return scalars;
            };

        const auto result =
            execute_fun_007b2270_body_buffer_with_fun_007afdd0_source_core_provider(
                raw,
                2u,
                1.0,
                provider);

        if (call_order != std::vector<std::size_t>{0u, 1u} ||
            result.provider_call_count != 2u ||
            result.applied_rotation_count != 1u ||
            result.zero_noop_count != 1u) {
            throw std::runtime_error(
                "FUN_007afdd0 scalar-provider BODY ordering mismatch");
        }
        if (observed_increments.size() != 2u ||
            observed_increments[0] != BodyFrameIntegrationVector3d{0.0, 0.0, 0.0} ||
            observed_increments[1] != BodyFrameIntegrationVector3d{0.0, 0.0, 2.0}) {
            throw std::runtime_error(
                "FUN_007afdd0 scalar provider saw wrong rotation increment");
        }

        require_basis(
            result.body_bytes,
            0u,
            {1.0f, 0.0f, 0.0f,
             0.0f, 1.0f, 0.0f,
             0.0f, 0.0f, 1.0f},
            "zero-path BODY basis changed");
        require_basis(
            result.body_bytes,
            1u,
            {0.0f, -1.0f, 0.0f,
             1.0f, 0.0f, 0.0f,
             0.0f, 0.0f, 1.0f},
            "source-core BODY basis mismatch");

        if (result.body_bytes[0x100u] != 0xa0u ||
            result.body_bytes[kBodyRecordSize + 0x100u] != 0xa1u) {
            throw std::runtime_error(
                "scalar-provider join changed unrelated BODY bytes");
        }

        bool missing_provider_rejected = false;
        try {
            (void)execute_fun_007b2270_body_buffer_with_fun_007afdd0_source_core_provider(
                raw,
                2u,
                1.0,
                {});
        } catch (const std::invalid_argument&) {
            missing_provider_rejected = true;
        }
        if (!missing_provider_rejected) {
            throw std::runtime_error("missing scalar provider accepted");
        }

        bool nonfinite_active_scalar_rejected = false;
        try {
            const Fun007afdd0ScalarProvider bad_provider =
                [](std::size_t body_index,
                   const ConstraintRefreshFrame3f&,
                   const BodyFrameIntegrationVector3d&) {
                    Fun007afdd0ScalarBoundary scalars{};
                    scalars.squared_magnitude_test = body_index == 0u ? 0.0f : 1.0f;
                    scalars.sqrt_magnitude = 1.0f;
                    scalars.sine = body_index == 0u
                        ? 0.0f
                        : std::numeric_limits<float>::infinity();
                    scalars.cosine = 1.0f;
                    return scalars;
                };
            (void)execute_fun_007b2270_body_buffer_with_fun_007afdd0_source_core_provider(
                raw,
                2u,
                1.0,
                bad_provider);
        } catch (const std::invalid_argument&) {
            nonfinite_active_scalar_rejected = true;
        }
        if (!nonfinite_active_scalar_rejected) {
            throw std::runtime_error("non-finite active scalar boundary accepted");
        }

        bool size_mismatch_rejected = false;
        try {
            auto bad = raw;
            bad.pop_back();
            (void)execute_fun_007b2270_body_buffer_with_fun_007afdd0_source_core_provider(
                bad,
                2u,
                1.0,
                provider);
        } catch (const std::invalid_argument&) {
            size_mismatch_rejected = true;
        }
        if (!size_mismatch_rejected) {
            throw std::runtime_error("BODY buffer size mismatch accepted");
        }

        std::cout
            << "{\"format\":\"" << kNativeFun007afdd0ScalarProviderJoinFormat << "\","
            << "\"ready\":true,"
            << "\"body_count\":2,"
            << "\"provider_call_count\":" << result.provider_call_count << ","
            << "\"applied_rotation_count\":" << result.applied_rotation_count << ","
            << "\"zero_noop_count\":" << result.zero_noop_count << ","
            << "\"source_core_used\":true,"
            << "\"unrelated_bytes_preserved\":true,"
            << "\"machine_scalar_production_ready\":false,"
            << "\"production_basis_callback_replacement_ready\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

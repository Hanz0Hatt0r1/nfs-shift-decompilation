#include "shift_fun_00770e80_two_half_step_schedule.hpp"
#include "shift_fun_007afdd0_scalar_provider_join.hpp"

#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using namespace shift::runtime::physics;

void put_u32_le(std::vector<std::uint8_t>& bytes, std::size_t offset, std::uint32_t value) {
    for (std::size_t byte = 0; byte < 4u; ++byte) {
        bytes[offset + byte] = static_cast<std::uint8_t>((value >> (byte * 8u)) & 0xffu);
    }
}

void put_u64_le(std::vector<std::uint8_t>& bytes, std::size_t offset, std::uint64_t value) {
    for (std::size_t byte = 0; byte < 8u; ++byte) {
        bytes[offset + byte] = static_cast<std::uint8_t>((value >> (byte * 8u)) & 0xffu);
    }
}

void put_f32(std::vector<std::uint8_t>& bytes, std::size_t offset, float value) {
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    put_u32_le(bytes, offset, bits);
}

void put_f64(std::vector<std::uint8_t>& bytes, std::size_t offset, double value) {
    std::uint64_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    put_u64_le(bytes, offset, bits);
}

double get_f64(const std::vector<std::uint8_t>& bytes, std::size_t offset) {
    std::uint64_t bits = 0u;
    for (std::size_t byte = 0; byte < 8u; ++byte) {
        bits |= static_cast<std::uint64_t>(bytes[offset + byte]) << (byte * 8u);
    }
    double value = 0.0;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

std::vector<std::uint8_t> make_body() {
    std::vector<std::uint8_t> bytes(kBodyRecordSize, 0u);
    const std::array<float, 9> identity = {
        1.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f,
        0.0f, 0.0f, 1.0f,
    };
    for (std::size_t index = 0; index < identity.size(); ++index) {
        put_f32(bytes, body_record_offset::kBasis[index], identity[index]);
    }
    put_f64(bytes, body_record_offset::kMotionTriplet[0], 4.0);
    put_f64(bytes, body_record_offset::kScalar0x90, 1.0);
    bytes[0x100u] = 0x5au;
    return bytes;
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        auto body_bytes = make_body();
        std::vector<std::string> order;
        std::vector<double> half_steps;
        std::size_t scalar_provider_calls = 0u;

        const Fun007afdd0ScalarProvider scalar_provider =
            [&](std::size_t body_index,
                const ConstraintRefreshFrame3f&,
                const BodyFrameIntegrationVector3d&) {
                if (body_index != 0u) {
                    throw std::runtime_error("unexpected BODY index in Phase 683 regression");
                }
                ++scalar_provider_calls;
                Fun007afdd0ScalarBoundary scalars{};
                scalars.squared_magnitude_test = 0.0f;
                scalars.sqrt_magnitude = std::numeric_limits<float>::quiet_NaN();
                scalars.sine = std::numeric_limits<float>::quiet_NaN();
                scalars.cosine = std::numeric_limits<float>::quiet_NaN();
                return scalars;
            };

        const auto schedule = execute_fun_00770e80_two_half_step_schedule(
            0.5,
            [&](std::size_t pass_index) {
                order.push_back("FUN_0076d100:" + std::to_string(pass_index));
            },
            [&](std::size_t pass_index, double half_timestep) {
                order.push_back("FUN_00765470:" + std::to_string(pass_index));
                half_steps.push_back(half_timestep);
                const auto integrated =
                    execute_fun_007b2270_body_buffer_with_fun_007afdd0_source_core_provider(
                        body_bytes,
                        1u,
                        half_timestep,
                        scalar_provider);
                body_bytes = integrated.body_bytes;
            },
            [&](std::size_t pass_index) {
                order.push_back("FUN_007b8810:" + std::to_string(pass_index));
            });

        const std::vector<std::string> expected_order = {
            "FUN_0076d100:0",
            "FUN_00765470:0",
            "FUN_007b8810:0",
            "FUN_0076d100:1",
            "FUN_00765470:1",
            "FUN_007b8810:1",
        };
        if (order != expected_order ||
            schedule.physics_pass_count != 2u ||
            schedule.half_step_count != 2u ||
            schedule.post_half_step_count != 2u ||
            schedule.half_timestep != 0.25 ||
            half_steps != std::vector<double>{0.25, 0.25}) {
            throw std::runtime_error("FUN_00770e80 two-half-step order mismatch");
        }
        if (scalar_provider_calls != 2u) {
            throw std::runtime_error("BODY integration did not execute once per half-step");
        }
        if (get_f64(body_bytes, body_record_offset::kOrigin[0]) != 2.0 ||
            get_f64(body_bytes, body_record_offset::kMotionTriplet[0]) != 4.0) {
            throw std::runtime_error("persistent BODY state did not cross both half-steps");
        }
        if (body_bytes[0x100u] != 0x5au) {
            throw std::runtime_error("two-half-step schedule changed unrelated BODY storage");
        }

        bool missing_callback_rejected = false;
        try {
            (void)execute_fun_00770e80_two_half_step_schedule(
                1.0,
                {},
                [](std::size_t, double) {},
                [](std::size_t) {});
        } catch (const std::invalid_argument&) {
            missing_callback_rejected = true;
        }
        if (!missing_callback_rejected) {
            throw std::runtime_error("missing FUN_0076d100 callback accepted");
        }

        bool nonfinite_timestep_rejected = false;
        try {
            (void)execute_fun_00770e80_two_half_step_schedule(
                std::numeric_limits<double>::infinity(),
                [](std::size_t) {},
                [](std::size_t, double) {},
                [](std::size_t) {});
        } catch (const std::invalid_argument&) {
            nonfinite_timestep_rejected = true;
        }
        if (!nonfinite_timestep_rejected) {
            throw std::runtime_error("non-finite outer timestep accepted");
        }

        std::cout
            << "{\"format\":\"" << kNativeFun00770e80TwoHalfStepScheduleFormat << "\","
            << "\"ready\":true,"
            << "\"pass_count\":2,"
            << "\"half_timestep\":" << schedule.half_timestep << ","
            << "\"anchor_order_proven\":true,"
            << "\"persistent_body_crosses_both_half_steps\":true,"
            << "\"callback_bodies_external\":true,"
            << "\"complete_fun_00770e80_semantics\":false,"
            << "\"rendered_frame_cadence_proven\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

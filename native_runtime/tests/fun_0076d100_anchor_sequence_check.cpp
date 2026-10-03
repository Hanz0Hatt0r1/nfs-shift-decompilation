#include "shift_fun_0076d100_anchor_sequence.hpp"
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
    bytes[0x100u] = 0x6bu;
    return bytes;
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        std::vector<std::string> single_pass_order;
        const auto single = execute_fun_0076d100_required_anchor_sequence(
            [&] { single_pass_order.push_back(kFun00765c40ContactFactorFunction); },
            [&] { single_pass_order.push_back(kFun00758b50WheelUpdateFunction); },
            [&] { single_pass_order.push_back(kFun00766510ContactResponseFunction); },
            [&] { single_pass_order.push_back(kFun007675f0ContactOuterFunction); },
            [&] { single_pass_order.push_back(kFun007682c0MotionReadGateFunction); });

        const std::vector<std::string> expected_single = {
            kFun00765c40ContactFactorFunction,
            kFun00758b50WheelUpdateFunction,
            kFun00766510ContactResponseFunction,
            kFun007675f0ContactOuterFunction,
            kFun007682c0MotionReadGateFunction,
        };
        if (single_pass_order != expected_single ||
            single.contact_factor_count != 1u ||
            single.wheel_update_count != 1u ||
            single.contact_response_count != 1u ||
            single.tail_invocation_count != 1u ||
            single.contact_outer_count != 1u ||
            single.motion_read_gate_count != 1u) {
            throw std::runtime_error("FUN_0076d100 required-anchor order mismatch");
        }

        auto body_bytes = make_body();
        std::vector<std::string> nested_order;
        std::size_t scalar_provider_calls = 0u;

        const Fun007afdd0ScalarProvider scalar_provider =
            [&](std::size_t body_index,
                const ConstraintRefreshFrame3f&,
                const BodyFrameIntegrationVector3d&) {
                if (body_index != 0u) {
                    throw std::runtime_error("unexpected BODY index in Phase 684 regression");
                }
                ++scalar_provider_calls;
                Fun007afdd0ScalarBoundary scalars{};
                scalars.squared_magnitude_test = 0.0f;
                scalars.sqrt_magnitude = std::numeric_limits<float>::quiet_NaN();
                scalars.sine = std::numeric_limits<float>::quiet_NaN();
                scalars.cosine = std::numeric_limits<float>::quiet_NaN();
                return scalars;
            };

        const auto outer = execute_fun_00770e80_two_half_step_schedule(
            0.5,
            [&](std::size_t pass_index) {
                const std::string suffix = ":" + std::to_string(pass_index);
                const auto pass = execute_fun_0076d100_required_anchor_sequence(
                    [&] { nested_order.push_back(std::string(kFun00765c40ContactFactorFunction) + suffix); },
                    [&] { nested_order.push_back(std::string(kFun00758b50WheelUpdateFunction) + suffix); },
                    [&] { nested_order.push_back(std::string(kFun00766510ContactResponseFunction) + suffix); },
                    [&] { nested_order.push_back(std::string(kFun007675f0ContactOuterFunction) + suffix); },
                    [&] { nested_order.push_back(std::string(kFun007682c0MotionReadGateFunction) + suffix); });
                if (pass.tail_invocation_count != 1u) {
                    throw std::runtime_error("FUN_00769ef0 tail was not entered exactly once");
                }
            },
            [&](std::size_t pass_index, double half_timestep) {
                nested_order.push_back(
                    std::string(kFun00765470HalfStep) + ":" + std::to_string(pass_index));
                const auto integrated =
                    execute_fun_007b2270_body_buffer_with_fun_007afdd0_source_core_provider(
                        body_bytes,
                        1u,
                        half_timestep,
                        scalar_provider);
                body_bytes = integrated.body_bytes;
            },
            [&](std::size_t pass_index) {
                nested_order.push_back(
                    std::string(kFun007b8810PostHalfStep) + ":" + std::to_string(pass_index));
            });

        const std::vector<std::string> expected_nested = {
            "FUN_00765c40:0",
            "FUN_00758b50:0",
            "FUN_00766510:0",
            "FUN_007675f0:0",
            "FUN_007682c0:0",
            "FUN_00765470:0",
            "FUN_007b8810:0",
            "FUN_00765c40:1",
            "FUN_00758b50:1",
            "FUN_00766510:1",
            "FUN_007675f0:1",
            "FUN_007682c0:1",
            "FUN_00765470:1",
            "FUN_007b8810:1",
        };
        if (nested_order != expected_nested ||
            outer.physics_pass_count != 2u ||
            outer.half_step_count != 2u ||
            outer.post_half_step_count != 2u) {
            throw std::runtime_error("nested outer/pass/half-step anchor order mismatch");
        }
        if (scalar_provider_calls != 2u ||
            get_f64(body_bytes, body_record_offset::kOrigin[0]) != 2.0 ||
            get_f64(body_bytes, body_record_offset::kMotionTriplet[0]) != 4.0) {
            throw std::runtime_error("persistent BODY state did not cross nested Phase 684 schedule");
        }
        if (body_bytes[0x100u] != 0x6bu) {
            throw std::runtime_error("nested Phase 684 schedule changed unrelated BODY storage");
        }

        bool missing_callback_rejected = false;
        try {
            (void)execute_fun_0076d100_required_anchor_sequence(
                {}, [] {}, [] {}, [] {}, [] {});
        } catch (const std::invalid_argument&) {
            missing_callback_rejected = true;
        }
        if (!missing_callback_rejected) {
            throw std::runtime_error("missing FUN_0076d100 anchor callback accepted");
        }

        std::cout
            << "{\"format\":\"" << kNativeFun0076d100AnchorSequenceFormat << "\","
            << "\"ready\":true,"
            << "\"required_pass_anchor_order_proven\":true,"
            << "\"required_tail_anchor_order_proven\":true,"
            << "\"tail_invocation_count\":1,"
            << "\"nested_outer_two_pass_schedule_proven\":true,"
            << "\"persistent_body_crosses_nested_schedule\":true,"
            << "\"intervening_local_work_modeled\":false,"
            << "\"complete_fun_0076d100_semantics\":false,"
            << "\"complete_fun_00769ef0_semantics\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

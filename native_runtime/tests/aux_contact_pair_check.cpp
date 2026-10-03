#include "shift_aux_contact_response.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {

void require_close(
    double actual,
    double expected,
    double tolerance,
    const char* label,
    double& max_error) {

    const double error = std::abs(actual - expected);
    max_error = std::max(max_error, error);
    if (!std::isfinite(actual) || error > tolerance) {
        throw std::runtime_error(label);
    }
}

shift::runtime::physics::AuxContactPairInput base_pair() {
    using namespace shift::runtime::physics;
    AuxContactPairInput input{};
    input.body_frame = {
        1.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f,
        0.0f, 0.0f, 1.0f,
    };
    input.body_transform.angular = {0.0, 0.0, 0.0};
    input.body_transform.body_position = {0.0, 0.0, 0.0};
    input.body_transform.translation = {5.0, 4.0, 1.0};
    input.reference_point = {2.0, 3.0, 5.0};

    AuxContactRecord record{};
    record.active = true;
    record.point = {5.0, 4.0, 1.0};
    record.directional_curve = {0.0, 0.0, 0.0, 0.0};
    record.gain = 2.0;
    record.scale = 2.0;
    input.records[0] = record;
    input.records[1] = record;
    return input;
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;

        if (kAuxContactRecordCount != 2u ||
            kAuxContactRecordOffsets[0] != 0x37d8u ||
            kAuxContactRecordOffsets[1] != 0x3858u) {
            throw std::runtime_error("FUN_00766510 auxiliary record layout mismatch");
        }

        const auto both = execute_fun_00766510_aux_contact_pair(base_pair());
        if (both.applied_count != 2u ||
            !both.records[0].applied ||
            !both.records[1].applied) {
            throw std::runtime_error("FUN_00766510 two-call orchestration mismatch");
        }

        const double expected_first_angular[3] = {96.0, -160.0, 160.0};
        const double expected_first_linear[3] = {0.0, 32.0, 32.0};
        const double expected_final_angular[3] = {192.0, -320.0, 320.0};
        const double expected_final_linear[3] = {0.0, 64.0, 64.0};
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                both.records[0].body_accumulator.angular[component],
                expected_first_angular[component],
                0.0,
                "first auxiliary call angular accumulator",
                max_error);
            require_close(
                both.records[0].body_accumulator.linear[component],
                expected_first_linear[component],
                0.0,
                "first auxiliary call linear accumulator",
                max_error);
            require_close(
                both.body_accumulator.angular[component],
                expected_final_angular[component],
                0.0,
                "paired auxiliary angular accumulation",
                max_error);
            require_close(
                both.body_accumulator.linear[component],
                expected_final_linear[component],
                0.0,
                "paired auxiliary linear accumulation",
                max_error);
        }

        auto second_inactive = base_pair();
        second_inactive.records[1].active = false;
        const auto one =
            execute_fun_00766510_aux_contact_pair(second_inactive);
        if (one.applied_count != 1u ||
            !one.records[0].applied ||
            one.records[1].applied) {
            throw std::runtime_error("inactive second auxiliary record mismatch");
        }
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                one.body_accumulator.angular[component],
                expected_first_angular[component],
                0.0,
                "inactive second record angular preservation",
                max_error);
            require_close(
                one.body_accumulator.linear[component],
                expected_first_linear[component],
                0.0,
                "inactive second record linear preservation",
                max_error);
        }

        auto seeded = base_pair();
        seeded.body_accumulator.angular = {1.0, 2.0, 3.0};
        seeded.body_accumulator.linear = {4.0, 5.0, 6.0};
        seeded.records[0].active = false;
        seeded.records[1].active = false;
        const auto preserved =
            execute_fun_00766510_aux_contact_pair(seeded);
        if (preserved.applied_count != 0u) {
            throw std::runtime_error("inactive pair unexpectedly applied");
        }
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                preserved.body_accumulator.angular[component],
                seeded.body_accumulator.angular[component],
                0.0,
                "inactive pair angular preservation",
                max_error);
            require_close(
                preserved.body_accumulator.linear[component],
                seeded.body_accumulator.linear[component],
                0.0,
                "inactive pair linear preservation",
                max_error);
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeAuxContactPair/1\","
            << "\"ready\":true,"
            << "\"caller\":\"FUN_00766510\","
            << "\"callee\":\"FUN_00758fc0\","
            << "\"record_count\":2,"
            << "\"record_offsets\":[\"0x37d8\",\"0x3858\"],"
            << "\"sequential_accumulator_join_proven\":true,"
            << "\"inactive_preservation_proven\":true,"
            << "\"runtime_scheduling_proven\":false,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}

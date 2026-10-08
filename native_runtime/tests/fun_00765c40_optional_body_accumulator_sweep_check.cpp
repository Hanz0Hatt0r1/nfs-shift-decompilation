#include "shift_fun_00765c40_optional_body_accumulator_sweep.hpp"

#include <iostream>
#include <stdexcept>

namespace {

using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main() {
    try {
        require(kFun00765c40OptionalBodyAccumulatorEntryCount == 4u,
                "FUN_00765c40 optional BODY sweep count drift");
        require(kFun00765c40OptionalBodyAccumulatorCallSite == 0x007664f2u,
                "FUN_00765c40 optional BODY sweep call-site drift");
        require(fun_00765c40_optional_body_accumulator_is_final_residual_stage(),
                "FUN_00765c40 optional BODY sweep ordering drift");

        BodyAccumulatorState initial{};
        initial.angular = {1.0, 2.0, 3.0};
        initial.linear = {4.0, 5.0, 6.0};

        Fun00765c40OptionalBodyAccumulatorSweepInput disabled{};
        disabled.enabled = false;
        const auto skipped =
            execute_fun_00765c40_optional_body_accumulator_sweep(initial, disabled);
        require(!skipped.executed && skipped.applied_entry_count == 0u,
                "disabled FUN_00765c40 optional BODY sweep must not execute");
        require(skipped.body.angular == initial.angular &&
                    skipped.body.linear == initial.linear,
                "disabled FUN_00765c40 optional BODY sweep mutated BODY state");

        Fun00765c40OptionalBodyAccumulatorSweepInput enabled{};
        enabled.enabled = true;
        enabled.entries = {{
            {{{1.0, 0.0, 0.0}}, {{0.0, 1.0, 0.0}}},
            {{{0.0, 1.0, 0.0}}, {{0.0, 0.0, 2.0}}},
            {{{0.0, 0.0, 1.0}}, {{3.0, 0.0, 0.0}}},
            {{{1.0, 1.0, 0.0}}, {{0.0, 0.0, 4.0}}},
        }};

        const auto applied =
            execute_fun_00765c40_optional_body_accumulator_sweep(initial, enabled);
        require(applied.executed && applied.applied_entry_count == 4u,
                "enabled FUN_00765c40 optional BODY sweep did not execute four entries");
        require(applied.body.angular == BodyAccumulatorVector3d{7.0, 1.0, 4.0},
                "FUN_00765c40 optional BODY angular accumulator drift");
        require(applied.body.linear == BodyAccumulatorVector3d{7.0, 6.0, 12.0},
                "FUN_00765c40 optional BODY linear accumulator drift");

        std::cout
            << "{\"format\":\"" << kFun00765c40OptionalBodyAccumulatorSweepFormat << "\","
            << "\"ready\":true,"
            << "\"entry_count\":4,"
            << "\"call_site\":\"0x007664f2\","
            << "\"predicate_internalized\":false,"
            << "\"entry_input_producers_internalized\":false,"
            << "\"body_accumulator_primitive_native\":true,"
            << "\"top_level_provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

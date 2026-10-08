#include "shift_fun_00765c40_contact_body_accumulation.hpp"

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
        require(kFun00765c40ContactArraySlotCount == 12u,
                "FUN_00765c40 contact BODY slot count drift");
        require(kFun00765c40ContactBodyAccumulatorCallSite == 0x00766365u,
                "FUN_00765c40 contact BODY call-site drift");

        BodyAccumulatorState initial{};
        initial.angular = {1.0, 2.0, 3.0};
        initial.linear = {4.0, 5.0, 6.0};

        Fun00765c40ContactBodyAccumulationEntries none{};
        const auto unchanged =
            execute_fun_00765c40_contact_body_accumulation(initial, none);
        require(unchanged.applied_entry_count == 0u,
                "empty contact BODY mask unexpectedly applied entries");
        require(unchanged.body.angular == initial.angular &&
                    unchanged.body.linear == initial.linear,
                "empty contact BODY mask mutated BODY state");

        Fun00765c40ContactBodyAccumulationEntries entries{};
        entries[1].apply = true;
        entries[1].point_or_lever_arm = {1.0, 0.0, 0.0};
        entries[1].contribution = {0.0, 2.0, 0.0};
        entries[7].apply = true;
        entries[7].point_or_lever_arm = {0.0, 1.0, 0.0};
        entries[7].contribution = {0.0, 0.0, 3.0};
        entries[11].apply = true;
        entries[11].point_or_lever_arm = {0.0, 0.0, 1.0};
        entries[11].contribution = {4.0, 0.0, 0.0};

        const auto applied =
            execute_fun_00765c40_contact_body_accumulation(initial, entries);
        require(applied.applied_entry_count == 3u,
                "contact BODY source mask did not preserve selected slot count");
        require(applied.body.angular == BodyAccumulatorVector3d{4.0, 6.0, 5.0},
                "contact BODY angular accumulator drift");
        require(applied.body.linear == BodyAccumulatorVector3d{8.0, 7.0, 9.0},
                "contact BODY linear accumulator drift");

        std::cout
            << "{\"format\":\"" << kFun00765c40ContactBodyAccumulationFormat << "\","
            << "\"ready\":true,"
            << "\"slot_count\":12,"
            << "\"call_site\":\"0x00766365\","
            << "\"per_slot_predicate_internalized\":false,"
            << "\"entry_input_producers_internalized\":false,"
            << "\"body_accumulator_primitive_native\":true,"
            << "\"top_level_provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

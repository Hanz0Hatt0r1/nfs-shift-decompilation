#include "shift_constraint_relation_state_mutation.hpp"

#include <cstdlib>
#include <exception>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

template <typename Fn>
void require_runtime_error(
    Fn&& fn,
    const char* needle,
    const char* label) {

    bool rejected = false;
    try {
        fn();
    } catch (const std::runtime_error& error) {
        rejected =
            std::string(error.what()).find(needle) !=
            std::string::npos;
    }
    if (!rejected) {
        throw std::runtime_error(
            std::string(label) + " was not rejected");
    }
}

shift::runtime::physics::ConstraintSampleEndpointRef
endpoint(std::size_t body) {
    return {body, 0u};
}

}  // namespace

int main() {
    try {
        using namespace shift::runtime::physics;

        PreparedConstraintSampleRelationFrame relations{};
        relations.body_count = 6u;

        PreparedJointConstraintRelation joint_pair{};
        joint_pair.positive = endpoint(1u);
        joint_pair.negative = endpoint(5u);
        PreparedJointConstraintRelation joint_other{};
        joint_other.positive = endpoint(2u);
        joint_other.negative = endpoint(4u);
        relations.joints = {joint_pair, joint_other};

        PreparedHingeConstraintRelation hinge_pair{};
        hinge_pair.positive = endpoint(5u);
        hinge_pair.negative = endpoint(1u);
        PreparedHingeConstraintRelation hinge_other{};
        hinge_other.positive = endpoint(3u);
        hinge_other.negative = endpoint(5u);
        relations.hinges = {hinge_pair, hinge_other};

        PreparedBarConstraintRelation bar_a{};
        bar_a.positive = endpoint(0u);
        bar_a.negative = endpoint(2u);
        PreparedBarConstraintRelation bar_b{};
        bar_b.positive = endpoint(4u);
        bar_b.negative = endpoint(2u);
        PreparedBarConstraintRelation bar_c{};
        bar_c.positive = endpoint(3u);
        bar_c.negative = endpoint(3u);
        relations.bars = {bar_a, bar_b, bar_c};

        PreparedConstraintRelationResetFrame state{};
        state.joint_state_bit0 = {0u, 0u};
        state.hinge_state_bit0 = {0u, 0u};
        state.bar_state_bit0 = {0u, 1u, 0u};

        const auto pair_branch =
            apply_fun_00757d2c_component_relation_state_mutation(
                relations,
                state,
                1u,
                std::nullopt,
                5u);
        if (pair_branch.branch !=
                ConstraintRelationStateMutationBranch::JointHingePair ||
            !pair_branch.component_state_504_set ||
            pair_branch.component_state_540_set ||
            pair_branch.frame.joint_state_bit0 !=
                std::vector<std::uint8_t>({1u, 0u}) ||
            pair_branch.frame.hinge_state_bit0 !=
                std::vector<std::uint8_t>({1u, 0u}) ||
            pair_branch.frame.bar_state_bit0 !=
                state.bar_state_bit0 ||
            pair_branch.matched_joint_relation_count != 1u ||
            pair_branch.matched_hinge_relation_count != 1u ||
            pair_branch.matched_bar_relation_count != 0u) {
            throw std::runtime_error(
                "FUN_00757d2c null-secondary pair branch mismatch");
        }

        const auto bar_branch =
            apply_fun_00757d2c_component_relation_state_mutation(
                relations,
                state,
                1u,
                2u,
                5u);
        if (bar_branch.branch !=
                ConstraintRelationStateMutationBranch::BarEndpoint ||
            !bar_branch.component_state_504_set ||
            !bar_branch.component_state_540_set ||
            bar_branch.frame.joint_state_bit0 !=
                state.joint_state_bit0 ||
            bar_branch.frame.hinge_state_bit0 !=
                state.hinge_state_bit0 ||
            bar_branch.frame.bar_state_bit0 !=
                std::vector<std::uint8_t>({1u, 1u, 0u}) ||
            bar_branch.matched_joint_relation_count != 0u ||
            bar_branch.matched_hinge_relation_count != 0u ||
            bar_branch.matched_bar_relation_count != 2u ||
            bar_branch.newly_set_bar_relation_count != 1u) {
            throw std::runtime_error(
                "FUN_00757d2c non-null-secondary BAR branch mismatch");
        }

        const auto null_rear =
            apply_fun_00757d2c_component_relation_state_mutation(
                relations,
                state,
                1u,
                std::nullopt,
                std::nullopt);
        if (null_rear.frame.joint_state_bit0 !=
                state.joint_state_bit0 ||
            null_rear.frame.hinge_state_bit0 !=
                state.hinge_state_bit0 ||
            null_rear.matched_joint_relation_count != 0u ||
            null_rear.matched_hinge_relation_count != 0u) {
            throw std::runtime_error(
                "null rear-axle pointer should not match relation endpoint");
        }

        ConstraintRelationVehicleComponentMap component_map{};
        component_map.components[0] = {1u, std::nullopt};
        component_map.components[1] = {1u, 2u};
        component_map.components[2] = {3u, std::nullopt};
        component_map.components[3] = {4u, 3u};
        component_map.rear_axle_body_index = 5u;

        const auto slot0 =
            apply_fun_00757d20_component_slot_relation_state_mutation(
                relations,
                state,
                component_map,
                0u);
        if (slot0.frame.joint_state_bit0 !=
                pair_branch.frame.joint_state_bit0 ||
            slot0.frame.hinge_state_bit0 !=
                pair_branch.frame.hinge_state_bit0) {
            throw std::runtime_error(
                "FUN_00757d20 slot 0 did not dispatch pair branch");
        }

        const auto slot1 =
            apply_fun_00757d20_component_slot_relation_state_mutation(
                relations,
                state,
                component_map,
                1u);
        if (slot1.frame.bar_state_bit0 !=
                bar_branch.frame.bar_state_bit0 ||
            slot1.branch !=
                ConstraintRelationStateMutationBranch::BarEndpoint) {
            throw std::runtime_error(
                "FUN_00757d20 slot 1 did not dispatch BAR branch");
        }

        require_runtime_error(
            [&]() {
                (void)apply_fun_00757d20_component_slot_relation_state_mutation(
                    relations,
                    state,
                    component_map,
                    4u);
            },
            "outside 0..3",
            "component slot range");

        require_runtime_error(
            [&]() {
                (void)apply_fun_00757d2c_component_relation_state_mutation(
                    relations,
                    state,
                    1u,
                    6u,
                    5u);
            },
            "component secondary BODY index",
            "invalid secondary BODY");

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeConstraintRelationComponentDispatchCheck/1\",\n"
            << "  \"wrapper_function\": \"FUN_00757d20\",\n"
            << "  \"thunk_address\": \"0x469736\",\n"
            << "  \"source_function\": \"FUN_00757d2c\",\n"
            << "  \"component_base_offset\": 1024,\n"
            << "  \"component_stride\": 2688,\n"
            << "  \"primary_body_offset\": 1056,\n"
            << "  \"secondary_body_offset\": 1060,\n"
            << "  \"component_state_504_offset\": 1284,\n"
            << "  \"component_state_540_offset\": 1344,\n"
            << "  \"rear_axle_vehicle_offset\": 11776,\n"
            << "  \"secondary_nonnull_selects_bar\": true,\n"
            << "  \"secondary_null_selects_joint_hinge\": true,\n"
            << "  \"joint_hinge_pair_uses_primary_and_rear_axle\": true,\n"
            << "  \"null_rear_axle_matches_nothing\": true,\n"
            << "  \"four_slot_wrapper_verified\": true,\n"
            << "  \"scheduler_integrated\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_constraint_relation_component_dispatch_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}

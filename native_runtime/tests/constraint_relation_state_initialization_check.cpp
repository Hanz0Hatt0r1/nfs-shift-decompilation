#include "shift_constraint_relation_state_mutation.hpp"

#include <array>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using shift::runtime::physics::PreparedBarConstraintRelation;
using shift::runtime::physics::PreparedConstraintRelationResetFrame;
using shift::runtime::physics::PreparedConstraintSampleRelationFrame;
using shift::runtime::physics::PreparedHingeConstraintRelation;
using shift::runtime::physics::PreparedJointConstraintRelation;
using shift::runtime::physics::VehicleConstraintBodyIdentityMap;
using shift::runtime::physics::VehicleConstraintRelationInitializationState;
using shift::runtime::physics::
    apply_fun_0076ed60_vehicle_relation_state_initialization;
using shift::runtime::physics::
    vehicle_constraint_setup_mutation_flag_source_offset;
using shift::runtime::physics::kVehicleConstraintSetupConfigComponentBaseOffset;
using shift::runtime::physics::kVehicleConstraintSetupConfigComponentStride;
using shift::runtime::physics::kVehicleConstraintSetupMutationFlagOffset;

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

template <typename Relation>
Relation make_relation(
    std::size_t positive_body_index,
    std::size_t negative_body_index) {

    Relation relation{};
    relation.positive.body_index = positive_body_index;
    relation.negative.body_index = negative_body_index;
    return relation;
}

}  // namespace

int main() {
    try {
        PreparedConstraintSampleRelationFrame relations{};
        relations.body_count = 11u;
        relations.joints = {
            make_relation<PreparedJointConstraintRelation>(0u, 8u),
            make_relation<PreparedJointConstraintRelation>(2u, 8u),
            make_relation<PreparedJointConstraintRelation>(4u, 8u),
        };
        relations.hinges = {
            make_relation<PreparedHingeConstraintRelation>(8u, 0u),
            make_relation<PreparedHingeConstraintRelation>(8u, 2u),
            make_relation<PreparedHingeConstraintRelation>(8u, 4u),
        };
        relations.bars = {
            make_relation<PreparedBarConstraintRelation>(5u, 9u),
            make_relation<PreparedBarConstraintRelation>(10u, 7u),
        };

        PreparedConstraintRelationResetFrame state{};
        state.joint_state_bit0 = {0u, 0u, 0u};
        state.hinge_state_bit0 = {0u, 0u, 0u};
        state.bar_state_bit0 = {0u, 1u};

        VehicleConstraintBodyIdentityMap body_map{};
        body_map.wheel_body_indices = {0u, 2u, 4u, 6u};
        body_map.spindle_body_indices = {1u, 3u, 5u, 7u};
        body_map.rear_axle_body_index = 8u;

        VehicleConstraintRelationInitializationState initialization{};
        initialization.mutation_enabled = {true, false, true, true};
        initialization.spindle_body_present = {false, false, true, true};

        const auto result =
            apply_fun_0076ed60_vehicle_relation_state_initialization(
                relations,
                state,
                body_map,
                initialization);

        require(
            result.dispatched_slot_count == 3u,
            "FUN_0076ed60 dispatched slot count mismatch");
        require(
            result.slot_dispatched ==
                std::array<bool, 4>{true, false, true, true},
            "FUN_0076ed60 dispatched slot mask mismatch");
        require(
            result.dispatched_slot_order[0] == 0u &&
                result.dispatched_slot_order[1] == 2u &&
                result.dispatched_slot_order[2] == 3u,
            "FUN_0076ed60 source-order dispatch mismatch");
        require(
            result.pair_branch_dispatch_count == 1u &&
                result.bar_branch_dispatch_count == 2u,
            "FUN_0076ed60 branch dispatch counts mismatch");

        require(
            result.frame.joint_state_bit0 ==
                std::vector<unsigned char>({1u, 0u, 0u}),
            "FUN_0076ed60 JOINT state mismatch");
        require(
            result.frame.hinge_state_bit0 ==
                std::vector<unsigned char>({1u, 0u, 0u}),
            "FUN_0076ed60 HINGE state mismatch");
        require(
            result.frame.bar_state_bit0 ==
                std::vector<unsigned char>({1u, 1u}),
            "FUN_0076ed60 BAR state mismatch");

        require(
            result.newly_set_joint_relation_count == 1u &&
                result.newly_set_hinge_relation_count == 1u &&
                result.newly_set_bar_relation_count == 1u,
            "FUN_0076ed60 newly-set relation counts mismatch");
        require(
            result.matched_joint_relation_count == 1u &&
                result.matched_hinge_relation_count == 1u &&
                result.matched_bar_relation_count == 2u,
            "FUN_0076ed60 matched relation counts mismatch");

        require(
            kVehicleConstraintSetupConfigComponentBaseOffset == 0x88u &&
                kVehicleConstraintSetupConfigComponentStride == 0xA0u &&
                kVehicleConstraintSetupMutationFlagOffset == 0x98u,
            "FUN_0076ed60 config geometry mismatch");
        require(
            vehicle_constraint_setup_mutation_flag_source_offset(0u) == 0x120u &&
                vehicle_constraint_setup_mutation_flag_source_offset(1u) == 0x1C0u &&
                vehicle_constraint_setup_mutation_flag_source_offset(2u) == 0x260u &&
                vehicle_constraint_setup_mutation_flag_source_offset(3u) == 0x300u,
            "FUN_0076ed60 mutation flag source offsets mismatch");

        VehicleConstraintRelationInitializationState no_triggers{};
        const auto unchanged =
            apply_fun_0076ed60_vehicle_relation_state_initialization(
                relations,
                state,
                body_map,
                no_triggers);
        require(
            unchanged.dispatched_slot_count == 0u &&
                unchanged.frame.joint_state_bit0 == state.joint_state_bit0 &&
                unchanged.frame.hinge_state_bit0 == state.hinge_state_bit0 &&
                unchanged.frame.bar_state_bit0 == state.bar_state_bit0,
            "FUN_0076ed60 disabled setup must preserve relation state");

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeConstraintRelationInitializationCheck/1\",\n"
            << "  \"source_function\": \"FUN_0076ed60\",\n"
            << "  \"mutation_function\": \"FUN_00757d2c\",\n"
            << "  \"component_config_base_offset\": 136,\n"
            << "  \"component_config_stride\": 160,\n"
            << "  \"component_mutation_flag_offset\": 152,\n"
            << "  \"mutation_flag_source_offsets\": [288, 448, 608, 768],\n"
            << "  \"slot_call_order_fl_fr_rl_rr\": true,\n"
            << "  \"disabled_slots_skipped\": true,\n"
            << "  \"initialization_provenance_closed\": true,\n"
            << "  \"fixed_step_scheduler_event\": false,\n"
            << "  \"persistent_runtime_state_integrated\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_constraint_relation_state_initialization_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}

#include "shift_constraint_relation_state_mutation.hpp"

#include <cstdlib>
#include <functional>
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
using shift::runtime::physics::
    dispatch_fun_00757d2c_vehicle_slot_relation_state_mutation;
using shift::runtime::physics::kVehicleConstraintComponentBaseOffset;
using shift::runtime::physics::kVehicleConstraintComponentCount;
using shift::runtime::physics::kVehicleConstraintComponentStride;
using shift::runtime::physics::kVehicleConstraintRearAxleBodyFieldOffset;
using shift::runtime::physics::kVehicleConstraintSpindleBodyFieldOffset;
using shift::runtime::physics::kVehicleConstraintWheelBodyFieldOffset;

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void require_runtime_error(
    const std::function<void()>& fn,
    const std::string& needle,
    const std::string& label) {

    try {
        fn();
    } catch (const std::runtime_error& error) {
        if (std::string(error.what()).find(needle) != std::string::npos) {
            return;
        }
        throw std::runtime_error(
            label + ": unexpected error: " + error.what());
    }
    throw std::runtime_error(label + ": expected runtime_error");
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
            make_relation<PreparedJointConstraintRelation>(8u, 2u),
            make_relation<PreparedJointConstraintRelation>(4u, 8u),
            make_relation<PreparedJointConstraintRelation>(9u, 10u),
        };
        relations.hinges = {
            make_relation<PreparedHingeConstraintRelation>(8u, 0u),
            make_relation<PreparedHingeConstraintRelation>(2u, 8u),
            make_relation<PreparedHingeConstraintRelation>(8u, 6u),
            make_relation<PreparedHingeConstraintRelation>(9u, 10u),
        };
        relations.bars = {
            make_relation<PreparedBarConstraintRelation>(1u, 9u),
            make_relation<PreparedBarConstraintRelation>(10u, 3u),
            make_relation<PreparedBarConstraintRelation>(5u, 7u),
            make_relation<PreparedBarConstraintRelation>(9u, 10u),
        };

        PreparedConstraintRelationResetFrame state{};
        state.joint_state_bit0 = {0u, 0u, 1u, 0u};
        state.hinge_state_bit0 = {0u, 0u, 0u, 0u};
        state.bar_state_bit0 = {0u, 0u, 0u, 1u};

        VehicleConstraintBodyIdentityMap body_map{};
        body_map.wheel_body_indices = {0u, 2u, 4u, 6u};
        body_map.spindle_body_indices = {1u, 3u, 5u, 7u};
        body_map.rear_axle_body_index = 8u;

        const auto front_left =
            dispatch_fun_00757d2c_vehicle_slot_relation_state_mutation(
                relations,
                state,
                body_map,
                0u,
                false);
        require(
            front_left.component_slot == 0u &&
                front_left.component_block_offset == 0x400u &&
                front_left.wheel_body_index == 0u &&
                front_left.spindle_body_index == 1u &&
                front_left.rear_axle_body_index == 8u &&
                !front_left.spindle_body_present,
            "front-left named slot mapping mismatch");
        require(
            front_left.mutation.matched_joint_relation_count == 1u &&
                front_left.mutation.newly_set_joint_relation_count == 1u &&
                front_left.mutation.matched_hinge_relation_count == 1u &&
                front_left.mutation.newly_set_hinge_relation_count == 1u &&
                front_left.mutation.matched_bar_relation_count == 0u,
            "front-left wheel/rear-axle pair dispatch mismatch");

        const auto front_right =
            dispatch_fun_00757d2c_vehicle_slot_relation_state_mutation(
                relations,
                front_left.mutation.frame,
                body_map,
                1u,
                false);
        require(
            front_right.component_slot == 1u &&
                front_right.component_block_offset == 0xE80u &&
                front_right.wheel_body_index == 2u &&
                front_right.spindle_body_index == 3u &&
                front_right.rear_axle_body_index == 8u &&
                !front_right.spindle_body_present,
            "front-right named slot mapping mismatch");
        require(
            front_right.mutation.frame.joint_state_bit0[1] == 1u &&
                front_right.mutation.frame.hinge_state_bit0[1] == 1u,
            "front-right wheel/rear-axle state mismatch");

        const auto rear_left =
            dispatch_fun_00757d2c_vehicle_slot_relation_state_mutation(
                relations,
                front_right.mutation.frame,
                body_map,
                2u,
                true);
        require(
            rear_left.component_slot == 2u &&
                rear_left.component_block_offset == 0x1900u &&
                rear_left.wheel_body_index == 4u &&
                rear_left.spindle_body_index == 5u &&
                rear_left.rear_axle_body_index == 8u &&
                rear_left.spindle_body_present,
            "rear-left named slot mapping mismatch");
        require(
            rear_left.mutation.matched_bar_relation_count == 1u &&
                rear_left.mutation.newly_set_bar_relation_count == 1u &&
                rear_left.mutation.frame.bar_state_bit0[2] == 1u,
            "rear-left spindle BAR dispatch mismatch");

        const auto rear_right =
            dispatch_fun_00757d2c_vehicle_slot_relation_state_mutation(
                relations,
                rear_left.mutation.frame,
                body_map,
                3u,
                true);
        require(
            rear_right.component_slot == 3u &&
                rear_right.component_block_offset == 0x2380u &&
                rear_right.wheel_body_index == 6u &&
                rear_right.spindle_body_index == 7u &&
                rear_right.rear_axle_body_index == 8u &&
                rear_right.spindle_body_present,
            "rear-right named slot mapping mismatch");
        require(
            rear_right.mutation.matched_bar_relation_count == 1u &&
                rear_right.mutation.newly_set_bar_relation_count == 0u &&
                rear_right.mutation.frame.bar_state_bit0[2] == 1u,
            "rear-right repeated set-only BAR dispatch mismatch");

        require(
            rear_right.mutation.frame.joint_state_bit0 ==
                std::vector<unsigned char>({1u, 1u, 1u, 0u}) &&
                rear_right.mutation.frame.hinge_state_bit0 ==
                    std::vector<unsigned char>({1u, 1u, 0u, 0u}) &&
                rear_right.mutation.frame.bar_state_bit0 ==
                    std::vector<unsigned char>({0u, 0u, 1u, 1u}),
            "final dispatched relation-state frame mismatch");

        require_runtime_error(
            [&]() {
                (void)
                    dispatch_fun_00757d2c_vehicle_slot_relation_state_mutation(
                        relations,
                        state,
                        body_map,
                        4u,
                        false);
            },
            "outside recovered 0..3 domain",
            "out-of-range component slot");

        require_runtime_error(
            [&]() {
                auto bad_map = body_map;
                bad_map.spindle_body_indices[3] = relations.body_count;
                (void)
                    dispatch_fun_00757d2c_vehicle_slot_relation_state_mutation(
                        relations,
                        state,
                        bad_map,
                        0u,
                        false);
            },
            "BODY index is outside relation domain",
            "out-of-range named BODY identity");

        require(kVehicleConstraintComponentCount == 4u, "component count mismatch");
        require(
            kVehicleConstraintComponentBaseOffset == 0x400u &&
                kVehicleConstraintComponentStride == 0xA80u,
            "component address geometry mismatch");
        require(
            kVehicleConstraintWheelBodyFieldOffset == 0x420u &&
                kVehicleConstraintSpindleBodyFieldOffset == 0x424u &&
                kVehicleConstraintRearAxleBodyFieldOffset == 0x2E00u,
            "named BODY field offsets mismatch");

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeConstraintRelationStateDispatchCheck/1\",\n"
            << "  \"source_function\": \"FUN_00757d2c\",\n"
            << "  \"component_slot_count\": 4,\n"
            << "  \"component_base_offset\": 1024,\n"
            << "  \"component_stride\": 2688,\n"
            << "  \"wheel_body_field_offset\": 1056,\n"
            << "  \"spindle_body_field_offset\": 1060,\n"
            << "  \"rear_axle_body_field_offset\": 11776,\n"
            << "  \"slot_names_fl_fr_rl_rr\": true,\n"
            << "  \"pair_branch_uses_wheel_rear_axle\": true,\n"
            << "  \"bar_branch_uses_spindle\": true,\n"
            << "  \"branch_from_spindle_presence\": true,\n"
            << "  \"set_only_preserved_through_dispatch\": true,\n"
            << "  \"scheduler_integrated\": false,\n"
            << "  \"event_timing_assigned\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_constraint_relation_state_dispatch_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}

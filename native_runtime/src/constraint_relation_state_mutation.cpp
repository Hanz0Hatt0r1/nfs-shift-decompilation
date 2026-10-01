#include "shift_constraint_relation_state_mutation.hpp"

#include <cstdint>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

void validate_state_cardinality(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& state) {

    if (state.joint_state_bit0.size() != relations.joints.size() ||
        state.hinge_state_bit0.size() != relations.hinges.size() ||
        state.bar_state_bit0.size() != relations.bars.size()) {
        throw std::runtime_error(
            "constraint relation state mutation cardinality mismatch");
    }
}

void validate_body_index(
    const PreparedConstraintSampleRelationFrame& relations,
    std::size_t body_index,
    const char* label) {

    if (relations.body_count == 0u ||
        body_index >= relations.body_count) {
        throw std::runtime_error(
            std::string(label) +
            " BODY index is outside relation domain");
    }
}

void validate_vehicle_body_identity_map(
    const PreparedConstraintSampleRelationFrame& relations,
    const VehicleConstraintBodyIdentityMap& body_map) {

    validate_body_index(
        relations,
        body_map.rear_axle_body_index,
        "rear axle");

    for (std::size_t slot = 0;
         slot < kVehicleConstraintComponentCount;
         ++slot) {
        validate_body_index(
            relations,
            body_map.wheel_body_indices[slot],
            "wheel");
        validate_body_index(
            relations,
            body_map.spindle_body_indices[slot],
            "spindle");
    }
}

template <typename Relation>
void validate_relation_endpoints(
    const PreparedConstraintSampleRelationFrame& relations,
    const Relation& relation,
    const char* label) {

    if (relation.positive.body_index >= relations.body_count ||
        relation.negative.body_index >= relations.body_count) {
        throw std::runtime_error(
            std::string(label) +
            " relation endpoint BODY index is outside relation domain");
    }
}

void validate_relation_frame(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& state) {

    if (relations.body_count == 0u) {
        throw std::runtime_error(
            "constraint relation state mutation requires BODY domain");
    }
    validate_state_cardinality(relations, state);

    for (const auto& relation : relations.joints) {
        validate_relation_endpoints(
            relations, relation, "JOINT");
    }
    for (const auto& relation : relations.hinges) {
        validate_relation_endpoints(
            relations, relation, "HINGE");
    }
    for (const auto& relation : relations.bars) {
        validate_relation_endpoints(
            relations, relation, "BAR");
    }

    auto validate_bits = [](const auto& bits, const char* label) {
        for (const std::uint8_t bit : bits) {
            if (bit > 1u) {
                throw std::runtime_error(
                    std::string(label) +
                    " relation state bit0 must be 0 or 1");
            }
        }
    };
    validate_bits(state.joint_state_bit0, "JOINT");
    validate_bits(state.hinge_state_bit0, "HINGE");
    validate_bits(state.bar_state_bit0, "BAR");
}

template <typename Relation>
bool unordered_pair_matches(
    const Relation& relation,
    std::size_t first_body_index,
    std::size_t second_body_index) {

    const std::size_t positive =
        relation.positive.body_index;
    const std::size_t negative =
        relation.negative.body_index;
    return
        (positive == first_body_index &&
         negative == second_body_index) ||
        (positive == second_body_index &&
         negative == first_body_index);
}

void set_state_bit(
    std::uint8_t& bit,
    std::size_t& matched_count,
    std::size_t& newly_set_count) {

    ++matched_count;
    if (bit == 0u) {
        bit = 1u;
        ++newly_set_count;
    }
}

}  // namespace

ConstraintRelationStateMutationResult
apply_fun_00757d2c_pair_relation_state_mutation(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& state,
    std::size_t first_body_index,
    std::size_t second_body_index) {

    validate_relation_frame(relations, state);
    validate_body_index(
        relations, first_body_index, "first");
    validate_body_index(
        relations, second_body_index, "second");

    ConstraintRelationStateMutationResult result{};
    result.frame = state;

    for (std::size_t index = 0;
         index < relations.joints.size();
         ++index) {
        if (unordered_pair_matches(
                relations.joints[index],
                first_body_index,
                second_body_index)) {
            set_state_bit(
                result.frame.joint_state_bit0[index],
                result.matched_joint_relation_count,
                result.newly_set_joint_relation_count);
        }
    }

    for (std::size_t index = 0;
         index < relations.hinges.size();
         ++index) {
        if (unordered_pair_matches(
                relations.hinges[index],
                first_body_index,
                second_body_index)) {
            set_state_bit(
                result.frame.hinge_state_bit0[index],
                result.matched_hinge_relation_count,
                result.newly_set_hinge_relation_count);
        }
    }

    return result;
}

ConstraintRelationStateMutationResult
apply_fun_00757d2c_bar_endpoint_state_mutation(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& state,
    std::size_t body_index) {

    validate_relation_frame(relations, state);
    validate_body_index(
        relations, body_index, "BAR endpoint");

    ConstraintRelationStateMutationResult result{};
    result.frame = state;

    for (std::size_t index = 0;
         index < relations.bars.size();
         ++index) {
        const auto& relation =
            relations.bars[index];
        if (relation.positive.body_index == body_index ||
            relation.negative.body_index == body_index) {
            set_state_bit(
                result.frame.bar_state_bit0[index],
                result.matched_bar_relation_count,
                result.newly_set_bar_relation_count);
        }
    }

    return result;
}

ConstraintRelationStateDispatchResult
dispatch_fun_00757d2c_vehicle_slot_relation_state_mutation(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& state,
    const VehicleConstraintBodyIdentityMap& body_map,
    std::size_t component_slot,
    bool spindle_body_present) {

    validate_relation_frame(relations, state);
    validate_vehicle_body_identity_map(relations, body_map);

    if (component_slot >= kVehicleConstraintComponentCount) {
        throw std::runtime_error(
            "FUN_00757d2c component slot is outside recovered 0..3 domain");
    }

    ConstraintRelationStateDispatchResult result{};
    result.component_slot = component_slot;
    result.component_block_offset =
        kVehicleConstraintComponentBaseOffset +
        component_slot * kVehicleConstraintComponentStride;
    result.wheel_body_index =
        body_map.wheel_body_indices[component_slot];
    result.spindle_body_index =
        body_map.spindle_body_indices[component_slot];
    result.rear_axle_body_index =
        body_map.rear_axle_body_index;
    result.spindle_body_present =
        spindle_body_present;

    if (spindle_body_present) {
        result.mutation =
            apply_fun_00757d2c_bar_endpoint_state_mutation(
                relations,
                state,
                result.spindle_body_index);
    } else {
        result.mutation =
            apply_fun_00757d2c_pair_relation_state_mutation(
                relations,
                state,
                result.wheel_body_index,
                result.rear_axle_body_index);
    }

    return result;
}

}  // namespace shift::runtime::physics

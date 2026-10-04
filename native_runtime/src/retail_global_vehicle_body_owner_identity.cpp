#include "shift_retail_global_vehicle_body_owner_identity.hpp"

namespace shift::runtime::physics {
namespace {

constexpr std::uint32_t kRetailGlobalVehicleAddress = 0x00c13700u;
constexpr std::uint32_t kRetailBodyOwnerPointerFieldOffset = 0x339cu;
constexpr std::uint32_t kRetailBmwChassisBodyIndex = 0u;

GlobalVehicleBodyOwnerIdentityHandoff retail_handoff() {
    GlobalVehicleBodyOwnerIdentityHandoff handoff{};
    handoff.outer_receiver_to_body_owner_continuity_proven = true;
    handoff.vehicle_body_selection_ready = true;
    handoff.selected_body_index_present = true;
    handoff.selected_body_index = kRetailBmwChassisBodyIndex;
    handoff.phase698_positive_selection_admissible = true;
    handoff.phase700_runtime_handoff_admissible = true;
    handoff.phase703_update_child_equality_gate_required = false;
    handoff.phase703_gate_rewrite_ready = true;
    return handoff;
}

}  // namespace

RetailGlobalVehicleBodyOwnerIdentity
retail_global_vehicle_body_owner_identity() {
    RetailGlobalVehicleBodyOwnerIdentity out{};
    out.global_vehicle_address = kRetailGlobalVehicleAddress;
    out.body_owner_pointer_field_offset = kRetailBodyOwnerPointerFieldOffset;
    out.body_array_owner_is_global_vehicle_base = false;
    out.body_array_owner_pointer_loaded_from_global_vehicle_base = true;
    out.handoff = retail_handoff();
    return out;
}

BmwVehicleWorldMatrixRuntimeHandoffResult
build_retail_bmw_vehicle_world_matrix_runtime_handoff(
    const shift::runtime::NativeRuntimeState& runtime,
    const ProvenBmwVhfBindFrame& vhf_bind,
    const ProvenBmwBody0BindFrame& body0_bind) {
    const auto identity = retail_global_vehicle_body_owner_identity();
    return build_bmw_vehicle_world_matrix_runtime_handoff(
        runtime,
        identity.handoff,
        vhf_bind,
        body0_bind);
}

PersistentBmwVehicleWorldTransformSnapshot
commit_retail_bmw_vehicle_world_transform(
    PersistentBmwVehicleWorldTransformState& state,
    const shift::runtime::NativeRuntimeState& runtime,
    const ProvenBmwVhfBindFrame& vhf_bind,
    const ProvenBmwBody0BindFrame& body0_bind) {
    const auto identity = retail_global_vehicle_body_owner_identity();
    return commit_bmw_vehicle_world_transform(
        state,
        runtime,
        identity.handoff,
        vhf_bind,
        body0_bind);
}

}  // namespace shift::runtime::physics

#pragma once

#include "shift_fun_00765c40_selected_bmw_world_position.hpp"

#include <cstddef>

namespace shift::runtime::physics {

inline constexpr const char* kFun00766510SelectedBmwApplicationPointFormat =
    "SHIFT.Fun00766510SelectedBMWApplicationPoint/1";
inline constexpr std::size_t kFun00765c40RotatedScratchOffset = 0x38f0u;

// PC retail FUN_00765c40 writes BODY0.basis * local_sample to HDVehicle+0x38f0
// before adding BODY0 origin for the collision query. The following FUN_00766510
// anchor reuses that same f64 vec3 as the second argument to FUN_007baa70.
// Phase727 already exposes the exact scratch as body_rotated_local, so selected
// BMW ownership is an alias of an existing native result rather than a second
// transform or a new physical interpretation.
inline const BodyAccumulatorVector3d&
fun_00766510_selected_bmw_primary_application_point(
    const Fun00765c40SelectedBmwWorldPositionResult& fun_00765c40_result) {
    return fun_00765c40_result.world_transform.body_rotated_local;
}

}  // namespace shift::runtime::physics

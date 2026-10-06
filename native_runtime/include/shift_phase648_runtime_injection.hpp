#pragma once

// The runtime source includes runtime_state.hpp later.  Load it before defining
// the narrow call-site macro so the macro cannot rewrite the method declaration.
#include "../src/runtime_state.hpp"

#include <cstddef>
#include <utility>

#include "shift_bmw_body0_bind_frame_runtime_admission.hpp"
#include "shift_bmw_persistent_world_transform_runtime_wiring.hpp"
#include "shift_phase648_runtime_vehicle_vulkan_wiring.hpp"
#include "shift_phase715_persistent_vehicle_runtime_wiring.hpp"

// native_runtime/src/shift_runtime.cpp has one executable fixed_step(intent)
// member call. Because this function-like macro expands after `native_state.`,
// the original member invocation must remain the first replacement token. The
// comma expression in its argument admits an optional positive BODY0 bind-frame
// packet before argument evaluation completes and therefore before fixed_step is
// entered. Absence remains inert; an invalid configured packet fails closed
// before the tick.
//
// After the physics tick, S4 consumes that admitted static BODY0 bind proof plus
// the current persistent BODY0 snapshot.  It resolves the already-prepared BMW
// vehicle child SVWT as the static VHF bind, commits a freshness-bound Phase 706
// world transform, and publishes it to Phase 715.  Phase 715 therefore receives
// the new commit in the same fixed-step continuation before any Vulkan vehicle
// upload.  The Phase 648 explicit transform-script regression hook stays last;
// dual producer selection remains fail-closed in Phase 715.
#define fixed_step(phase648_intent_) \
    fixed_step(( \
        ::shift::runtime::physics::admit_bmw_body0_bind_frame_from_environment_once(), \
        (phase648_intent_))); \
    ::shift::runtime::physics::commit_and_publish_admitted_bmw_world_transform_after_fixed_step( \
        native_state, args.scene_set, scene_set_mode, material_geometry.size()); \
    ::shift::runtime::render::phase715_after_fixed_step( \
        runtime, material_geometry, args.scene_set, scene_set_mode, \
        native_state, simulation_steps); \
    ::shift::runtime::render::phase648_after_fixed_step( \
        runtime, material_geometry, args.scene_set, scene_set_mode, \
        simulation_steps, frame_limit)

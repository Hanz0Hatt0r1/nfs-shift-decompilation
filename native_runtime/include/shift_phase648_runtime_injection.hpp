#pragma once

// The runtime source includes runtime_state.hpp later.  Load it before defining
// the narrow call-site macro so the macro cannot rewrite the method declaration.
#include "../src/runtime_state.hpp"

#include <cstddef>
#include <utility>

#include "shift_phase648_runtime_vehicle_vulkan_wiring.hpp"
#include "shift_phase715_persistent_vehicle_runtime_wiring.hpp"

// native_runtime/src/shift_runtime.cpp has one executable fixed_step(intent)
// call. Phase 715 first gives an already-published Phase 706 persistent state the
// production-facing renderer sink. If no persistent state was published, it is
// inert and the established Phase 648 explicit transform-script regression hook
// remains unchanged. Phase 715 runs first so dual producer selection fails before
// the Phase 648 script can mutate Vulkan memory.
#define fixed_step(phase648_intent_) \
    fixed_step(phase648_intent_); \
    ::shift::runtime::render::phase715_after_fixed_step( \
        runtime, material_geometry, args.scene_set, scene_set_mode, \
        native_state, simulation_steps); \
    ::shift::runtime::render::phase648_after_fixed_step( \
        runtime, material_geometry, args.scene_set, scene_set_mode, \
        simulation_steps, frame_limit)

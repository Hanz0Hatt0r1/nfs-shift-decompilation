#pragma once

// The runtime source includes runtime_state.hpp later.  Load it before defining
// the narrow call-site macro so the macro cannot rewrite the method declaration.
#include "../src/runtime_state.hpp"

#include <cstddef>
#include <utility>

#include "shift_phase648_runtime_vehicle_vulkan_wiring.hpp"

// native_runtime/src/shift_runtime.cpp has one executable fixed_step(intent)
// call.  Phase 648 attaches the optional renderer upload immediately after that
// existing shell step.  With no explicit transform-script environment variable,
// phase648_after_fixed_step() returns without changing the ordinary runtime path.
#define fixed_step(phase648_intent_) \
    fixed_step(phase648_intent_); \
    ::shift::runtime::render::phase648_after_fixed_step( \
        runtime, material_geometry, args.scene_set, scene_set_mode, \
        simulation_steps, frame_limit)

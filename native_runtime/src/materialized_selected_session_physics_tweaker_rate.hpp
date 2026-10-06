#pragma once

#include "selected_session_physics_tweaker_rate_handoff.hpp"

namespace shift::runtime {

// Generated from the exact PC PHYSICSBOOTFLOW.bff only after archive identity,
// entry metadata, decoded SHA-256 and unique PhysicsTweaker `tick rate` validation.
inline constexpr SelectedSessionPhysicsTweakerRateHandoff
    kMaterializedSelectedSessionPhysicsTweakerRateHandoff{
        "SHIFT.SelectedSessionPhysicsTweakerRate/1",
        true,
        "selected-session-physics-tweaker-rate-ready",
        "PHYSICSBOOTFLOW.bff",
        "f4205984343987d7879fcd65f6b2527848a6fd16e9830d6ccca70b7e5db4254a",
        49u,
        "vehicles/physics/physicstweaker.xml",
        2u,
        2452u,
        21762u,
        "6cdd05f0512d367c8ce240cb13dd22fe10fb3e21da95185ea8f79e1ca67ca62f",
        "exact-retail-bff",
        true,
        true,
        "tick rate",
        180u,
        "DAT_00c130d2",
        "0x388",
        true,
        true,
        true,
        false,
        false,
        false,
        false,
        false,
    };

static_assert(kMaterializedSelectedSessionPhysicsTweakerRateHandoff.rate_hz == 180u);
static_assert(kMaterializedSelectedSessionPhysicsTweakerRateHandoff.ready);
static_assert(kMaterializedSelectedSessionPhysicsTweakerRateHandoff.loaded_inner_physics_rate_admitted);
static_assert(!kMaterializedSelectedSessionPhysicsTweakerRateHandoff.retail_inner_substep_execution_admitted);

}  // namespace shift::runtime

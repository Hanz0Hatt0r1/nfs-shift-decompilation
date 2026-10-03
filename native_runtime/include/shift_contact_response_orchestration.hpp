#pragma once

#include "shift_aux_contact_response.hpp"
#include "shift_wheel_query_response_join.hpp"

#include <array>
#include <optional>

namespace shift::runtime::physics {

inline constexpr const char* kNativeContactResponseOrchestrationFormat =
    "SHIFT.NativeContactResponseOrchestration/1";
inline constexpr const char* kContactResponseOrchestrationFunction = "FUN_00766510";

struct ContactResponseOrchestrationInput {
    WheelQueryResponseJoinInput query_response{};
    BodyPointTransformState body_transform{};
    ConstraintRefreshVector3d aux_reference_point{};
    std::array<AuxContactRecord, kAuxContactRecordCount> aux_records{};

    // The source-visible primary FUN_007551e0 response is applied before the
    // two FUN_00758fc0 auxiliary records, but its exact transform/application
    // contract is not yet frozen.  Callers must therefore supply the proven
    // BODY accumulator state *after* that application.  Missing state is an
    // unresolved producer and must fail closed; zero is never synthesized.
    std::optional<BodyAccumulatorState> body_accumulator_after_primary_application{};
};

struct ContactResponseOrchestrationResult {
    WheelQueryResponseJoinResult query_response{};
    BodyAccumulatorState body_accumulator_at_primary_barrier{};
    AuxContactPairResult aux_pair{};
    BodyAccumulatorState body_accumulator{};
};

ContactResponseOrchestrationResult execute_fun_00766510_partial_contact_chain(
    const ContactResponseOrchestrationInput& input);

}  // namespace shift::runtime::physics

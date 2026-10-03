#include "shift_contact_response_orchestration.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

template <typename Range>
void require_finite(const Range& values, const char* label) {
    for (const auto value : values) {
        if (!std::isfinite(static_cast<double>(value))) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite value");
        }
    }
}

void require_finite_accumulator(
    const BodyAccumulatorState& state,
    const char* label) {
    require_finite(state.angular, label);
    require_finite(state.linear, label);
}

}  // namespace

ContactResponseOrchestrationResult execute_fun_00766510_partial_contact_chain(
    const ContactResponseOrchestrationInput& input) {

    ContactResponseOrchestrationResult result{};

    // This is the already-proven FUN_00765c40 -> FUN_00766510 response stage.
    // It deliberately stops before the unresolved primary response application.
    result.query_response =
        execute_fun_00765c40_to_00766510_response_join(input.query_response);

    if (!input.body_accumulator_after_primary_application.has_value()) {
        throw std::invalid_argument(
            "FUN_00766510 primary response application state is unresolved");
    }
    result.body_accumulator_at_primary_barrier =
        *input.body_accumulator_after_primary_application;
    require_finite_accumulator(
        result.body_accumulator_at_primary_barrier,
        "FUN_00766510 post-primary BODY accumulator");

    // The same BODY +0xd4 frame used by the response-input transform is reused
    // by the two source-visible auxiliary records.  Do not accept a second,
    // independently supplied frame that could describe a different BODY domain.
    AuxContactPairInput aux{};
    aux.body_frame = input.query_response.body_frame;
    aux.body_transform = input.body_transform;
    aux.body_accumulator = result.body_accumulator_at_primary_barrier;
    aux.reference_point = input.aux_reference_point;
    aux.records = input.aux_records;

    result.aux_pair = execute_fun_00766510_aux_contact_pair(aux);
    result.body_accumulator = result.aux_pair.body_accumulator;
    return result;
}

}  // namespace shift::runtime::physics

#pragma once

#include "shift_fun_00765c40_collision_output_validation.hpp"
#include "shift_fun_00765c40_load_terms.hpp"
#include "shift_fun_00765c40_query_input_boundary.hpp"
#include "shift_fun_00765c40_residual_producer_handoff.hpp"
#include "shift_fun_00765c40_selected_bmw_query_fallback.hpp"

#include <optional>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40ExternalPassResultFormat =
    "SHIFT.Fun00765c40ExternalPassResult/5";
inline constexpr const char* kFun00765c40HistoricalCollisionOutputResultFormat =
    "SHIFT.Fun00765c40ExternalPassResult/4";
inline constexpr const char* kFun00765c40ExternalPassInputFormat =
    "SHIFT.Fun00765c40ExternalPassInput/2";

struct Fun00765c40ExternalPassInput {
    std::optional<CollisionQueryVector3d> world_position{};
    std::optional<std::uint64_t> cached_handle{};

    std::optional<double> selected_bmw_miss_fallback() const {
        if (!world_position.has_value()) {
            return std::nullopt;
        }
        return selected_bmw_m3_e36_fun_00765c40_query_fallback();
    }

    std::optional<Fun00765c40QueryInputBoundary> selected_bmw_query_input() const {
        if (!world_position.has_value()) {
            return std::nullopt;
        }
        Fun00765c40QueryInputBoundary query{};
        query.world_position = *world_position;
        query.cached_handle = cached_handle;
        query.miss_fallback = selected_bmw_m3_e36_fun_00765c40_query_fallback();
        validate_fun_00765c40_query_input_boundary(query);
        return query;
    }
};

struct Fun00765c40ExternalPassResult {
    // Historical /1..../4 prefix. Keep field order stable so existing aggregate
    // providers remain source-compatible when the /5 witness is omitted.
    Fun00765c40LoadTerms load_terms{};
    Fun00765c40QueryInputBoundary query_input{};
    std::optional<std::uint64_t> returned_cache_handle{};
    std::optional<CollisionQueryOutput> query_output{};

    // /5 appends a non-authoritative pure-data witness for the residual producer
    // values grouped by SHIFT.Fun00765c40ResidualProducerHandoff/1. Absence is
    // valid: selected providers are not required to synthesize unresolved
    // producer formulas. Presence does not make these values native-owned.
    std::optional<Fun00765c40ResidualProducerHandoff> residual_producer_handoff{};
};

inline void validate_fun_00765c40_external_pass_result(
    const Fun00765c40ExternalPassInput& input,
    const Fun00765c40ExternalPassResult& result) {
    validate_fun_00765c40_load_terms(result.load_terms);
    validate_fun_00765c40_query_input_boundary(result.query_input);

    const auto native_selected_query = input.selected_bmw_query_input();
    if (native_selected_query.has_value() &&
        (result.query_input.world_position != native_selected_query->world_position ||
         result.query_input.cached_handle != native_selected_query->cached_handle ||
         result.query_input.miss_fallback != native_selected_query->miss_fallback)) {
        throw std::invalid_argument(
            "FUN_00765c40 residual provider changed native-owned selected query input");
    }

    // Preserve the source-visible provenance guards individually as well as the
    // aggregate native query-object comparison. Older phase gates pin these
    // explicit ownership checks, and their distinct diagnostics remain useful.
    if (result.query_input.cached_handle != input.cached_handle) {
        throw std::invalid_argument(
            "FUN_00765c40 residual provider did not consume native-owned cached handle");
    }
    if (input.world_position.has_value() &&
        result.query_input.world_position != *input.world_position) {
        throw std::invalid_argument(
            "FUN_00765c40 residual provider did not consume native-owned selected BMW world position");
    }
    const auto selected_fallback = input.selected_bmw_miss_fallback();
    if (selected_fallback.has_value() &&
        result.query_input.miss_fallback != *selected_fallback) {
        throw std::invalid_argument(
            "FUN_00765c40 residual provider did not consume native-owned selected BMW +0x38e8 fallback");
    }

    if (input.world_position.has_value() && !result.query_output.has_value()) {
        throw std::invalid_argument(
            "FUN_00765c40 selected BMW provider hid FUN_007b0710 collision output");
    }
    if (result.query_output.has_value()) {
        validate_fun_00765c40_collision_output_handoff(
            result.query_input,
            *result.query_output);
        if (result.returned_cache_handle != result.query_output->returned_handle) {
            throw std::invalid_argument(
                "FUN_00765c40 returned cache handle disagrees with FUN_007b0710 output");
        }
    }

    // The /5 residual producer handoff is intentionally opaque here. Exact-width
    // payload validation belongs to the individual stage contracts. Merely
    // returning this witness cannot promote producer arithmetic to native-owned.
}

inline Fun00765c40QueryInputBoundary
materialize_fun_00765c40_session_query_snapshot(
    const Fun00765c40ExternalPassInput& input,
    const Fun00765c40ExternalPassResult& result) {
    validate_fun_00765c40_external_pass_result(input, result);
    const auto native_selected_query = input.selected_bmw_query_input();
    if (native_selected_query.has_value()) {
        return *native_selected_query;
    }
    return result.query_input;
}

}  // namespace shift::runtime::physics

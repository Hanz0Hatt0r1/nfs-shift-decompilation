#pragma once

#include "shift_fun_00765c40_load_terms.hpp"
#include "shift_fun_00765c40_query_input_boundary.hpp"
#include "shift_fun_00765c40_selected_bmw_query_fallback.hpp"

#include <cmath>
#include <optional>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40ExternalPassResultFormat =
    "SHIFT.Fun00765c40ExternalPassResult/4";
inline constexpr const char* kFun00765c40ExternalPassInputFormat =
    "SHIFT.Fun00765c40ExternalPassInput/2";

// Native-owned inputs supplied before the residual FUN_00765c40 pass executes.
// cached_handle is always session-owned. world_position is present only on the
// selected BMW path closed by Phase739. Its presence is also the selected-session
// identity tag for Phase741: selected_bmw_miss_fallback() then exposes the exact
// source-backed FUN_00756bb0 setup value derived from FRONTWING.FWMaxHeight.
// Generic historical fixtures leave world_position absent and keep their former
// compatibility fallback in the audit witness rather than masquerading as BMW.
struct Fun00765c40ExternalPassInput {
    std::optional<CollisionQueryVector3d> world_position{};
    std::optional<std::uint64_t> cached_handle{};

    std::optional<double> selected_bmw_miss_fallback() const {
        if (!world_position.has_value()) {
            return std::nullopt;
        }
        return selected_bmw_m3_e36_fun_00765c40_query_fallback();
    }
};

// Residual external pass result. Phase742 makes the already-native
// FUN_007b0710 output explicit instead of letting the complete pass hide it.
// returned_cache_handle is retained as the source-visible HDVehicle+0x38dc write
// witness and must equal query_output.returned_handle.
struct Fun00765c40ExternalPassResult {
    Fun00765c40LoadTerms load_terms{};
    Fun00765c40QueryInputBoundary query_input{};
    CollisionQueryOutput query_output{};
    std::optional<std::uint64_t> returned_cache_handle{};
};

inline void validate_fun_00765c40_collision_output_handoff(
    const Fun00765c40QueryInputBoundary& query_input,
    const CollisionQueryOutput& output) {
    const auto expected = build_fun_00765c40_query_record(query_input);

    if (output.query_record.query_position != expected.query_position ||
        output.query_record.y_tolerance != expected.y_tolerance ||
        output.query_record.max_aux != expected.max_aux ||
        output.query_record.cache_enabled != expected.cache_enabled) {
        throw std::invalid_argument(
            "FUN_00765c40 collision output does not belong to the typed query input");
    }
    for (double value : output.normal) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "FUN_00765c40 collision output normal must be finite");
        }
    }

    if (output.hit) {
        if (!output.contact_height.has_value() ||
            !output.returned_handle.has_value() ||
            !output.query_record.output_height.has_value() ||
            !output.query_record.cache_handle.has_value()) {
            throw std::invalid_argument(
                "FUN_00765c40 hit output is incomplete");
        }
        if (!std::isfinite(*output.contact_height) ||
            *output.query_record.output_height != *output.contact_height ||
            *output.query_record.cache_handle != *output.returned_handle) {
            throw std::invalid_argument(
                "FUN_00765c40 hit output fields disagree");
        }
    } else {
        if (output.contact_height.has_value() ||
            output.returned_handle.has_value() ||
            output.query_record.output_height.has_value() ||
            output.query_record.cache_handle != expected.cache_handle) {
            throw std::invalid_argument(
                "FUN_00765c40 miss output fields disagree");
        }
    }

    const bool expected_reuse =
        output.hit && query_input.cached_handle.has_value() &&
        output.returned_handle.has_value() &&
        *query_input.cached_handle == *output.returned_handle;
    if (output.reused_cache != expected_reuse) {
        throw std::invalid_argument(
            "FUN_00765c40 collision output cache-reuse flag disagrees with query state");
    }
}

inline void validate_fun_00765c40_external_pass_result(
    const Fun00765c40ExternalPassInput& input,
    const Fun00765c40ExternalPassResult& result) {
    validate_fun_00765c40_load_terms(result.load_terms);
    validate_fun_00765c40_query_input_boundary(result.query_input);

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

    validate_fun_00765c40_collision_output_handoff(
        result.query_input,
        result.query_output);
    if (result.returned_cache_handle != result.query_output.returned_handle) {
        throw std::invalid_argument(
            "FUN_00765c40 returned cache handle disagrees with FUN_007b0710 output");
    }
}

}  // namespace shift::runtime::physics

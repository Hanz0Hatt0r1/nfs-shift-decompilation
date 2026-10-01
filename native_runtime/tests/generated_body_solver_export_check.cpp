#include "shift_generated_body_solver_export.hpp"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void require_close(
    const std::vector<double>& actual,
    const std::vector<double>& expected,
    double tolerance,
    const char* label,
    double& observed_max) {

    if (actual.size() != expected.size()) {
        throw std::runtime_error(
            std::string(label) + " cardinality mismatch");
    }
    for (std::size_t index = 0;
         index < actual.size();
         ++index) {
        const double error =
            std::abs(actual[index] - expected[index]);
        observed_max =
            std::max(observed_max, error);
        if (error > tolerance) {
            throw std::runtime_error(
                std::string(label) +
                " mismatch at index " +
                std::to_string(index));
        }
    }
}

shift::runtime::physics::GeneratedBodySolverExportInput
fixture() {
    using namespace shift::runtime::physics;

    GeneratedBodySolverExportInput input{};
    input.body_index = 0u;
    input.constraints.scalar_count = 6u;
    input.constraints.body_position = {
        1.0, 2.0, 3.0
    };
    input.constraints.preprojection.body_correction = {
        0.0, 0.0, 0.0
    };
    input.constraints.preprojection.body_axis = {
        0.25, 0.5, 0.75
    };
    input.constraints.preprojection.angular_state = {
        0.125, 0.25, 0.5
    };
    input.constraints.preprojection.linear_state = {
        0.5, 0.75, 1.0
    };
    input.constraints.preprojection.inverse_scalar = 1.0;
    input.constraints.preprojection.body_frame = {
        1.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f,
        0.0f, 0.0f, 1.0f,
    };
    input.constraints.body_tensor = {{
        {{1.0, 0.0, 0.0}},
        {{0.0, 1.0, 0.0}},
        {{0.0, 0.0, 1.0}},
    }};
    input.constraints.scales.linear_scale = 2.0;
    input.constraints.scales.quadratic_scale = 3.0;

    input.constraints.joints.push_back({
        {1.5, 2.5, 3.5},
        0u,
        0u,
    });
    input.constraints.hinges.push_back({
        {1.0, 2.0, 3.0},
        {4.0, 5.0, 6.0},
        {1.0, 2.0, 3.0},
        {0.5, 1.0, 1.5},
        3u,
        0u,
    });
    input.constraints.bars.push_back({
        {2.0, 1.0, 3.0},
        {1.0, 2.0, 1.0},
        0.5,
        5u,
        0u,
    });

    input.row_indices =
        canonical_builtin_body_row_indices(6u);
    input.matrix_double_count = 36u;
    input.provider_present = false;
    return input;
}

}  // namespace

int main() {
    try {
        using namespace shift::runtime::physics;
        double max_absolute_error = 0.0;

        const auto result =
            generate_and_export_fun_007bc680_body(
                fixture());

        const std::vector<double> expected_vector = {
            7.125,
            15.0,
            20.3125,
            9.125,
            20.75,
            52.5,
        };
        const std::vector<double> expected_matrix = {
            19.5, 0.0, 0.0, 0.0, 0.0, 0.0,
            -3.75, 15.5, 0.0, 0.0, 0.0, 0.0,
            -5.25, -8.75, 9.5, 0.0, 0.0, 0.0,
            -0.5, 1.0, -0.5, 14.0, 0.0, 0.0,
            2.5, -5.0, 2.5, 32.0, 77.0, 0.0,
            -3.0, 24.0, -13.0, 6.0, 3.0, 41.0,
        };

        require_close(
            result.assembly.solver_vector,
            expected_vector,
            1e-12,
            "generated BODY local vector",
            max_absolute_error);
        require_close(
            result.sparse_storage.matrix_pool,
            expected_matrix,
            1e-12,
            "generated BODY sparse pool",
            max_absolute_error);
        require_close(
            result.exported_solver_vector,
            expected_vector,
            1e-12,
            "FUN_007ba570 exported vector",
            max_absolute_error);
        require_close(
            result.exported_solver_matrix,
            expected_matrix,
            1e-12,
            "FUN_007ba570 exported matrix",
            max_absolute_error);

        if (!result.canonical_builtin_row_layout ||
            result.contribution.body_index != 0u ||
            result.contribution.solver_vector !=
                result.assembly.solver_vector ||
            result.contribution.solver_matrix !=
                result.sparse_storage.matrix_pool ||
            result.export_result.solver_vector_count != 6u ||
            result.export_result.solver_matrix_count != 36u) {
            throw std::runtime_error(
                "generated BODY export handoff mismatch");
        }

        bool noncanonical_rejected = false;
        try {
            auto invalid = fixture();
            invalid.row_indices = {
                18u, 0u, 30u, 6u, 24u, 12u,
            };
            (void)generate_and_export_fun_007bc680_body(
                invalid);
        } catch (const std::invalid_argument&) {
            noncanonical_rejected = true;
        }
        if (!noncanonical_rejected) {
            throw std::runtime_error(
                "provider-shaped row layout was accepted as builtin");
        }

        bool provider_rejected = false;
        try {
            auto invalid = fixture();
            invalid.provider_present = true;
            (void)generate_and_export_fun_007bc680_body(
                invalid);
        } catch (const std::invalid_argument&) {
            provider_rejected = true;
        }
        if (!provider_rejected) {
            throw std::runtime_error(
                "provider-present generated BODY export was accepted");
        }

        bool matrix_shape_rejected = false;
        try {
            auto invalid = fixture();
            invalid.matrix_double_count = 35u;
            (void)generate_and_export_fun_007bc680_body(
                invalid);
        } catch (const std::invalid_argument&) {
            matrix_shape_rejected = true;
        }
        if (!matrix_shape_rejected) {
            throw std::runtime_error(
                "non-N-squared builtin matrix count was accepted");
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeGeneratedBodySolverExportCheck/1\",\n"
            << "  \"generation_function\": \"FUN_007bc680\",\n"
            << "  \"storage_function\": \"FUN_007bb8d0\",\n"
            << "  \"export_function\": \"FUN_007ba570\",\n"
            << "  \"export_source_line\": 818768,\n"
            << "  \"body_index\": 0,\n"
            << "  \"scalar_count\": 6,\n"
            << "  \"matrix_double_count\": 36,\n"
            << "  \"canonical_builtin_row_layout\": true,\n"
            << "  \"generated_contribution_matches_export\": true,\n"
            << "  \"sbex_contribution_shape_ready\": true,\n"
            << "  \"provider_present\": false,\n"
            << "  \"noncanonical_layout_rejected\": true,\n"
            << "  \"provider_present_rejected\": true,\n"
            << "  \"matrix_shape_rejected\": true,\n"
            << "  \"sampled_state_refresh_executed\": false,\n"
            << "  \"max_absolute_error\": "
            << std::setprecision(17)
            << max_absolute_error << ",\n"
            << "  \"oracle_tolerance\": 1e-12,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_generated_body_solver_export_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}

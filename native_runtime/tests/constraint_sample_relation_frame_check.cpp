#include "shift_constraint_sample_relation_frame.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

double max_error = 0.0;

void check_close(
    double actual,
    double expected,
    double tolerance = 1e-12) {

    const double error = std::abs(actual - expected);
    max_error = std::max(max_error, error);
    if (error > tolerance * std::max(1.0, std::abs(expected))) {
        throw std::runtime_error(
            "constraint relation refresh oracle mismatch");
    }
}

template <std::size_t N>
void check_array(
    const std::array<double, N>& actual,
    const std::array<double, N>& expected) {

    for (std::size_t index = 0; index < N; ++index) {
        check_close(actual[index], expected[index]);
    }
}

template <typename Fn>
void require_runtime_error(
    Fn&& fn,
    const char* needle,
    const char* label) {

    bool rejected = false;
    try {
        fn();
    } catch (const std::runtime_error& error) {
        rejected =
            std::string(error.what()).find(needle) !=
            std::string::npos;
    }
    if (!rejected) {
        throw std::runtime_error(
            std::string(label) + " was not rejected");
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        using namespace shift::runtime::physics;
        if (argc != 3) {
            std::cerr
                << "usage: shift_runtime_constraint_sample_relation_frame_check "
                << "FILE.gbcf FILE.csrf\n";
            return EXIT_FAILURE;
        }

        const auto source =
            load_prepared_generated_body_constraint_frame(argv[1]);
        const auto relations =
            load_prepared_constraint_sample_relation_frame(argv[2]);
        const auto refreshed =
            refresh_generated_body_constraint_frame(
                source,
                relations);

        if (source.bodies.size() != 2u ||
            source.scalar_count != 6u ||
            relations.body_count != 2u ||
            refreshed.joint_relation_count != 1u ||
            refreshed.hinge_relation_count != 1u ||
            refreshed.bar_relation_count != 1u ||
            refreshed.refreshed_joint_sample_count != 2u ||
            refreshed.refreshed_hinge_sample_count != 2u ||
            refreshed.refreshed_bar_sample_count != 2u) {
            throw std::runtime_error(
                "constraint relation refresh cardinality mismatch");
        }

        const auto& positive =
            refreshed.frame.bodies[0].constraints;
        const auto& negative =
            refreshed.frame.bodies[1].constraints;

        check_array(
            positive.joints.at(0).position,
            std::array<double, 3>{0.5, 1.5, 3.0});
        check_array(
            negative.joints.at(0).position,
            std::array<double, 3>{-1.0, 1.0, 6.0});

        check_array(
            positive.hinges.at(0).angular,
            std::array<double, 3>{2.0, 6.0, 12.0});
        check_array(
            positive.hinges.at(0).linear,
            std::array<double, 3>{8.0, 15.0, 24.0});
        check_array(
            negative.hinges.at(0).angular,
            std::array<double, 3>{0.0, 24.0, 108.0});
        check_array(
            negative.hinges.at(0).linear,
            std::array<double, 3>{0.0, -72.0, 36.0});

        check_array(
            positive.bars.at(0).point,
            std::array<double, 3>{2.0, 0.0, 0.0});
        check_array(
            negative.bars.at(0).point,
            std::array<double, 3>{0.0, 2.0, 0.0});
        const std::array<double, 3> expected_direction = {
            2.0 / std::sqrt(5.0),
            0.0,
            1.0 / std::sqrt(5.0),
        };
        check_array(
            positive.bars.at(0).direction,
            expected_direction);
        check_array(
            negative.bars.at(0).direction,
            expected_direction);

        if (positive.joints.at(0).side_flag != 1u ||
            negative.joints.at(0).side_flag != 0u ||
            positive.hinges.at(0).side_flag != 1u ||
            negative.hinges.at(0).side_flag != 0u ||
            positive.bars.at(0).side_flag != 1u ||
            negative.bars.at(0).side_flag != 0u) {
            throw std::runtime_error(
                "constraint relation endpoint side identity changed");
        }
        if (positive.joints.at(0).scalar_base != 0u ||
            negative.joints.at(0).scalar_base != 0u ||
            positive.hinges.at(0).scalar_base != 3u ||
            negative.hinges.at(0).scalar_base != 3u ||
            positive.bars.at(0).scalar_base != 5u ||
            negative.bars.at(0).scalar_base != 5u) {
            throw std::runtime_error(
                "constraint relation scalar identity changed");
        }

        const auto generated =
            execute_prepared_generated_body_constraint_frame(
                refreshed.frame);
        if (generated.body_count != 2u ||
            generated.joint_sample_count != 2u ||
            generated.hinge_sample_count != 2u ||
            generated.bar_sample_count != 2u) {
            throw std::runtime_error(
                "refreshed GBCF generation cardinality mismatch");
        }
        for (const double value : generated.solver_vector) {
            if (!std::isfinite(value)) {
                throw std::runtime_error(
                    "refreshed GBCF generated non-finite RHS");
            }
        }
        for (const double value : generated.solver_matrix) {
            if (!std::isfinite(value)) {
                throw std::runtime_error(
                    "refreshed GBCF generated non-finite matrix");
            }
        }

        require_runtime_error(
            [&]() {
                auto bad = relations;
                bad.joints.push_back(bad.joints.front());
                (void)refresh_generated_body_constraint_frame(
                    source,
                    bad);
            },
            "ownership is duplicated",
            "duplicate endpoint ownership");

        require_runtime_error(
            [&]() {
                auto bad_source = source;
                bad_source.bodies[0]
                    .constraints.joints[0].side_flag = 0u;
                (void)refresh_generated_body_constraint_frame(
                    bad_source,
                    relations);
            },
            "side flag",
            "endpoint side mismatch");

        require_runtime_error(
            [&]() {
                auto bad_source = source;
                bad_source.bodies[1]
                    .constraints.bars[0].scalar_base = 4u;
                (void)refresh_generated_body_constraint_frame(
                    bad_source,
                    relations);
            },
            "scalar bases do not match",
            "endpoint scalar mismatch");

        require_runtime_error(
            [&]() {
                auto bad_source = source;
                bad_source.bodies[0]
                    .constraints.joints.push_back(
                        bad_source.bodies[0]
                            .constraints.joints.front());
                (void)refresh_generated_body_constraint_frame(
                    bad_source,
                    relations);
            },
            "ownership is incomplete",
            "incomplete endpoint ownership");

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeConstraintSampleRelationFrameCheck/1\",\n"
            << "  \"relation_packet_format\": "
            << "\"SHIFT.NativeConstraintSampleRelationFramePacket/1\",\n"
            << "  \"generated_frame_format\": "
            << "\"SHIFT.NativeGeneratedBodyConstraintFramePacket/1\",\n"
            << "  \"refresh_function\": \"FUN_007b3ed0\",\n"
            << "  \"joint_relation_count\": 1,\n"
            << "  \"hinge_relation_count\": 1,\n"
            << "  \"bar_relation_count\": 1,\n"
            << "  \"joint_endpoint_samples\": 2,\n"
            << "  \"hinge_endpoint_samples\": 2,\n"
            << "  \"bar_endpoint_samples\": 2,\n"
            << "  \"positive_side_flag\": 1,\n"
            << "  \"negative_side_flag\": 0,\n"
            << "  \"complete_endpoint_ownership\": true,\n"
            << "  \"duplicate_ownership_rejected\": true,\n"
            << "  \"side_mismatch_rejected\": true,\n"
            << "  \"scalar_mismatch_rejected\": true,\n"
            << "  \"refreshed_native_generation_executed\": true,\n"
            << "  \"contribution_values_stored_in_relation_packet\": false,\n"
            << "  \"max_absolute_error\": "
            << std::setprecision(17) << max_error << ",\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_constraint_sample_relation_frame_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}

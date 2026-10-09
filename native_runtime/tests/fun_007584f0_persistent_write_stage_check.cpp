#include "shift_fun_007584f0_interpolation_call_seam.hpp"
#include "shift_fun_007584f0_persistent_write_stage.hpp"
#include "shift_fun_007584f0_positive_qword_reduction.hpp"
#include "shift_fun_007584f0_positive_qword_trig.hpp"
#include "shift_fun_007584f0_positive_qword_vector_construction.hpp"
#include "shift_fun_00769640_trig_source_writer.hpp"

#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

std::uint32_t f32_bits(float value) {
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

}  // namespace

int main() {
    try {
        require(kFun007584f0WheelPersistentOffsets ==
                    std::array<std::size_t, 2>{0x0d40u, 0x17c0u},
                "FUN_007584f0 wheel persistent offsets drift");
        require(kFun007584f0WheelStride == 0x0a80u,
                "FUN_007584f0 wheel persistent stride drift");
        require(kFun007584f0FilteredStateOffset == 0x3420u,
                "FUN_007584f0 filtered-state offset drift");
        require(kFun007584f0InterpolationHelper == 0x00783a30u,
                "FUN_007584f0 interpolation helper drift");
        require(kFun007584f0InterpolationCallSite == 0x007587efu,
                "FUN_007584f0 interpolation call site drift");
        require(kFun007584f0InterpolationStoreSite == 0x007587f4u,
                "FUN_007584f0 interpolation store site drift");
        require(kFun007584f0InterpolationArgumentCount == 4u,
                "FUN_007584f0 interpolation argument count drift");
        require(kFun007584f0PositiveQwordReductionStart == 0x007586f9u,
                "FUN_007584f0 positive-qword reduction start drift");
        require(kFun007584f0PositiveQwordStoreSite == 0x00758731u,
                "FUN_007584f0 positive-qword store-site drift");
        require(kFun007584f0AlternateZeroStoreSite == 0x0075873bu,
                "FUN_007584f0 alternate zero-store site drift");
        require(fun_007584f0_positive_qword_destination_offset(0u) == 0x0d40u &&
                    fun_007584f0_positive_qword_destination_offset(1u) == 0x17c0u,
                "FUN_007584f0 positive-qword destination geometry drift");
        require(kFun007584f0SelectedBodyPointerOffset == 0x33a0u &&
                    kFun007584f0SelectedBodyTransformOffset == 0x00d4u,
                "FUN_007584f0 selected BODY transform source drift");
        require(kFun007584f0SourceVector8a0Offset == 0x08a0u &&
                    kFun007584f0SourceVector888Offset == 0x0888u &&
                    kFun007584f0SourceVector8d0Offset == 0x08d0u,
                "FUN_007584f0 positive-qword vector source offsets drift");
        require(kFun007584f0TrigSpanStart == 0x00758560u &&
                    kFun007584f0TrigSpanEnd == 0x0075858bu,
                "FUN_007584f0 positive-qword trig span drift");
        require(kFun007584f0CosineCallSite == 0x0075856fu &&
                    kFun007584f0SineCallSite == 0x00758580u,
                "FUN_007584f0 positive-qword trig call order drift");
        require(fun_007584f0_trig_source_offset(0u) == 0x0738u &&
                    fun_007584f0_trig_source_offset(1u) == 0x11b8u,
                "FUN_007584f0 positive-qword trig source geometry drift");
        require(kFun00769640TrigWriterSpanStart == 0x00769c05u &&
                    kFun00769640TrigWriterSpanEnd == 0x00769c2du,
                "FUN_00769640 trig source writer span drift");
        require(kFun00769640TableRootOffset == 0x4330u &&
                    kFun00769640TableRecordStride == 0x50u,
                "FUN_00769640 trig source table geometry drift");
        require(kFun00769640SelectedRecordIndices ==
                    std::array<std::size_t, 2>{12u, 13u},
                "FUN_00769640 selected table record drift");
        require(kFun00769640TableBaseValueOffsets ==
                    std::array<std::size_t, 2>{0x54b8u, 0x5508u} &&
                    kFun00769640TableSlopeValueOffsets ==
                    std::array<std::size_t, 2>{0x54c0u, 0x5510u} &&
                    kFun00769640TableCoefficientAbsoluteOffsets ==
                    std::array<std::size_t, 2>{0x54ccu, 0x551cu},
                "FUN_00769640 trig source table field offsets drift");

        const Fun007584f0InterpolationArguments interpolation_arguments{{
            0.0f,
            2.0f,
            1.0f,
            1.0f,
        }};
        const auto interpolation =
            execute_fun_007584f0_interpolation_native(interpolation_arguments);
        require(interpolation.helper_call_count == 1u,
                "FUN_007584f0 interpolation helper call count drift");
        require(interpolation.destination_offset == 0x3420u,
                "FUN_007584f0 interpolation destination drift");
        require(interpolation.value == 1.0f,
                "FUN_007584f0 native FUN_00783a30 formula drift");

        const double trig_source = execute_fun_00769640_trig_source_writer({
            0.0,
            0.125,
            2,
        });
        require(trig_source == 0.25,
                "FUN_00769640 trig source writer arithmetic drift");

        bool rejected_non_finite_writer = false;
        try {
            (void)execute_fun_00769640_trig_source_writer({
                std::numeric_limits<double>::infinity(),
                1.0,
                1,
            });
        } catch (const std::invalid_argument&) {
            rejected_non_finite_writer = true;
        }
        require(rejected_non_finite_writer,
                "FUN_00769640 non-finite trig source input failed open");

        const auto trig =
            materialize_fun_007584f0_positive_qword_trig(trig_source);
        require(f32_bits(trig.angle_f32) == 0x3e800000u,
                "FUN_007584f0 trig angle f32 spill drift");
        require(f32_bits(trig.cosine_f32) == 0x3f780aa5u,
                "FUN_007584f0 FCOS f32 witness drift");
        require(f32_bits(trig.sine_f32) == 0x3e7d5777u,
                "FUN_007584f0 FSIN f32 witness drift");

        bool rejected_non_finite_trig = false;
        try {
            (void)materialize_fun_007584f0_positive_qword_trig(
                std::numeric_limits<double>::infinity());
        } catch (const std::invalid_argument&) {
            rejected_non_finite_trig = true;
        }
        require(rejected_non_finite_trig,
                "FUN_007584f0 non-finite trig source failed open");

        const Fun007584f0PositiveQwordVectorSourceInput vector_source{
            {1.0f, 0.0f, 0.0f,
             0.0f, 1.0f, 0.0f,
             0.0f, 0.0f, 1.0f},
            0.0f,
            1.0f,
            1u,
            {1.0, 2.0, 3.0},
            {4.0, 5.0, 6.0},
            {7.0, 8.0, 9.0},
            2.0,
            2.0,
            0.25,
            1.0,
            0.5f,
            7.0f,
            0.5,
            1.0,
            2.0,
        };
        const auto constructed =
            materialize_fun_007584f0_positive_qword_vectors(vector_source);
        require(constructed.a == Fun007584f0PositiveQwordVector{0.0, 0.0, 1.0},
                "FUN_007584f0 vector A construction drift");
        require(constructed.b ==
                    Fun007584f0PositiveQwordVector{-15.25, 41.5, -14.25},
                "FUN_007584f0 vector B construction drift");
        require(constructed.c == Fun007584f0PositiveQwordVector{0.0, 6.0, -4.0},
                "FUN_007584f0 vector C construction drift");

        auto trig_vector_source = vector_source;
        trig_vector_source.cosine_f32 = trig.cosine_f32;
        trig_vector_source.sine_f32 = trig.sine_f32;
        const auto trig_constructed =
            materialize_fun_007584f0_positive_qword_vectors(trig_vector_source);
        require(trig_constructed.a ==
                    Fun007584f0PositiveQwordVector{
                        0.0,
                        static_cast<double>(trig.cosine_f32),
                        static_cast<double>(trig.sine_f32)},
                "FUN_007584f0 trig-to-vector A handoff drift");

        const double constructed_qword =
            execute_fun_007584f0_positive_qword_reduction(constructed);
        require(constructed_qword == 3.5625,
                "FUN_007584f0 constructed positive-qword result drift");

        auto index_zero_source = vector_source;
        index_zero_source.loop_index = 0u;
        index_zero_source.index_zero_factor_aa9afc = 2.0f;
        const auto index_zero_constructed =
            materialize_fun_007584f0_positive_qword_vectors(index_zero_source);
        require(index_zero_constructed.b != constructed.b,
                "FUN_007584f0 index-zero factor branch was not applied");

        bool rejected_bad_loop_index = false;
        try {
            auto bad = vector_source;
            bad.loop_index = 2u;
            (void)materialize_fun_007584f0_positive_qword_vectors(bad);
        } catch (const std::out_of_range&) {
            rejected_bad_loop_index = true;
        }
        require(rejected_bad_loop_index,
                "FUN_007584f0 invalid positive-qword loop index failed open");

        const Fun007584f0PositiveQwordReductionInput qword_input{
            {2.0, 3.0, 4.0},
            {5.0, 7.0, 11.0},
            {13.0, 17.0, 19.0},
        };
        const double positive_qword =
            execute_fun_007584f0_positive_qword_reduction(qword_input);
        require(positive_qword == 75.0 / 153.0,
                "FUN_007584f0 positive-qword reduction formula drift");

        bool rejected_zero_denominator = false;
        try {
            (void)execute_fun_007584f0_positive_qword_reduction({
                {1.0, 0.0, 0.0},
                {2.0, 3.0, 4.0},
                {0.0, 1.0, 0.0},
            });
        } catch (const std::invalid_argument&) {
            rejected_zero_denominator = true;
        }
        require(rejected_zero_denominator,
                "FUN_007584f0 zero positive-qword denominator failed open");

        bool rejected_non_finite_vector = false;
        try {
            (void)execute_fun_007584f0_positive_qword_reduction({
                {std::numeric_limits<double>::infinity(), 0.0, 0.0},
                {1.0, 0.0, 0.0},
                {1.0, 0.0, 0.0},
            });
        } catch (const std::invalid_argument&) {
            rejected_non_finite_vector = true;
        }
        require(rejected_non_finite_vector,
                "FUN_007584f0 non-finite positive-qword vector failed open");

        const Fun00765c40LoadTerms loads = {-0.5, 2.0, 8.0, 9.0};
        const Fun007584f0ComputedInputs computed{
            {11.0, constructed_qword},
            interpolation.value,
        };
        const auto state = materialize_fun_007584f0_persistent_write_stage(
            loads,
            computed);
        require(state.wheel_values[0] == 0.0,
                "FUN_007584f0 non-positive load must write zero qword");
        require(state.wheel_values[1] == constructed_qword,
                "FUN_007584f0 positive load must preserve computed qword");
        require(state.filtered_value == 1.0f,
                "FUN_007584f0 +0x3420 interpolation handoff drift");

        const Fun00765c40LoadTerms zero_loads = {0.0, 0.0, 1.0, 1.0};
        const auto zero_state = materialize_fun_007584f0_persistent_write_stage(
            zero_loads,
            computed);
        require(zero_state.wheel_values[0] == 0.0 &&
                    zero_state.wheel_values[1] == 0.0,
                "FUN_007584f0 zero load must take alternate zero branch");

        std::cout
            << "{\"format\":\"" << kFun007584f0PersistentWriteStageFormat << "\","
            << "\"ready\":true,"
            << "\"persistent_write_count\":3,"
            << "\"interpolation_call_seam_format\":\""
            << kFun007584f0InterpolationCallSeamFormat << "\","
            << "\"interpolation_helper_call_count\":1,"
            << "\"interpolation_helper_formula_internalized\":true,"
            << "\"positive_qword_reduction_format\":\""
            << kFun007584f0PositiveQwordReductionFormat << "\","
            << "\"positive_qword_vector_construction_format\":\""
            << kFun007584f0PositiveQwordVectorConstructionFormat << "\","
            << "\"positive_qword_trig_format\":\""
            << kFun007584f0PositiveQwordTrigFormat << "\","
            << "\"trig_source_writer_format\":\""
            << kFun00769640TrigSourceWriterFormat << "\","
            << "\"positive_qword_final_reduction_internalized\":true,"
            << "\"positive_qword_vector_arithmetic_internalized\":true,"
            << "\"positive_qword_source_acquisition_internalized\":false,"
            << "\"positive_qword_x87_trig_internalized\":true,"
            << "\"positive_qword_trig_source_writer_arithmetic_internalized\":true,"
            << "\"positive_qword_trig_source_table_acquisition_internalized\":false,"
            << "\"branch_semantics_internalized\":true,"
            << "\"computed_arithmetic_internalized\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}

cmake_minimum_required(VERSION 3.16)
project(shift_vulkan_probe LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

enable_testing()

add_library(shift_xbox_draw_input STATIC src/xbox_draw_input.cpp)
target_include_directories(shift_xbox_draw_input PUBLIC include)

add_library(shift_xbox_guest_ring STATIC src/xbox_guest_ring.cpp)
target_include_directories(shift_xbox_guest_ring PUBLIC include)
target_link_libraries(shift_xbox_guest_ring PUBLIC shift_xbox_draw_input)

add_library(shift_xbox_shader_translate STATIC src/xbox_shader_translate.cpp)
target_include_directories(shift_xbox_shader_translate PUBLIC include)
target_link_libraries(shift_xbox_shader_translate PUBLIC shift_xbox_draw_input)

add_executable(shift_xbox_draw_input_check tests/xbox_draw_input_check.cpp)
target_link_libraries(shift_xbox_draw_input_check PRIVATE shift_xbox_draw_input)
add_test(NAME shift_xbox_draw_input_check COMMAND shift_xbox_draw_input_check)

add_executable(shift_xbox_guest_ring_check tests/xbox_guest_ring_check.cpp)
target_link_libraries(shift_xbox_guest_ring_check PRIVATE shift_xbox_guest_ring)
add_test(NAME shift_xbox_guest_ring_check COMMAND shift_xbox_guest_ring_check)

add_executable(shift_xbox_shader_translate_check tests/xbox_shader_translate_check.cpp)
target_link_libraries(shift_xbox_shader_translate_check PRIVATE shift_xbox_shader_translate)
target_compile_definitions(shift_xbox_shader_translate_check PRIVATE
  SHIFT_XBOX_SHADER_TEST_FIXTURE_DIR="${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures"
)
add_test(NAME shift_xbox_shader_translate_check COMMAND shift_xbox_shader_translate_check)

find_package(Vulkan QUIET)

if(NOT Vulkan_FOUND)
  message(STATUS "Vulkan SDK not found; shift_vulkan_probe will not be built")
  return()
endif()

add_library(shift_xbox_live_vulkan_renderer STATIC src/xbox_live_vulkan_renderer.cpp)
target_include_directories(shift_xbox_live_vulkan_renderer PUBLIC include)
target_link_libraries(shift_xbox_live_vulkan_renderer PUBLIC Vulkan::Vulkan)

add_executable(shift_vulkan_probe src/vulkan_probe.cpp)
target_link_libraries(shift_vulkan_probe PRIVATE Vulkan::Vulkan)

add_executable(shift_vulkan_headless_clear src/vulkan_headless_clear.cpp)
target_link_libraries(shift_vulkan_headless_clear PRIVATE Vulkan::Vulkan)

add_executable(
  shift_vulkan_world_transform_check
  src/vulkan_world_transform_check.cpp
)
target_link_libraries(shift_vulkan_world_transform_check PRIVATE Vulkan::Vulkan)

find_program(GLSLANG_VALIDATOR NAMES glslangValidator)

if(GLSLANG_VALIDATOR)
  set(SHIFT_VULKAN_SHADER_DIR ${CMAKE_CURRENT_BINARY_DIR}/shaders)
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/live_draw_smoke.vert.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/live_draw_smoke.vert
            -o ${SHIFT_VULKAN_SHADER_DIR}/live_draw_smoke.vert.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/live_draw_smoke.vert
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/live_draw_smoke.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/live_draw_smoke.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/live_draw_smoke.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/live_draw_smoke.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/live_draw_rectlist.geom.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/live_draw_rectlist.geom
            -o ${SHIFT_VULKAN_SHADER_DIR}/live_draw_rectlist.geom.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/live_draw_rectlist.geom
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/clip_disabled_window.vert.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/clip_disabled_window.vert
            -o ${SHIFT_VULKAN_SHADER_DIR}/clip_disabled_window.vert.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/clip_disabled_window.vert
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/clip_disabled_window.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/clip_disabled_window.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/clip_disabled_window.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/clip_disabled_window.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0.vert.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_sample0.vert
            -o ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0.vert.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_sample0.vert
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_sample0.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_sample0.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0_single.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_sample0_single.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0_single.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_sample0_single.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_4x_u16x4.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_4x_u16x4.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_4x_u16x4.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_4x_u16x4.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0_rg16f_ms.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_sample0_rg16f_ms.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0_rg16f_ms.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_sample0_rg16f_ms.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0_rg16f_single.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_sample0_rg16f_single.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0_rg16f_single.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_sample0_rg16f_single.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/copy_constant.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/copy_constant.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/copy_constant.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/copy_constant.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/edram_clear.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/edram_clear.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/edram_clear.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/edram_clear.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/xenos_edram_alias_4x_to_1x.vert.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_edram_alias_4x_to_1x.vert
            -o ${SHIFT_VULKAN_SHADER_DIR}/xenos_edram_alias_4x_to_1x.vert.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_edram_alias_4x_to_1x.vert
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/xenos_edram_alias_4x_to_1x.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_edram_alias_4x_to_1x.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/xenos_edram_alias_4x_to_1x.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_edram_alias_4x_to_1x.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/edram_alias_lane_seed.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/edram_alias_lane_seed.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/edram_alias_lane_seed.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/edram_alias_lane_seed.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/edram_alias_lane_baseline.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/edram_alias_lane_baseline.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/edram_alias_lane_baseline.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/edram_alias_lane_baseline.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_black.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_black.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_black.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_black.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/gamma_target_encoded.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/gamma_target_encoded.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/gamma_target_encoded.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/gamma_target_encoded.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/gamma_target_linear.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/gamma_target_linear.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/gamma_target_linear.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/gamma_target_linear.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_gamma_single.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_gamma_single.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_gamma_single.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_gamma_single.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_gamma_ms.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_gamma_ms.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_gamma_ms.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/xenos_copy_gamma_ms.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/disclaimer_frame907.vert.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/disclaimer_frame907.vert
            -o ${SHIFT_VULKAN_SHADER_DIR}/disclaimer_frame907.vert.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/disclaimer_frame907.vert
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/disclaimer_frame907_encoded.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/disclaimer_frame907_encoded.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/disclaimer_frame907_encoded.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/disclaimer_frame907_encoded.frag
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/disclaimer_frame907_linear.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/disclaimer_frame907_linear.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/disclaimer_frame907_linear.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/disclaimer_frame907_linear.frag
    VERBATIM
  )
  add_executable(xbox_live_vulkan_renderer_check tests/xbox_live_vulkan_renderer_check.cpp)
  add_dependencies(xbox_live_vulkan_renderer_check shift_xbox_live_vulkan_renderer)
  target_link_libraries(xbox_live_vulkan_renderer_check PRIVATE
    shift_xbox_live_vulkan_renderer
    shift_xbox_draw_input
  )
  add_custom_target(shift_xbox_live_vulkan_renderer_smoke_shaders
    DEPENDS
      ${SHIFT_VULKAN_SHADER_DIR}/live_draw_smoke.vert.spv
      ${SHIFT_VULKAN_SHADER_DIR}/live_draw_smoke.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/live_draw_rectlist.geom.spv
      ${SHIFT_VULKAN_SHADER_DIR}/clip_disabled_window.vert.spv
      ${SHIFT_VULKAN_SHADER_DIR}/clip_disabled_window.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0.vert.spv
      ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0_single.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_4x_u16x4.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0_rg16f_ms.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0_rg16f_single.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/copy_constant.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/edram_clear.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/xenos_edram_alias_4x_to_1x.vert.spv
      ${SHIFT_VULKAN_SHADER_DIR}/xenos_edram_alias_4x_to_1x.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/edram_alias_lane_seed.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/edram_alias_lane_baseline.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_black.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/gamma_target_encoded.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/gamma_target_linear.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_gamma_single.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_gamma_ms.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/disclaimer_frame907.vert.spv
      ${SHIFT_VULKAN_SHADER_DIR}/disclaimer_frame907_encoded.frag.spv
      ${SHIFT_VULKAN_SHADER_DIR}/disclaimer_frame907_linear.frag.spv
  )
  add_dependencies(xbox_live_vulkan_renderer_check shift_xbox_live_vulkan_renderer_smoke_shaders)
  add_test(
    NAME xbox_live_vulkan_renderer_check
    COMMAND xbox_live_vulkan_renderer_check
            ${SHIFT_VULKAN_SHADER_DIR}/live_draw_smoke.vert.spv
            ${SHIFT_VULKAN_SHADER_DIR}/live_draw_smoke.frag.spv
            ${SHIFT_VULKAN_SHADER_DIR}/live_draw_rectlist.geom.spv
            ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0.vert.spv
            ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0.frag.spv
            ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0_single.frag.spv
            ${SHIFT_VULKAN_SHADER_DIR}/clip_disabled_window.vert.spv
            ${SHIFT_VULKAN_SHADER_DIR}/clip_disabled_window.frag.spv
            ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_black.frag.spv
            ${SHIFT_VULKAN_SHADER_DIR}/gamma_target_encoded.frag.spv
            ${SHIFT_VULKAN_SHADER_DIR}/gamma_target_linear.frag.spv
            ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_gamma_single.frag.spv
            ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_gamma_ms.frag.spv
            ${SHIFT_VULKAN_SHADER_DIR}/disclaimer_frame907.vert.spv
            ${SHIFT_VULKAN_SHADER_DIR}/disclaimer_frame907_encoded.frag.spv
            ${SHIFT_VULKAN_SHADER_DIR}/disclaimer_frame907_linear.frag.spv
            ${CMAKE_CURRENT_SOURCE_DIR}/../evidence/process2_disclaimer_frame907_draw5058_dxt5_raw_20261026.bin
            ${CMAKE_CURRENT_SOURCE_DIR}/../evidence/process2_disclaimer_frame907_draw5058_packed_mip0_rgba8_20261026.bin
            ${CMAKE_CURRENT_SOURCE_DIR}/../evidence/process2_disclaimer_frame907_draw5058_vertices_20261026.bin
            ${CMAKE_CURRENT_SOURCE_DIR}/../evidence/process2_disclaimer_frame907_draw5059_vertices_20261026.bin
            ${CMAKE_CURRENT_SOURCE_DIR}/../evidence/process2_disclaimer_frame907_draw5060_vertices_20261026.bin
            ${CMAKE_CURRENT_SOURCE_DIR}/../evidence/process2_disclaimer_frame907_draw5061_vertices_20261026.bin
            ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_4x_u16x4.frag.spv
            ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0_rg16f_ms.frag.spv
            ${SHIFT_VULKAN_SHADER_DIR}/xenos_copy_sample0_rg16f_single.frag.spv
            ${SHIFT_VULKAN_SHADER_DIR}/copy_constant.frag.spv
            ${SHIFT_VULKAN_SHADER_DIR}/edram_clear.frag.spv
            ${SHIFT_VULKAN_SHADER_DIR}/xenos_edram_alias_4x_to_1x.vert.spv
            ${SHIFT_VULKAN_SHADER_DIR}/xenos_edram_alias_4x_to_1x.frag.spv
            ${SHIFT_VULKAN_SHADER_DIR}/edram_alias_lane_seed.frag.spv
            ${SHIFT_VULKAN_SHADER_DIR}/edram_alias_lane_baseline.frag.spv
  )
  set_tests_properties(xbox_live_vulkan_renderer_check PROPERTIES SKIP_RETURN_CODE 77)

  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/triangle.vert.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/triangle.vert
            -o ${SHIFT_VULKAN_SHADER_DIR}/triangle.vert.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/triangle.vert
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/triangle.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/triangle.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/triangle.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/triangle.frag
    VERBATIM
  )
  add_custom_target(shift_vulkan_triangle_shaders
    DEPENDS
      ${SHIFT_VULKAN_SHADER_DIR}/triangle.vert.spv
      ${SHIFT_VULKAN_SHADER_DIR}/triangle.frag.spv
  )
  add_executable(shift_vulkan_headless_triangle src/vulkan_headless_triangle.cpp)
  add_dependencies(shift_vulkan_headless_triangle shift_vulkan_triangle_shaders)
  target_link_libraries(shift_vulkan_headless_triangle PRIVATE Vulkan::Vulkan)
else()
  message(STATUS "glslangValidator not found; headless triangle target will not be built")
endif()

if(GLSLANG_VALIDATOR)
  add_executable(shift_vulkan_render_geometry src/vulkan_render_geometry.cpp)
  target_link_libraries(shift_vulkan_render_geometry PRIVATE Vulkan::Vulkan)
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/geometry.vert.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/geometry.vert
            -o ${SHIFT_VULKAN_SHADER_DIR}/geometry.vert.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/geometry.vert
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/geometry.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/geometry.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/geometry.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/geometry.frag
    VERBATIM
  )
  add_custom_target(shift_vulkan_geometry_shaders
    DEPENDS
      ${SHIFT_VULKAN_SHADER_DIR}/geometry.vert.spv
      ${SHIFT_VULKAN_SHADER_DIR}/geometry.frag.spv
  )
  add_dependencies(shift_vulkan_render_geometry shift_vulkan_geometry_shaders)
else()
  message(STATUS "glslangValidator not found; geometry shader target will not be built")
endif()

if(GLSLANG_VALIDATOR)
  add_executable(shift_vulkan_constant_upload src/vulkan_constant_upload.cpp)
  target_link_libraries(shift_vulkan_constant_upload PRIVATE Vulkan::Vulkan)
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/constants.vert.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/constants.vert
            -o ${SHIFT_VULKAN_SHADER_DIR}/constants.vert.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/constants.vert
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/constants.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/constants.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/constants.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/constants.frag
    VERBATIM
  )
  add_custom_target(shift_vulkan_constant_shaders
    DEPENDS
      ${SHIFT_VULKAN_SHADER_DIR}/constants.vert.spv
      ${SHIFT_VULKAN_SHADER_DIR}/constants.frag.spv
  )
  add_dependencies(shift_vulkan_constant_upload shift_vulkan_constant_shaders)
else()
  message(STATUS "glslangValidator not found; constant upload target will not be built")
endif()

if(GLSLANG_VALIDATOR)
  add_executable(shift_vulkan_texture_upload src/vulkan_texture_upload.cpp)
  target_link_libraries(shift_vulkan_texture_upload PRIVATE Vulkan::Vulkan)
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/texture.vert.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/texture.vert
            -o ${SHIFT_VULKAN_SHADER_DIR}/texture.vert.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/texture.vert
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/texture.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/texture.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/texture.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/texture.frag
    VERBATIM
  )
  add_custom_target(shift_vulkan_texture_shaders
    DEPENDS
      ${SHIFT_VULKAN_SHADER_DIR}/texture.vert.spv
      ${SHIFT_VULKAN_SHADER_DIR}/texture.frag.spv
  )
  add_dependencies(shift_vulkan_texture_upload shift_vulkan_texture_shaders)
else()
  message(STATUS "glslangValidator not found; texture upload target will not be built")
endif()

if(GLSLANG_VALIDATOR)
  add_executable(shift_vulkan_sampler_cube src/vulkan_sampler_cube.cpp)
  target_link_libraries(shift_vulkan_sampler_cube PRIVATE Vulkan::Vulkan)
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/cube.vert.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/cube.vert
            -o ${SHIFT_VULKAN_SHADER_DIR}/cube.vert.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/cube.vert
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/cube.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/cube.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/cube.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/cube.frag
    VERBATIM
  )
  add_custom_target(shift_vulkan_cube_shaders
    DEPENDS
      ${SHIFT_VULKAN_SHADER_DIR}/cube.vert.spv
      ${SHIFT_VULKAN_SHADER_DIR}/cube.frag.spv
  )
  add_dependencies(shift_vulkan_sampler_cube shift_vulkan_cube_shaders)
else()
  message(STATUS "glslangValidator not found; samplerCube target will not be built")
endif()

if(Vulkan_FOUND)
  add_executable(shift_vulkan_bundle_runner src/vulkan_bundle_runner.cpp)
  target_link_libraries(shift_vulkan_bundle_runner PRIVATE Vulkan::Vulkan)
endif()

if(Vulkan_FOUND)
  add_executable(shift_vulkan_bundle_execute src/vulkan_bundle_execute.cpp)
  target_include_directories(shift_vulkan_bundle_execute PRIVATE include)
  target_link_libraries(shift_vulkan_bundle_execute PRIVATE Vulkan::Vulkan)
endif()

add_library(
  shift_vulkan_surface_backend
  STATIC
  src/vulkan_surface_backend.cpp
)
target_include_directories(
  shift_vulkan_surface_backend
  PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include
)
target_link_libraries(
  shift_vulkan_surface_backend
  PUBLIC
  Vulkan::Vulkan
)

if(ANDROID)
  add_library(
    shift_vulkan_android_surface_probe
    SHARED
    src/android_vulkan_surface_probe.cpp
  )
  target_include_directories(
    shift_vulkan_android_surface_probe
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
  )
  target_compile_definitions(
    shift_vulkan_android_surface_probe
    PRIVATE
    VK_USE_PLATFORM_ANDROID_KHR
  )
  target_link_libraries(
    shift_vulkan_android_surface_probe
    PRIVATE
    shift_vulkan_surface_backend
    Vulkan::Vulkan
  )
else()
  find_package(PkgConfig QUIET)
  if(PkgConfig_FOUND)
    pkg_check_modules(XCB QUIET IMPORTED_TARGET xcb)
  endif()
  if(XCB_FOUND)
    add_library(
      shift_vulkan_xcb_surface_probe
      STATIC
      src/xcb_vulkan_surface_probe.cpp
    )
    target_include_directories(
      shift_vulkan_xcb_surface_probe
      PUBLIC
      ${CMAKE_CURRENT_SOURCE_DIR}/include
    )
    target_compile_definitions(
      shift_vulkan_xcb_surface_probe
      PRIVATE
      VK_USE_PLATFORM_XCB_KHR
    )
    target_link_libraries(
      shift_vulkan_xcb_surface_probe
      PRIVATE
      shift_vulkan_surface_backend
      Vulkan::Vulkan
      PkgConfig::XCB
    )
  endif()
endif()

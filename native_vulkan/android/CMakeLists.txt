cmake_minimum_required(VERSION 3.22)
project(shift_android_native_activity LANGUAGES CXX)

if(NOT ANDROID)
  message(FATAL_ERROR "This CMake entrypoint requires the Android NDK toolchain")
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_library(SHIFT_ANDROID_LIB android REQUIRED)
find_library(SHIFT_LOG_LIB log REQUIRED)
find_library(SHIFT_VULKAN_LIB vulkan REQUIRED)

add_library(shift_xbox_draw_input STATIC ../src/xbox_draw_input.cpp)
add_library(shift_xbox_guest_ring STATIC ../src/xbox_guest_ring.cpp)
add_library(shift_xbox_shader_translate STATIC ../src/xbox_shader_translate.cpp)
add_library(shift_xbox_live_vulkan_renderer STATIC ../src/xbox_live_vulkan_renderer.cpp)
target_include_directories(shift_xbox_draw_input PUBLIC ../include)
target_include_directories(shift_xbox_guest_ring PUBLIC ../include)
target_include_directories(shift_xbox_shader_translate PUBLIC ../include)
target_include_directories(shift_xbox_live_vulkan_renderer PUBLIC ../include)
target_link_libraries(shift_xbox_guest_ring PUBLIC shift_xbox_draw_input)
target_link_libraries(shift_xbox_shader_translate PUBLIC shift_xbox_draw_input)
target_link_libraries(shift_xbox_live_vulkan_renderer PUBLIC ${SHIFT_VULKAN_LIB})

find_program(GLSLANG_VALIDATOR NAMES glslangValidator)
if(GLSLANG_VALIDATOR)
  set(SHIFT_ANDROID_SHADER_DIR ${CMAKE_CURRENT_BINARY_DIR}/shaders)
  foreach(stage IN ITEMS vert frag)
    add_custom_command(
      OUTPUT ${SHIFT_ANDROID_SHADER_DIR}/live_draw_smoke.${stage}.spv
      COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_ANDROID_SHADER_DIR}
      COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
              ${CMAKE_CURRENT_SOURCE_DIR}/../shaders/live_draw_smoke.${stage}
              -o ${SHIFT_ANDROID_SHADER_DIR}/live_draw_smoke.${stage}.spv
      DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../shaders/live_draw_smoke.${stage}
      VERBATIM
    )
    list(APPEND SHIFT_ANDROID_LIVE_DRAW_SPIRV
      ${SHIFT_ANDROID_SHADER_DIR}/live_draw_smoke.${stage}.spv)
  endforeach()
  add_custom_command(
    OUTPUT ${SHIFT_ANDROID_SHADER_DIR}/live_draw_rectlist.geom.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_ANDROID_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/../shaders/live_draw_rectlist.geom
            -o ${SHIFT_ANDROID_SHADER_DIR}/live_draw_rectlist.geom.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../shaders/live_draw_rectlist.geom
    VERBATIM
  )
  foreach(stage IN ITEMS vert frag)
    add_custom_command(
      OUTPUT ${SHIFT_ANDROID_SHADER_DIR}/xenos_copy_sample0.${stage}.spv
      COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_ANDROID_SHADER_DIR}
      COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
              ${CMAKE_CURRENT_SOURCE_DIR}/../shaders/xenos_copy_sample0.${stage}
              -o ${SHIFT_ANDROID_SHADER_DIR}/xenos_copy_sample0.${stage}.spv
      DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../shaders/xenos_copy_sample0.${stage}
      VERBATIM
    )
    list(APPEND SHIFT_ANDROID_LIVE_DRAW_SPIRV
      ${SHIFT_ANDROID_SHADER_DIR}/xenos_copy_sample0.${stage}.spv)
  endforeach()
  add_custom_command(
    OUTPUT ${SHIFT_ANDROID_SHADER_DIR}/xenos_copy_sample0_single.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_ANDROID_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/../shaders/xenos_copy_sample0_single.frag
            -o ${SHIFT_ANDROID_SHADER_DIR}/xenos_copy_sample0_single.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../shaders/xenos_copy_sample0_single.frag
    VERBATIM
  )
  list(APPEND SHIFT_ANDROID_LIVE_DRAW_SPIRV
    ${SHIFT_ANDROID_SHADER_DIR}/live_draw_rectlist.geom.spv
    ${SHIFT_ANDROID_SHADER_DIR}/xenos_copy_sample0_single.frag.spv)
  add_custom_command(
    OUTPUT ${SHIFT_ANDROID_SHADER_DIR}/xenos_copy_black.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_ANDROID_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/../shaders/xenos_copy_black.frag
            -o ${SHIFT_ANDROID_SHADER_DIR}/xenos_copy_black.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../shaders/xenos_copy_black.frag
    VERBATIM
  )
  list(APPEND SHIFT_ANDROID_LIVE_DRAW_SPIRV
    ${SHIFT_ANDROID_SHADER_DIR}/xenos_copy_black.frag.spv)
  foreach(shader IN ITEMS gamma_target_encoded.frag
                          gamma_target_linear.frag
                          xenos_copy_gamma_single.frag
                          xenos_copy_gamma_ms.frag)
    add_custom_command(
      OUTPUT ${SHIFT_ANDROID_SHADER_DIR}/${shader}.spv
      COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_ANDROID_SHADER_DIR}
      COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
              ${CMAKE_CURRENT_SOURCE_DIR}/../shaders/${shader}
              -o ${SHIFT_ANDROID_SHADER_DIR}/${shader}.spv
      DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../shaders/${shader}
      VERBATIM
    )
    list(APPEND SHIFT_ANDROID_LIVE_DRAW_SPIRV
      ${SHIFT_ANDROID_SHADER_DIR}/${shader}.spv)
  endforeach()
  foreach(shader IN ITEMS xenos_copy_4x_u16x4.frag
                          xenos_copy_sample0_rg16f_ms.frag
                          xenos_copy_sample0_rg16f_single.frag)
    add_custom_command(
      OUTPUT ${SHIFT_ANDROID_SHADER_DIR}/${shader}.spv
      COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_ANDROID_SHADER_DIR}
      COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
              ${CMAKE_CURRENT_SOURCE_DIR}/../shaders/${shader}
              -o ${SHIFT_ANDROID_SHADER_DIR}/${shader}.spv
      DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../shaders/${shader}
      VERBATIM
    )
    list(APPEND SHIFT_ANDROID_LIVE_DRAW_SPIRV
      ${SHIFT_ANDROID_SHADER_DIR}/${shader}.spv)
  endforeach()
  add_custom_command(
    OUTPUT ${SHIFT_ANDROID_SHADER_DIR}/copy_constant.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_ANDROID_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
            ${CMAKE_CURRENT_SOURCE_DIR}/../tests/fixtures/copy_constant.frag
            -o ${SHIFT_ANDROID_SHADER_DIR}/copy_constant.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../tests/fixtures/copy_constant.frag
    VERBATIM
  )
  list(APPEND SHIFT_ANDROID_LIVE_DRAW_SPIRV
    ${SHIFT_ANDROID_SHADER_DIR}/copy_constant.frag.spv)
  # Keep the Android offscreen regression's shader inputs in sync with the
  # host renderer check, including real window-coordinate transform shaders.
  foreach(stage IN ITEMS vert frag)
    add_custom_command(
      OUTPUT ${SHIFT_ANDROID_SHADER_DIR}/clip_disabled_window.${stage}.spv
      COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_ANDROID_SHADER_DIR}
      COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.1
              ${CMAKE_CURRENT_SOURCE_DIR}/../shaders/clip_disabled_window.${stage}
              -o ${SHIFT_ANDROID_SHADER_DIR}/clip_disabled_window.${stage}.spv
      DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../shaders/clip_disabled_window.${stage}
      VERBATIM
    )
    list(APPEND SHIFT_ANDROID_LIVE_DRAW_SPIRV
      ${SHIFT_ANDROID_SHADER_DIR}/clip_disabled_window.${stage}.spv)
  endforeach()
  add_custom_target(shift_android_live_draw_smoke_shaders
    DEPENDS ${SHIFT_ANDROID_LIVE_DRAW_SPIRV})
  add_executable(xbox_live_vulkan_renderer_check ../tests/xbox_live_vulkan_renderer_check.cpp)
  add_dependencies(xbox_live_vulkan_renderer_check shift_android_live_draw_smoke_shaders)
  target_link_libraries(xbox_live_vulkan_renderer_check PRIVATE
    shift_xbox_live_vulkan_renderer shift_xbox_draw_input ${SHIFT_VULKAN_LIB})
endif()

add_executable(shift_xbox_guest_ring_check ../tests/xbox_guest_ring_check.cpp)
target_link_libraries(shift_xbox_guest_ring_check PRIVATE shift_xbox_guest_ring)

add_executable(shift_xbox_draw_input_check ../tests/xbox_draw_input_check.cpp)
target_link_libraries(shift_xbox_draw_input_check PRIVATE shift_xbox_draw_input)

add_executable(
  shift_xbox_shader_translate_check
  ../tests/xbox_shader_translate_check.cpp
)
target_link_libraries(
  shift_xbox_shader_translate_check
  PRIVATE
  shift_xbox_shader_translate
)

# Offscreen command-line runner used to exercise the same captured Vulkan
# bundle on Android GPUs without coupling the renderer to a window system.
add_executable(
  shift_vulkan_bundle_execute
  ../src/vulkan_bundle_execute.cpp
)
target_include_directories(
  shift_vulkan_bundle_execute
  PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/../include
)
target_compile_options(
  shift_vulkan_bundle_execute
  PRIVATE
  -Wall
  -Wextra
  -Wpedantic
)
target_link_libraries(
  shift_vulkan_bundle_execute
  PRIVATE
  ${SHIFT_VULKAN_LIB}
)

add_library(
  shift_vulkan_android_native_activity
  SHARED
  ../src/vulkan_surface_backend.cpp
  ../src/android_vulkan_surface_probe.cpp
  ../src/android_native_activity.cpp
)

target_include_directories(
  shift_vulkan_android_native_activity
  PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/../include
)

target_compile_definitions(
  shift_vulkan_android_native_activity
  PRIVATE
  VK_USE_PLATFORM_ANDROID_KHR=1
)

target_compile_options(
  shift_vulkan_android_native_activity
  PRIVATE
  -Wall
  -Wextra
  -Wpedantic
)

target_link_libraries(
  shift_vulkan_android_native_activity
  PRIVATE
  shift_xbox_shader_translate
  ${SHIFT_ANDROID_LIB}
  ${SHIFT_LOG_LIB}
  ${SHIFT_VULKAN_LIB}
)

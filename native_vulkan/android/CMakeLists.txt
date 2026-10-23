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
target_include_directories(shift_xbox_draw_input PUBLIC ../include)
target_include_directories(shift_xbox_guest_ring PUBLIC ../include)
target_include_directories(shift_xbox_shader_translate PUBLIC ../include)
target_link_libraries(shift_xbox_guest_ring PUBLIC shift_xbox_draw_input)
target_link_libraries(shift_xbox_shader_translate PUBLIC shift_xbox_draw_input)

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

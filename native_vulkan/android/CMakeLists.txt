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
  ${SHIFT_ANDROID_LIB}
  ${SHIFT_LOG_LIB}
  ${SHIFT_VULKAN_LIB}
)

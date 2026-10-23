cmake_minimum_required(VERSION 3.25)
project(shift_rexglue_native_gpu LANGUAGES CXX)
option(SHIFT_REXGLUE_NATIVE_BUILD_TESTS "Build the native GPU plugin smoke test" ON)

set(SHIFT_REXGLUE_SDK_ROOT "" CACHE PATH "Path to the ReXGlue SDK checkout")
if(NOT SHIFT_REXGLUE_SDK_ROOT OR
   NOT EXISTS "${SHIFT_REXGLUE_SDK_ROOT}/CMakeLists.txt")
  message(FATAL_ERROR
    "Set SHIFT_REXGLUE_SDK_ROOT to a ReXGlue SDK checkout with rexui-vulkan")
endif()

set(REXGLUE_USE_VULKAN ON CACHE BOOL "Enable the ReXGlue Vulkan provider")
set(REXGLUE_USE_D3D12 OFF CACHE BOOL "Disable the ReXGlue D3D12 provider")
set(REXGLUE_BUILD_TESTS OFF CACHE BOOL "Disable ReXGlue SDK tests")

add_subdirectory(
  "${SHIFT_REXGLUE_SDK_ROOT}"
  "${CMAKE_BINARY_DIR}/rexglue-sdk"
  EXCLUDE_FROM_ALL
)
if(NOT TARGET rexui-vulkan OR NOT TARGET rexruntime)
  message(FATAL_ERROR "ReXGlue checkout must define rexui-vulkan and rexruntime")
endif()
get_target_property(SHIFT_REXGLUE_OUTPUT_DIRECTORY rexruntime LIBRARY_OUTPUT_DIRECTORY)

add_library(shift_guest_ring STATIC
  ../src/xbox_draw_input.cpp
  ../src/xbox_guest_ring.cpp
)
target_include_directories(shift_guest_ring PUBLIC ../include)
target_compile_features(shift_guest_ring PUBLIC cxx_std_17)

add_library(rexgpu-shift-native SHARED shift_native_gpu_plugin.cpp)
target_include_directories(rexgpu-shift-native PRIVATE
  "${SHIFT_REXGLUE_SDK_ROOT}/include"
  "${SHIFT_REXGLUE_SDK_ROOT}/thirdparty/renderdoc"
)
target_compile_features(rexgpu-shift-native PRIVATE cxx_std_23)
target_link_libraries(rexgpu-shift-native PRIVATE
  rexruntime
  rexui-vulkan
  shift_guest_ring
)
set_target_properties(rexgpu-shift-native PROPERTIES
  OUTPUT_NAME "rexgpu-shift-native"
  CXX_VISIBILITY_PRESET hidden
  VISIBILITY_INLINES_HIDDEN ON
)
if(SHIFT_REXGLUE_OUTPUT_DIRECTORY AND
   NOT SHIFT_REXGLUE_OUTPUT_DIRECTORY MATCHES "-NOTFOUND$")
  set_target_properties(rexgpu-shift-native PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${SHIFT_REXGLUE_OUTPUT_DIRECTORY}"
    RUNTIME_OUTPUT_DIRECTORY "${SHIFT_REXGLUE_OUTPUT_DIRECTORY}"
  )
endif()
if(COMMAND rex_config_postfix)
  rex_config_postfix(rexgpu-shift-native)
endif()

if(SHIFT_REXGLUE_NATIVE_BUILD_TESTS)
  enable_testing()
  add_executable(rexgpu_shift_native_factory_check factory_smoke.cpp)
  add_dependencies(rexgpu_shift_native_factory_check rexgpu-shift-native)
  target_include_directories(rexgpu_shift_native_factory_check PRIVATE
    "${SHIFT_REXGLUE_SDK_ROOT}/include"
  )
  target_compile_features(rexgpu_shift_native_factory_check PRIVATE cxx_std_23)
  target_link_libraries(rexgpu_shift_native_factory_check PRIVATE ${CMAKE_DL_LIBS})
  add_test(NAME rexgpu_shift_native_factory_check
    COMMAND rexgpu_shift_native_factory_check $<TARGET_FILE:rexgpu-shift-native>
  )
endif()

cmake_minimum_required(VERSION 3.25)
project(shift_rexglue_native_gpu LANGUAGES CXX)
option(SHIFT_REXGLUE_NATIVE_BUILD_TESTS "Build the native GPU plugin smoke test" ON)

set(SHIFT_REXGLUE_SDK_ROOT "" CACHE PATH "Path to the ReXGlue SDK checkout")
if(NOT SHIFT_REXGLUE_SDK_ROOT AND DEFINED REXSDK_DIR)
  set(SHIFT_REXGLUE_SDK_ROOT "${REXSDK_DIR}")
endif()
if(NOT SHIFT_REXGLUE_SDK_ROOT OR
   NOT EXISTS "${SHIFT_REXGLUE_SDK_ROOT}/CMakeLists.txt")
  message(FATAL_ERROR
    "Set SHIFT_REXGLUE_SDK_ROOT to a ReXGlue SDK checkout with rexui-vulkan")
endif()

if(NOT TARGET rexruntime)
  set(REXGLUE_USE_VULKAN ON CACHE BOOL "Enable the ReXGlue Vulkan provider")
  set(REXGLUE_USE_D3D12 OFF CACHE BOOL "Disable the ReXGlue D3D12 provider")
  set(REXGLUE_BUILD_TESTS OFF CACHE BOOL "Disable ReXGlue SDK tests")

  add_subdirectory(
    "${SHIFT_REXGLUE_SDK_ROOT}"
    "${CMAKE_BINARY_DIR}/rexglue-sdk"
    EXCLUDE_FROM_ALL
  )
endif()
if(NOT TARGET rexruntime)
  message(FATAL_ERROR "ReXGlue SDK was not added and has no rexruntime target")
elseif(TARGET rexui-vulkan)
  set(SHIFT_REXGLUE_VULKAN_PROVIDER_TARGET rexui-vulkan)
elseif(TARGET rexui AND ANDROID)
  # ReXGlue 0.10.0 keeps the Vulkan provider in rexruntime. Its older factory
  # cannot request geometryShader independently, so the plugin fails closed on
  # rectangle-list draws while keeping the native point-draw path available.
  set(SHIFT_REXGLUE_LEGACY_VULKAN_PROVIDER ON)
else()
  message(FATAL_ERROR "ReXGlue checkout must define rexui-vulkan")
endif()
find_package(Vulkan REQUIRED)
get_target_property(SHIFT_REXGLUE_OUTPUT_DIRECTORY rexruntime LIBRARY_OUTPUT_DIRECTORY)

add_library(shift_guest_ring STATIC
  ../src/xbox_draw_input.cpp
  ../src/xbox_guest_ring.cpp
)
target_include_directories(shift_guest_ring PUBLIC ../include)
target_compile_features(shift_guest_ring PUBLIC cxx_std_17)

add_library(shift_xbox_shader_translate STATIC ../src/xbox_shader_translate.cpp)
target_include_directories(shift_xbox_shader_translate PUBLIC ../include)
target_compile_features(shift_xbox_shader_translate PUBLIC cxx_std_17)
target_link_libraries(shift_xbox_shader_translate PUBLIC shift_guest_ring)

add_library(shift_xbox_live_vulkan_renderer STATIC ../src/xbox_live_vulkan_renderer.cpp)
target_include_directories(shift_xbox_live_vulkan_renderer PUBLIC ../include)
target_compile_features(shift_xbox_live_vulkan_renderer PUBLIC cxx_std_17)
target_link_libraries(shift_xbox_live_vulkan_renderer PUBLIC Vulkan::Vulkan)

add_library(rexgpu-shift-native SHARED shift_native_gpu_plugin.cpp)
target_sources(rexgpu-shift-native PRIVATE
  "${SHIFT_REXGLUE_SDK_ROOT}/thirdparty/glslang/StandAlone/ResourceLimits.cpp"
)
target_include_directories(rexgpu-shift-native PRIVATE
  "${SHIFT_REXGLUE_SDK_ROOT}/include"
  "${SHIFT_REXGLUE_SDK_ROOT}/thirdparty/renderdoc"
  "${SHIFT_REXGLUE_SDK_ROOT}/thirdparty/glslang"
)
target_compile_features(rexgpu-shift-native PRIVATE cxx_std_23)
target_link_libraries(rexgpu-shift-native PRIVATE
  rexruntime
  ${SHIFT_REXGLUE_VULKAN_PROVIDER_TARGET}
  shift_guest_ring
  shift_xbox_shader_translate
  shift_xbox_live_vulkan_renderer
  Vulkan::Vulkan
  glslang::SPIRV
  glslang
  MachineIndependent
  GenericCodeGen
  OSDependent
  OGLCompiler
)
if(SHIFT_REXGLUE_LEGACY_VULKAN_PROVIDER)
  target_compile_definitions(rexgpu-shift-native PRIVATE
    SHIFT_REXGLUE_LEGACY_VULKAN_PROVIDER=1
  )
endif()
set_target_properties(rexgpu-shift-native PROPERTIES
  OUTPUT_NAME "rexgpu-shift-native"
  DEBUG_POSTFIX "d"
  RELWITHDEBINFO_POSTFIX "rd"
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

  add_executable(rexgpu_shift_native_live_ring_check live_ring_smoke.cpp)
  add_dependencies(rexgpu_shift_native_live_ring_check rexgpu-shift-native)
  target_include_directories(rexgpu_shift_native_live_ring_check PRIVATE
    "${SHIFT_REXGLUE_SDK_ROOT}/include"
  )
  target_compile_features(rexgpu_shift_native_live_ring_check PRIVATE cxx_std_23)
  target_link_libraries(rexgpu_shift_native_live_ring_check PRIVATE
    rexruntime
    ${CMAKE_DL_LIBS}
  )
  add_test(NAME rexgpu_shift_native_live_ring_check
    COMMAND rexgpu_shift_native_live_ring_check $<TARGET_FILE:rexgpu-shift-native>
  )
  add_test(NAME rexgpu_shift_native_live_ring_readback_check
    COMMAND rexgpu_shift_native_live_ring_check $<TARGET_FILE:rexgpu-shift-native>
  )
  set_tests_properties(rexgpu_shift_native_live_ring_readback_check PROPERTIES
    ENVIRONMENT
      "SHIFT_NATIVE_VULKAN_DEBUG_FRAGMENT_COLOR=magenta;SHIFT_NATIVE_VULKAN_READBACK_PATH=${CMAKE_CURRENT_BINARY_DIR}/live-ring-diagnostic.a2b10g10r10"
  )
endif()

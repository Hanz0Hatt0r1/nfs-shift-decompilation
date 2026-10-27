cmake_minimum_required(VERSION 3.25)
project(shift_rexglue_native_gpu LANGUAGES CXX)
option(SHIFT_REXGLUE_NATIVE_BUILD_TESTS "Build the native GPU plugin smoke test" ON)
option(SHIFT_NATIVE_VULKAN_TRACE_RING_DEFAULT_ON
    "Enable the bounded guest ring trace when its environment flag is unavailable" OFF)
set(SHIFT_REXGLUE_PLUGIN_OUTPUT_DIR "" CACHE PATH
    "Optional isolated output directory for the native GPU plugin")
set(SHIFT_REXGLUE_PREBUILT_RUNTIME "" CACHE FILEPATH
    "Optional existing ReXGlue runtime shared library used instead of rebuilding it")
set(SHIFT_NATIVE_VULKAN_DEBUG_READBACK_FRAME "500" CACHE STRING
    "Submitted frame selected for the Android debug Vulkan readback")
set(SHIFT_NATIVE_VULKAN_DEBUG_READBACK_PATH "" CACHE FILEPATH
    "Optional file path for the Android debug Vulkan readback")
if(NOT SHIFT_NATIVE_VULKAN_DEBUG_READBACK_FRAME MATCHES "^[1-9][0-9]*$")
  message(FATAL_ERROR "SHIFT_NATIVE_VULKAN_DEBUG_READBACK_FRAME must be a positive integer")
endif()

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
  # ReXGlue 0.10.0 keeps the Vulkan provider in rexruntime.
else()
  message(FATAL_ERROR "ReXGlue checkout must define rexui-vulkan")
endif()
file(READ "${SHIFT_REXGLUE_SDK_ROOT}/include/rex/ui/vulkan/provider.h"
     SHIFT_REXGLUE_VULKAN_PROVIDER_HEADER)
if(SHIFT_REXGLUE_VULKAN_PROVIDER_HEADER MATCHES "bool with_geometry_shader")
  set(SHIFT_REXGLUE_OPTIONAL_GEOMETRY_SHADER_PROVIDER ON)
endif()
if(SHIFT_REXGLUE_VULKAN_PROVIDER_HEADER MATCHES "bool with_depth_stencil_resolve")
  set(SHIFT_REXGLUE_OPTIONAL_DEPTH_STENCIL_RESOLVE_PROVIDER ON)
endif()
if(SHIFT_REXGLUE_VULKAN_PROVIDER_HEADER MATCHES "bool with_sampler_anisotropy")
  set(SHIFT_REXGLUE_OPTIONAL_SAMPLER_ANISOTROPY_PROVIDER ON)
endif()
find_package(Vulkan REQUIRED)
get_target_property(SHIFT_REXGLUE_OUTPUT_DIRECTORY rexruntime LIBRARY_OUTPUT_DIRECTORY)
set(SHIFT_REXGLUE_PLUGIN_RUNTIME_TARGET rexruntime)
if(SHIFT_REXGLUE_PREBUILT_RUNTIME)
  if(NOT EXISTS "${SHIFT_REXGLUE_PREBUILT_RUNTIME}")
    message(FATAL_ERROR
      "SHIFT_REXGLUE_PREBUILT_RUNTIME does not exist: ${SHIFT_REXGLUE_PREBUILT_RUNTIME}")
  endif()
  add_library(shift_rexglue_prebuilt_runtime SHARED IMPORTED GLOBAL)
  set_target_properties(shift_rexglue_prebuilt_runtime PROPERTIES
    IMPORTED_LOCATION "${SHIFT_REXGLUE_PREBUILT_RUNTIME}"
  )
  set(SHIFT_REXGLUE_PLUGIN_RUNTIME_TARGET shift_rexglue_prebuilt_runtime)
endif()
if(SHIFT_REXGLUE_PLUGIN_OUTPUT_DIR)
  set(SHIFT_REXGLUE_OUTPUT_DIRECTORY "${SHIFT_REXGLUE_PLUGIN_OUTPUT_DIR}")
endif()

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
target_compile_definitions(rexgpu-shift-native PRIVATE
  SHIFT_NATIVE_VULKAN_DEBUG_READBACK_FRAME=${SHIFT_NATIVE_VULKAN_DEBUG_READBACK_FRAME}
)
if(SHIFT_NATIVE_VULKAN_TRACE_RING_DEFAULT_ON)
  target_compile_definitions(rexgpu-shift-native PRIVATE
    SHIFT_NATIVE_VULKAN_TRACE_RING_DEFAULT_ON=1
  )
endif()
if(SHIFT_REXGLUE_OPTIONAL_SAMPLER_ANISOTROPY_PROVIDER)
  target_compile_definitions(rexgpu-shift-native PRIVATE
    SHIFT_REXGLUE_OPTIONAL_SAMPLER_ANISOTROPY_PROVIDER
  )
endif()
if(SHIFT_NATIVE_VULKAN_DEBUG_READBACK_PATH)
  target_compile_definitions(rexgpu-shift-native PRIVATE
    SHIFT_NATIVE_VULKAN_DEBUG_READBACK_PATH="${SHIFT_NATIVE_VULKAN_DEBUG_READBACK_PATH}"
  )
endif()
target_sources(rexgpu-shift-native PRIVATE
  "${SHIFT_REXGLUE_SDK_ROOT}/thirdparty/glslang/StandAlone/ResourceLimits.cpp"
)
target_include_directories(rexgpu-shift-native PRIVATE
  "${SHIFT_REXGLUE_SDK_ROOT}/include"
  "${SHIFT_REXGLUE_SDK_ROOT}/thirdparty/renderdoc"
  "${SHIFT_REXGLUE_SDK_ROOT}/thirdparty/glslang"
)
if(SHIFT_REXGLUE_PREBUILT_RUNTIME)
  target_include_directories(rexgpu-shift-native SYSTEM PRIVATE
    "${SHIFT_REXGLUE_SDK_ROOT}/thirdparty/fmt/include"
    "${SHIFT_REXGLUE_SDK_ROOT}/thirdparty/spdlog/include"
    "${SHIFT_REXGLUE_SDK_ROOT}/thirdparty/simde"
    "${SHIFT_REXGLUE_SDK_ROOT}/thirdparty/vulkan-headers/include"
  )
endif()
target_compile_features(rexgpu-shift-native PRIVATE cxx_std_23)
target_link_libraries(rexgpu-shift-native PRIVATE
  ${SHIFT_REXGLUE_PLUGIN_RUNTIME_TARGET}
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
if(ANDROID AND SHIFT_REXGLUE_OPTIONAL_DEPTH_STENCIL_RESOLVE_PROVIDER)
  # This provider is embedded in the plugin while Android's librexruntime may
  # still export the older VulkanProvider implementation. Keep the embedded
  # provider's vtables and calls bound to this DSO instead of allowing ELF
  # interposition to route them through the runtime's older definitions.
  target_link_options(rexgpu-shift-native PRIVATE "LINKER:-Bsymbolic")
endif()
if(SHIFT_REXGLUE_OPTIONAL_GEOMETRY_SHADER_PROVIDER)
  target_compile_definitions(rexgpu-shift-native PRIVATE
    SHIFT_REXGLUE_OPTIONAL_GEOMETRY_SHADER_PROVIDER=1
  )
endif()
if(SHIFT_REXGLUE_OPTIONAL_DEPTH_STENCIL_RESOLVE_PROVIDER)
  target_compile_definitions(rexgpu-shift-native PRIVATE
    SHIFT_REXGLUE_OPTIONAL_DEPTH_STENCIL_RESOLVE_PROVIDER=1
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
  add_executable(rexgpu_shift_native_r8_upload_scratch_check
    r8_upload_scratch_check.cpp
  )
  target_compile_features(rexgpu_shift_native_r8_upload_scratch_check PRIVATE cxx_std_17)
  add_test(NAME rexgpu_shift_native_r8_upload_scratch_check
    COMMAND rexgpu_shift_native_r8_upload_scratch_check
  )

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
  set_tests_properties(rexgpu_shift_native_live_ring_check PROPERTIES
    ENVIRONMENT "SHIFT_NATIVE_VULKAN_TRACE_RING=0"
  )
  add_test(NAME rexgpu_shift_native_live_ring_write_trace_check
    COMMAND rexgpu_shift_native_live_ring_check $<TARGET_FILE:rexgpu-shift-native>
  )
  set_tests_properties(rexgpu_shift_native_live_ring_write_trace_check PROPERTIES
    ENVIRONMENT "SHIFT_NATIVE_VULKAN_TRACE_RING=1"
  )
  add_test(NAME rexgpu_shift_native_live_ring_selected_draw_dump_check
    COMMAND rexgpu_shift_native_live_ring_check $<TARGET_FILE:rexgpu-shift-native>
  )
  set_tests_properties(rexgpu_shift_native_live_ring_selected_draw_dump_check PROPERTIES
    ENVIRONMENT
      "SHIFT_NATIVE_VULKAN_DUMP_DRAW_FRAME=1;SHIFT_NATIVE_VULKAN_DUMP_GEOMETRY_PREFIX=${CMAKE_CURRENT_BINARY_DIR}/live-ring-geometry-dump;SHIFT_NATIVE_VULKAN_DUMP_TEXTURES_PREFIX=${CMAKE_CURRENT_BINARY_DIR}/live-ring-texture-dump;SHIFT_NATIVE_VULKAN_DUMP_TEXTURE_SOURCE_PREFIX=${CMAKE_CURRENT_BINARY_DIR}/live-ring-texture-source-dump;SHIFT_NATIVE_VULKAN_DUMP_TEXTURE_SOURCE_GUEST_ADDRESS=0x09D57000"
  )
  add_test(NAME rexgpu_shift_native_live_ring_readback_check
    COMMAND rexgpu_shift_native_live_ring_check $<TARGET_FILE:rexgpu-shift-native>
  )
  set_tests_properties(rexgpu_shift_native_live_ring_readback_check PROPERTIES
    ENVIRONMENT
      "SHIFT_NATIVE_VULKAN_DEBUG_FRAGMENT_COLOR=magenta;SHIFT_NATIVE_VULKAN_READBACK_PATH=${CMAKE_CURRENT_BINARY_DIR}/live-ring-diagnostic.a2b10g10r10;SHIFT_NATIVE_VULKAN_READBACK_FRAME=2"
  )
  if(SHIFT_REXGLUE_OPTIONAL_DEPTH_STENCIL_RESOLVE_PROVIDER)
    add_executable(rexgpu_vulkan_resolve_capability_check resolve_capability_check.cpp)
    target_include_directories(rexgpu_vulkan_resolve_capability_check PRIVATE
      "${SHIFT_REXGLUE_SDK_ROOT}/include"
      "${SHIFT_REXGLUE_SDK_ROOT}/thirdparty/renderdoc"
    )
    target_compile_features(rexgpu_vulkan_resolve_capability_check PRIVATE cxx_std_23)
    target_link_libraries(rexgpu_vulkan_resolve_capability_check PRIVATE
      ${SHIFT_REXGLUE_PLUGIN_RUNTIME_TARGET}
      ${SHIFT_REXGLUE_VULKAN_PROVIDER_TARGET}
    )
    add_test(NAME rexgpu_vulkan_resolve_capability_check
      COMMAND rexgpu_vulkan_resolve_capability_check
    )
  endif()
  if(SHIFT_REXGLUE_OPTIONAL_SAMPLER_ANISOTROPY_PROVIDER)
    target_sources(rexgpu-shift-native PRIVATE sampler_anisotropy_check.cpp)
    if(NOT ANDROID)
      add_test(NAME rexgpu_vulkan_sampler_anisotropy_check
        COMMAND rexgpu_shift_native_factory_check
          $<TARGET_FILE:rexgpu-shift-native> --sampler-anisotropy
      )
    endif()
  endif()
endif()

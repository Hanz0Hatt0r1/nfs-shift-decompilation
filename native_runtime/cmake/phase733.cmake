# Single-process S6 Phase 733: recover the PC retail HDVehicle+0x120
# FUN_007675f0 surface-probe node cache and its +0x128/+0x130/+0x138
# refresh-position policy while keeping FUN_00717cd0 lookup behavior external.

add_executable(shift_runtime_fun_007675f0_surface_probe_node_cache_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007675f0_surface_probe_node_cache_check.cpp)
target_include_directories(
  shift_runtime_fun_007675f0_surface_probe_node_cache_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_007675f0_surface_probe_node_cache_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_007675f0_surface_probe_node_cache_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_007675f0_surface_probe_node_cache
    COMMAND shift_runtime_fun_007675f0_surface_probe_node_cache_check)
endif()

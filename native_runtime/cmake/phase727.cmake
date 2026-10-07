# Single-process S6 Phase 727: prove and implement the exact PC retail
# FUN_00765c40 local-sample -> chassis BODY0 world-position transform.
# The HDVehicle+0x3938 local-sample producer and the per-pass BODY snapshot join
# remain separate external/runtime boundaries.

target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/fun_00765c40_world_position_transform.cpp)

add_executable(shift_runtime_fun_00765c40_world_position_transform_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00765c40_world_position_transform_check.cpp)
target_include_directories(
  shift_runtime_fun_00765c40_world_position_transform_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(
  shift_runtime_fun_00765c40_world_position_transform_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00765c40_world_position_transform_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00765c40_world_position_transform
    COMMAND shift_runtime_fun_00765c40_world_position_transform_check)
endif()

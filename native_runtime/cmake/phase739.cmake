# Single-process S6 Phase 739: compose the selected BMW FUN_00765c40 query
# world position from current persistent BODY3/BODY4 -> Phase728 -> Phase727.

add_executable(shift_runtime_fun_00765c40_selected_bmw_world_position_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00765c40_selected_bmw_world_position_check.cpp)
target_include_directories(
  shift_runtime_fun_00765c40_selected_bmw_world_position_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00765c40_selected_bmw_world_position_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00765c40_selected_bmw_world_position_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00765c40_selected_bmw_world_position
    COMMAND shift_runtime_fun_00765c40_selected_bmw_world_position_check)
endif()

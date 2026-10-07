# Single-process S6 Phase 726: type and capture the source-backed FUN_00765c40
# input consumed by the already-native FUN_007b0710 query-record materializer.
# The world-position producer and collision-provider implementation stay external.

add_executable(shift_runtime_fun_00765c40_query_input_boundary_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00765c40_query_input_boundary_check.cpp)
target_include_directories(
  shift_runtime_fun_00765c40_query_input_boundary_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(
  shift_runtime_fun_00765c40_query_input_boundary_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00765c40_query_input_boundary_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00765c40_query_input_boundary
    COMMAND shift_runtime_fun_00765c40_query_input_boundary_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase727.cmake)

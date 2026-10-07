# Single-process S6 Phase 732: replace production planar_delta/surface_scalar
# inputs with the earlier source-backed FUN_00759210 node boundary, deriving
# current BODY0 query position and both probe outputs natively per pass.

add_executable(shift_runtime_fun_007675f0_surface_probe_join_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007675f0_surface_probe_join_check.cpp)
target_include_directories(
  shift_runtime_fun_007675f0_surface_probe_join_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_007675f0_surface_probe_join_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_007675f0_surface_probe_join_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_007675f0_surface_probe_join
    COMMAND shift_runtime_fun_007675f0_surface_probe_join_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase733.cmake)

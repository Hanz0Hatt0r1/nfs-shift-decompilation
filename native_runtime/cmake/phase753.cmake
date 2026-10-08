# Single-process S6 Phase 753: consume the closed Process 1 inventory of all
# direct FUN_00753650 caller-accumulator sites without collapsing unresolved
# interleaved auxiliary/final accumulator contributions.

add_executable(shift_runtime_fun_00766510_direct_accumulator_surface_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00766510_direct_accumulator_surface_check.cpp)
target_include_directories(
  shift_runtime_fun_00766510_direct_accumulator_surface_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00766510_direct_accumulator_surface_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00766510_direct_accumulator_surface_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00766510_direct_accumulator_surface
    COMMAND shift_runtime_fun_00766510_direct_accumulator_surface_check)
endif()

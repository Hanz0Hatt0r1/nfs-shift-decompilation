# Single-process S6 Phase 748: internalize the FUN_00712940 three-record
# aggregate and FUN_00713630 participant reference-source writer while keeping
# its earlier dynamic participant/config materialization explicit.

add_executable(shift_runtime_fun_00713630_reference_source_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00713630_reference_source_check.cpp)
target_include_directories(
  shift_runtime_fun_00713630_reference_source_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00713630_reference_source_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00713630_reference_source_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00713630_reference_source
    COMMAND shift_runtime_fun_00713630_reference_source_check)
endif()

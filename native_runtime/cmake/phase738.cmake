# Single-process S6 Phase 738: prove FUN_007618f0 param_2 as VehicleLoadData
# and freeze the selected BMW E36 +0x338/+0x918 source inputs.

add_executable(shift_runtime_fun_007618f0_selected_bmw_source_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007618f0_selected_bmw_source_check.cpp)
target_include_directories(
  shift_runtime_fun_007618f0_selected_bmw_source_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_007618f0_selected_bmw_source_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_007618f0_selected_bmw_source_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_007618f0_selected_bmw_source
    COMMAND shift_runtime_fun_007618f0_selected_bmw_source_check)
endif()

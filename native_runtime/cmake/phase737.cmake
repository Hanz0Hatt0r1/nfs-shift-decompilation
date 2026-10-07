# Single-process S6 Phase 737: own the two pointer-backed FUN_007618f0
# wheel BODY origin inputs from selected BMW persistent BODY state.

add_executable(shift_runtime_fun_007618f0_wheel_body_origin_ownership_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007618f0_wheel_body_origin_ownership_check.cpp)
target_include_directories(
  shift_runtime_fun_007618f0_wheel_body_origin_ownership_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_007618f0_wheel_body_origin_ownership_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_007618f0_wheel_body_origin_ownership_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_007618f0_wheel_body_origin_ownership
    COMMAND shift_runtime_fun_007618f0_wheel_body_origin_ownership_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase738.cmake)

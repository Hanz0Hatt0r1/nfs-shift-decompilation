# Single-process S6 Phase 745: thread the selected same-pass FUN_00765c40
# collision output and Phase743 application point into residual FUN_00766510.

add_executable(shift_runtime_fun_00766510_same_pass_handoff_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00766510_same_pass_handoff_check.cpp)
target_include_directories(
  shift_runtime_fun_00766510_same_pass_handoff_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00766510_same_pass_handoff_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00766510_same_pass_handoff_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00766510_same_pass_handoff
    COMMAND shift_runtime_fun_00766510_same_pass_handoff_check)
endif()

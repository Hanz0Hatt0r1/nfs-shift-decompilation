# Single-process S6 Phase 745: thread the selected BMW FUN_00765c40 collision
# output, native +0x38e0/+0x38e8 scalar handoff, and Phase743 +0x38f0 point
# into the still-external FUN_00766510 remainder at the recovered anchor order.

add_executable(shift_runtime_fun_00766510_session_handoff_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00766510_session_handoff_check.cpp)
target_include_directories(
  shift_runtime_fun_00766510_session_handoff_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00766510_session_handoff_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00766510_session_handoff_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00766510_session_handoff
    COMMAND shift_runtime_fun_00766510_session_handoff_check)
endif()

# Single-process S6 Phase 749: consume the Process 1 later-response ownership
# contract by internalizing FUN_00756b10 persistent derived state and the
# mandatory +0x3ac0/+0x3ac8 sixth-table-entry runtime materialization.

add_executable(shift_runtime_fun_00766510_later_response_branch_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00766510_later_response_branch_check.cpp)
target_include_directories(
  shift_runtime_fun_00766510_later_response_branch_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00766510_later_response_branch_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00766510_later_response_branch_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00766510_later_response_branch
    COMMAND shift_runtime_fun_00766510_later_response_branch_check)
endif()

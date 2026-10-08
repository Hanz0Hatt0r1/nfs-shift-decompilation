# Single-process S6 Phase 752: consume the Process 1 response-config ownership
# contract by internalizing setup-owned +0x3910/+0x3918/+0x3950 and exact
# FUN_00756ac0 +0x3908 derived-state refresh.

add_executable(shift_runtime_fun_00766510_response_config_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00766510_response_config_check.cpp)
target_include_directories(
  shift_runtime_fun_00766510_response_config_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00766510_response_config_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00766510_response_config_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00766510_response_config
    COMMAND shift_runtime_fun_00766510_response_config_check)
endif()

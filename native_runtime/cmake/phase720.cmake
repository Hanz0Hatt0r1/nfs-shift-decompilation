# Single-process S6 Phase 720: internalize the PC FUN_007594e0 ->
# HDVehicle+0x4068 steering producer executed by FUN_0076f970 before both
# FUN_00770e80 physics passes.

target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/fun_007594e0_machine_angle.cpp)

add_executable(shift_runtime_fun_007594e0_machine_angle_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007594e0_machine_angle_check.cpp)
target_include_directories(
  shift_runtime_fun_007594e0_machine_angle_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(
  shift_runtime_fun_007594e0_machine_angle_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_007594e0_machine_angle_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_fun_007594e0_session_angle_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007594e0_session_angle_check.cpp)
target_include_directories(
  shift_runtime_fun_007594e0_session_angle_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_007594e0_session_angle_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_007594e0_session_angle_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_007594e0_machine_angle
    COMMAND shift_runtime_fun_007594e0_machine_angle_check)
  add_test(
    NAME shift_runtime_fun_007594e0_session_angle
    COMMAND shift_runtime_fun_007594e0_session_angle_check)
endif()

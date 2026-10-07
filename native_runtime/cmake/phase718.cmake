# Single-process S6 Phase 718: consume exact PC FUN_007682c0 machine arithmetic
# from raw retail inputs while retaining historical Phase 696 effect-provider
# interfaces for compatibility/regression history.

target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/fun_007682c0_machine_effect.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/fun_00770e80_motion_read_machine_input_provider_chain.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/runtime_motion_read_machine_input_state.cpp)

add_executable(shift_runtime_fun_007682c0_machine_effect_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007682c0_machine_effect_check.cpp)
target_include_directories(
  shift_runtime_fun_007682c0_machine_effect_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_007682c0_machine_effect_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_007682c0_machine_effect_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_007682c0_machine_effect
    COMMAND shift_runtime_fun_007682c0_machine_effect_check)
endif()

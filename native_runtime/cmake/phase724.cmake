# Single-process S6 Phase 724: prove DAT_00c128cc is RaceModeInfo+0x6c
# Player Difficulty, bind the selected native-session selector, and remove the
# final top-level FUN_007682c0 raw-input provider.

add_executable(shift_runtime_dat_00c128cc_player_difficulty_ownership_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/dat_00c128cc_player_difficulty_ownership_check.cpp)
target_include_directories(
  shift_runtime_dat_00c128cc_player_difficulty_ownership_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(
  shift_runtime_dat_00c128cc_player_difficulty_ownership_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_dat_00c128cc_player_difficulty_ownership_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_dat_00c128cc_player_difficulty_ownership
    COMMAND shift_runtime_dat_00c128cc_player_difficulty_ownership_check)
endif()

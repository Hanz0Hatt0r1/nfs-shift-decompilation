# Single-process S6 Phase 747: close ownership and exact transform of the shared
# FUN_00766510 local_d8/local_d0/local_c8 reference vector while leaving its
# dynamic actual-participant source state unscheduled.

add_executable(shift_runtime_fun_00766510_shared_reference_vector_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00766510_shared_reference_vector_check.cpp)
target_include_directories(
  shift_runtime_fun_00766510_shared_reference_vector_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00766510_shared_reference_vector_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00766510_shared_reference_vector_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00766510_shared_reference_vector
    COMMAND shift_runtime_fun_00766510_shared_reference_vector_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase748.cmake)

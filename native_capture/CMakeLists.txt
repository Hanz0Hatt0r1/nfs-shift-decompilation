cmake_minimum_required(VERSION 3.16)
project(shift_d3d9_capture LANGUAGES CXX)

if(WIN32)
  add_library(shift_d3d9_capture SHARED src/d3d9_trace_proxy.cpp)
  target_compile_features(shift_d3d9_capture PRIVATE cxx_std_17)
  target_include_directories(shift_d3d9_capture PRIVATE include)
  target_link_libraries(shift_d3d9_capture PRIVATE d3d9)
  set_target_properties(shift_d3d9_capture PROPERTIES OUTPUT_NAME "shift_d3d9_capture")
else()
  add_custom_target(shift_d3d9_capture
    COMMENT "SHIFT D3D9 capture proxy is Windows-only")
endif()
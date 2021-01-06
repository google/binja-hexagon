add_library(interval_map
  INTERFACE
)

add_executable(interval_map_test
  interval_map_unittest.cc
)

target_link_libraries(interval_map_test
  interval_map
  gmock
  glog
  gtest_main
  absl::base
  absl::strings
  absl::str_format
)

add_test(interval_map_test interval_map_test)
add_dependencies(check interval_map_test)

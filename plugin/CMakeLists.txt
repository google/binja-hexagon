# Copyright (C) 2020 Google LLC
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

# Generate insn text funcs.
set(INSN_TEXT_FUNCS_CC  ${CMAKE_CURRENT_BINARY_DIR}/insn_text_funcs_generated.cc)
add_custom_command(
  OUTPUT ${INSN_TEXT_FUNCS_CC}
  COMMAND PYTHONPATH=${CMAKE_SOURCE_DIR}/third_party/qemu-hexagon ${CMAKE_CURRENT_SOURCE_DIR}/gen_insn_text_funcs.py ${SEMANTICS} ${CMAKE_SOURCE_DIR}/third_party/qemu-hexagon/attribs_def.h ${INSN_TEXT_FUNCS_CC}
  COMMAND clang-format -i ${INSN_TEXT_FUNCS_CC} || (exit 0)
  DEPENDS gen_insn_text_funcs.py ${CMAKE_SOURCE_DIR}/third_party/qemu-hexagon/hex_common.py ${SEMANTICS} ${CMAKE_SOURCE_DIR}/third_party/qemu-hexagon/attribs_def.h
)

add_custom_target(gen_insn_text_funcs
  DEPENDS ${INSN_TEXT_FUNCS_CC}
)

add_dependencies(gen_insn_text_funcs
  hexagon_generated_headers_deps
)

add_test(NAME gen_insn_text_funcs_test
  COMMAND python3 gen_insn_text_funcs_test.py
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)
set_tests_properties(gen_insn_text_funcs_test PROPERTIES
  ENVIRONMENT PYTHONPATH=${CMAKE_SOURCE_DIR}/third_party/qemu-hexagon
)

# Generate il funcs.
set(IL_FUNCS_CC   ${CMAKE_CURRENT_BINARY_DIR}/il_funcs_generated.cc)
add_custom_command(
  OUTPUT ${IL_FUNCS_CC}
  COMMAND PYTHONPATH=${CMAKE_SOURCE_DIR}/third_party/qemu-hexagon ${CMAKE_CURRENT_SOURCE_DIR}/gen_il_funcs.py ${SEMANTICS} ${CMAKE_SOURCE_DIR}/third_party/qemu-hexagon/attribs_def.h ${IL_FUNCS_CC}
  COMMAND clang-format -i ${IL_FUNCS_CC} || (exit 0)
  DEPENDS gen_il_funcs.py gen_il_funcs_data.py ${CMAKE_SOURCE_DIR}/third_party/qemu-hexagon/hex_common.py ${SEMANTICS} ${CMAKE_SOURCE_DIR}/third_party/qemu-hexagon/attribs_def.h
)

add_custom_target(gen_il_funcs
  DEPENDS ${IL_FUNCS_CC}
)

add_dependencies(gen_il_funcs
  hexagon_generated_headers_deps
)

add_test(NAME gen_il_funcs_test
  COMMAND python3 gen_il_funcs_test.py
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)
set_tests_properties(gen_il_funcs_test PROPERTIES
  ENVIRONMENT PYTHONPATH=${CMAKE_SOURCE_DIR}/third_party/qemu-hexagon
)

add_library(plugin_lib
  ${INSN_TEXT_FUNCS_CC}
  ${IL_FUNCS_CC}
  decoder.cc
  il_util.cc
  insn_util.cc
  packet_context.cc
  packet_db.cc
  text_util.cc
)


target_link_libraries(plugin_lib
  binaryninjaapi
  interval_map
  decoder_c_lib
  absl::base
  absl::strings
  absl::statusor
  absl::synchronization
  glog
)

target_include_directories(plugin_lib
  PRIVATE
  ${CMAKE_CURRENT_BINARY_DIR}
)

function (add_plugin_test name)
  add_executable(${name}
    ${name}.cc
  )

  target_link_libraries(${name}
    plugin_lib
    gmock
    gtest_main
    absl::base
    absl::strings
  )

  add_test(${name} ${name})
  add_dependencies(check ${name})
endfunction()

add_plugin_test(decoder_test)
add_plugin_test(packet_db_test)
add_plugin_test(il_util_test)
add_plugin_test(insn_util_test)

add_library(arch_hexagon SHARED
  arch_hexagon.cc
)

target_link_libraries(arch_hexagon
  plugin_lib
  binaryninjaapi
)

set_target_properties(arch_hexagon PROPERTIES
  CXX_STANDARD 17
  CXX_VISIBILITY_PRESET hidden
  CXX_STANDARD_REQUIRED ON
  C_STANDARD 99
  C_STANDARD_REQUIRED ON
  C_VISIBILITY_PRESET hidden
  VISIBILITY_INLINES_HIDDEN ON
  POSITION_INDEPENDENT_CODE ON
)

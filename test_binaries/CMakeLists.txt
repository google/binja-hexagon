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

if(NOT EXISTS ${HEXAGON_SDK_TOOLS_DIR})
  message(STATUS "SDK directory '${HEXAGON_SDK_TOOLS_DIR}' does not exist, not building test binaries, and using prebuilt instead.")

  add_test(NAME bn_llil_test
    COMMAND python3 bn_llil_test.py
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )
  set_tests_properties(bn_llil_test PROPERTIES
    ENVIRONMENT "PYTHONPATH=${BN_INSTALL_DIR}/python;TEST_TARGET_FILE=${CMAKE_CURRENT_SOURCE_DIR}/prebuilt/bn_llil_test_app"
  )
else()
  set(CMAKE_ASM_COMPILER "${HEXAGON_CLANG_C}")
  set(CMAKE_C_COMPILER "${HEXAGON_CLANG_C}")
  set(CMAKE_CXX_COMPILER "${HEXAGON_CLANG_CXX}")
  set(CMAKE_ASM_FLAGS "-mv67 -O2 -mhvx -Wall")
  set(CMAKE_C_FLAGS "-mv67 -O2 -mhvx -Wall")
  set(CMAKE_CXX_FLAGS "-mv67 -O2 -mhvx -Wall")

  function (add_asm_test name)
    add_executable(${name}
      first.s
      ${name}.s
    )
    set_target_properties(${name}
      PROPERTIES LINK_FLAGS "-static -nostdlib -Wl,-e,start"
    )
  endfunction()

  add_asm_test(bn_llil_test_app)

  add_test(NAME bn_llil_test
    COMMAND python3 bn_llil_test.py
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )
  set_tests_properties(bn_llil_test PROPERTIES
    ENVIRONMENT "PYTHONPATH=${BN_INSTALL_DIR}/python;TEST_TARGET_FILE=$<TARGET_FILE:bn_llil_test_app>"
  )

  add_executable(bn_hlil_test_app bn_hlil_test_app.c)

  add_test(NAME bn_hlil_test
    COMMAND python3 bn_hlil_test.py
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )
  set_tests_properties(bn_hlil_test PROPERTIES
    ENVIRONMENT "PYTHONPATH=${BN_INSTALL_DIR}/python;TEST_TARGET_FILE=$<TARGET_FILE:bn_hlil_test_app>"
  )

endif()

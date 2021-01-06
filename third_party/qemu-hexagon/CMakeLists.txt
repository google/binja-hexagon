#
#  Step 1
#  We use a C program to create semantics_generated.pyinc
#
add_executable(gen_semantics
  gen_semantics.c
)

set(SEMANTICS ${CMAKE_CURRENT_BINARY_DIR}/semantics_generated.pyinc)
set(SEMANTICS ${SEMANTICS} PARENT_SCOPE)
add_custom_command(
  OUTPUT ${SEMANTICS}
  COMMAND $<TARGET_FILE:gen_semantics> ${SEMANTICS}
)

#
# Step 2
# We use Python scripts to generate the following files
#
set(OPCODES_DEF_H    ${CMAKE_CURRENT_BINARY_DIR}/opcodes_def_generated.h)
set(OP_REGS_H        ${CMAKE_CURRENT_BINARY_DIR}/op_regs_generated.h)
set(OP_ATTRIBS_H     ${CMAKE_CURRENT_BINARY_DIR}/op_attribs_generated.h)
set(SHORTCODE_H      ${CMAKE_CURRENT_BINARY_DIR}/shortcode_generated.h)

add_custom_command(
  OUTPUT ${OPCODES_DEF_H}
  COMMAND python3 gen_opcodes_def.py ${SEMANTICS} attribs_def.h ${OPCODES_DEF_H}
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  DEPENDS hex_common.py gen_opcodes_def.py ${SEMANTICS} attribs_def.h
)

add_custom_command(
  OUTPUT ${OP_REGS_H}
  COMMAND python3 gen_op_regs.py ${SEMANTICS} attribs_def.h ${OP_REGS_H}
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  DEPENDS hex_common.py gen_op_regs.py ${SEMANTICS} attribs_def.h
)

add_custom_command(
  OUTPUT ${OP_ATTRIBS_H}
  COMMAND python3 gen_op_attribs.py ${SEMANTICS} attribs_def.h ${OP_ATTRIBS_H}
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  DEPENDS hex_common.py gen_op_attribs.py ${SEMANTICS} attribs_def.h
)

add_custom_command(
  OUTPUT ${SHORTCODE_H}
  COMMAND python3 gen_shortcode.py ${SEMANTICS} attribs_def.h ${SHORTCODE_H}
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  DEPENDS hex_common.py gen_shortcode.py ${SEMANTICS} attribs_def.h
)

#
# Step 3
# We use a C program to create iset.py which is imported into dectree.py
# to create the decode tree
#

add_executable(gen_dectree_import
  gen_dectree_import.c
)

target_include_directories(gen_dectree_import
  PRIVATE
  ${CMAKE_CURRENT_BINARY_DIR}
)

add_custom_target(gen_opcodes_def_h
  DEPENDS ${OPCODES_DEF_H} ${OP_REGS_H}
)
add_dependencies(gen_dectree_import
  gen_opcodes_def_h
)

set(DECTREE_IMPORT ${CMAKE_CURRENT_BINARY_DIR}/iset.py)
add_custom_command(
  OUTPUT ${DECTREE_IMPORT}
  COMMAND $<TARGET_FILE:gen_dectree_import> ${DECTREE_IMPORT}
)

#
# Step 4
# We use the dectree.py script to generate the decode tree header file
#
set(DECTREE_HEADER ${CMAKE_CURRENT_BINARY_DIR}/dectree_generated.h)
add_custom_command(
  OUTPUT ${DECTREE_HEADER}
  COMMAND PYTHONPATH=${CMAKE_CURRENT_BINARY_DIR} python3 dectree.py ${DECTREE_HEADER}
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  DEPENDS dectree.py ${DECTREE_IMPORT}
)


#
# Special deps and interface targets.
#
set(GENERATED_HEXAGON_FILES
  ${OPCODES_DEF_H}
  ${OP_REGS_H}
  ${OP_ATTRIBS_H}
  ${SHORTCODE_H}
  ${DECTREE_HEADER}
)

add_custom_target(hexagon_generated_headers_deps
  DEPENDS ${GENERATED_HEXAGON_FILES}
)

add_library(hexagon_generated_headers_interface
  INTERFACE
)

target_include_directories(hexagon_generated_headers_interface
  INTERFACE
  ${CMAKE_CURRENT_BINARY_DIR}
)

#
# Decoder library.
#
add_library(decoder_c_lib
  decode_ext_mmvec.c
  decode.c
  iclass.c
  opcodes.c
  reg_fields.c
)

target_link_libraries(decoder_c_lib
  hexagon_generated_headers_interface
)

add_dependencies(decoder_c_lib
  hexagon_generated_headers_deps
)


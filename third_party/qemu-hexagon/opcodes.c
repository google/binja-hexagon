/*
 *  Copyright(c) 2019-2020 Qualcomm Innovation Center, Inc. All Rights Reserved.
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, see <http://www.gnu.org/licenses/>.
 */

/*
 * opcodes.c
 *
 * data tables generated automatically
 * Maybe some functions too
 */

#include "third_party/qemu-hexagon/opcodes.h"

#include <ctype.h>
#include <setjmp.h>
#include <stdarg.h>
#include <string.h>

#include "third_party/qemu-hexagon/decode.h"

extern __thread jmp_buf decode_jmp_buf;
#define ASSERT_AND_ABORT(condition)                                            \
  if (!(condition)) {                                                          \
    longjmp(decode_jmp_buf, 1);                                                \
  }

#define VEC_DESCR(A, B, C) DESCR(A, B, C)
#define DONAME(X) #X

const char *const opcode_names[] = {
#define OPCODE(IID) DONAME(IID)
#include "opcodes_def_generated.h"
    NULL
#undef OPCODE
};

const char *const opcode_reginfo[] = {
#define IMMINFO(TAG, SIGN, SIZE, SHAMT, SIGN2, SIZE2, SHAMT2) /* nothing */
#define REGINFO(TAG, REGINFO, RREGS, WREGS) REGINFO,
#include "op_regs_generated.h"
    NULL
#undef REGINFO
#undef IMMINFO
};

const char *const opcode_rregs[] = {
#define IMMINFO(TAG, SIGN, SIZE, SHAMT, SIGN2, SIZE2, SHAMT2) /* nothing */
#define REGINFO(TAG, REGINFO, RREGS, WREGS) RREGS,
#include "op_regs_generated.h"
    NULL
#undef REGINFO
#undef IMMINFO
};

const char *const opcode_wregs[] = {
#define IMMINFO(TAG, SIGN, SIZE, SHAMT, SIGN2, SIZE2, SHAMT2) /* nothing */
#define REGINFO(TAG, REGINFO, RREGS, WREGS) WREGS,
#include "op_regs_generated.h"
    NULL
#undef REGINFO
#undef IMMINFO
};

const char *const opcode_short_semantics[] = {
#define DEF_SHORTCODE(TAG, SHORTCODE) [TAG] = #SHORTCODE,
#include "shortcode_generated.h"
#undef DEF_SHORTCODE
    NULL};

DECLARE_BITMAP(opcode_attribs[XX_LAST_OPCODE], A_ZZ_LASTATTRIB);

static void init_attribs(int tag, ...) {
  va_list ap;
  int attr;
  va_start(ap, tag);
  while ((attr = va_arg(ap, int)) != 0) {
    set_bit(attr, opcode_attribs[tag]);
  }
}

const OpcodeEncoding opcode_encodings[] = {
#define DEF_ENC32(OPCODE, ENCSTR) [OPCODE] = {.encoding = ENCSTR},

#define DEF_ENC_SUBINSN(OPCODE, CLASS, ENCSTR)                                 \
  [OPCODE] = {.encoding = ENCSTR, .enc_class = CLASS},

#define DEF_EXT_ENC(OPCODE, CLASS, ENCSTR)                                     \
  [OPCODE] = {.encoding = ENCSTR, .enc_class = CLASS},

#include "third_party/qemu-hexagon/imported/encode.def"

#undef DEF_ENC32
#undef DEF_ENC_SUBINSN
#undef DEF_EXT_ENC
};

void opcode_init(void) {
  init_attribs(0, 0);

#define ATTRIBS(...) , ##__VA_ARGS__, 0
#define OP_ATTRIB(TAG, ARGS) init_attribs(TAG ARGS);
#include "op_attribs_generated.h"
#undef OP_ATTRIB
#undef ATTRIBS

  decode_init();
}

#define NEEDLE "IMMEXT("

int opcode_which_immediate_is_extended(Opcode opcode) {
  const char *p;

  ASSERT_AND_ABORT(opcode < XX_LAST_OPCODE);
  ASSERT_AND_ABORT(GET_ATTRIB(opcode, A_EXTENDABLE));

  p = opcode_short_semantics[opcode];
  p = strstr(p, NEEDLE);
  ASSERT_AND_ABORT(p);
  p += strlen(NEEDLE);
  while (isspace(*p)) {
    p++;
  }
  /* lower is always imm 0, upper always imm 1. */
  if (islower(*p)) {
    return 0;
  } else if (isupper(*p)) {
    return 1;
  } else {
    ASSERT_AND_ABORT(0);
  }
}

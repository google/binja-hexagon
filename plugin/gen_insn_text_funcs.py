#!/usr/bin/env python3
#
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

import concurrent.futures
import sys
import re
import string
from io import StringIO
from collections import namedtuple, OrderedDict
from lark import Lark, Transformer, v_args

from hex_common import *

immext_casere = re.compile(r'IMMEXT\(([A-Za-z])')

# A grammar to parse the Hexagon instruction strings.
#
# For example,
#     "memh(Rs32+#s11:1)=Rt.H32"
#  =>
#      assign_to_exp
#        call_exp
#          None
#          call_rator2
#            insn      memh
#            reg       Rs32
#            rator
#            imm       #s11:1
#          None
#        None
#        None
#        None
#        reg   Rt.H32
#        None
#
# Then a transformer visits all nodes, and generates BinaryNinja calls.
#
#   insn token "jump:nt" => add(InstructionToken, "jump:nt");

insn_grammar = r"""
    ?exp: [not_sign] call [res_hint]      -> call_exp
        | "if (" [not_sign] cond ")" exp  -> if_exp
        | assign_exp

    ?call: insn
         | insn operand                                      -> call1_no_paren
         | insn "(" operand ")"                              -> call1
         | insn "(" operand "," operand ")"                  -> call2
         | insn "(" operand "," rator operand ")"            -> call2_rator
         | insn "(" operand "," operand "," operand ")"      -> call3
         | insn "(" operand rator operand ")"                -> call_rator2
         | insn "(" operand rator operand rator operand ")"  -> call_rator3
         | insn "(" call ")"                                 -> call_nested1
         | insn "(" operand "," call ")"                     -> call_nested2
         | insn "(" call "," operand ")"                     -> call_nested3

    ?cond: operand
         | operand cmp_sign operand  -> cond2
         | call
    cmp_sign: "==" | "!=" | ">=" | "<="
    not_sign: "!"

    assign_exp: operand ["," reg] [rator] "=" [rator] (operand | exp)     -> assign_to_op
              | operand [rator] "=" [rator] (operand | exp) ";" exp       -> assign_comma
              | exp [subfield] [rator] "=" [rator] (operand | exp) [subfield] -> assign_to_exp

    rator: "+" | "<<" | "=" | "++" | "-" | "&" | "|" | "^" | "~"
    subfield: ".uh" | ".h" | ".uw" | ".w" | ".ub" | ".b"

    shift_hint: ":<<1" | ":<<16" | ":>>1" | ":shift"
    rnd_hint: ":rnd" | ":crnd"
    sat_hint: ":sat"
    hilo_hint: ":hi" | ":lo"
    raw_hint: ":raw" [hilo_hint]
    jump_hint: ":t" | ":nt"
    carry_hint: ":carry"
    scale_hint: ":scale"
    lib_hint: ":lib"
    pos_hint: ":pos"
    neg_hint: ":neg"
    chop_hint: ":chop"
    scatter_hint: ":scatter_release"
    nomatch_hint: ":nomatch"
    ?res_hint: shift_hint [res_hint]
             | rnd_hint [res_hint]
             | sat_hint [res_hint]
             | raw_hint [res_hint]
             | jump_hint [res_hint]
             | carry_hint [res_hint]
             | scale_hint
             | lib_hint
             | pos_hint
             | neg_hint
             | chop_hint
             | scatter_hint
             | nomatch_hint

    insn: WORD
        | WORD "." WORD
        | WORD "_" WORD
        | WORD DIGIT ~ 0..2
        | WORD (":t" | ":nt" | "128" | "256")
        | "convert_" WORD "2" WORD
        | "sp" DIGIT "loop" DIGIT
        | "k0" "un"? "lock"
        | "l2" WORD


    circ_addr: imm_or_circi ":circ(" reg ")"
    circ_i: "I"
    ?imm_or_circi: imm | circ_i

    const: "#" SIGNED_NUMBER

    imm: "#" IMMLETT INT [":" INT]
    IMMLETT: /[rRsSuUm]/

    reg:  REG_A REG_B ["."] [REG_C] INT ["S"]
    REG_A: /[MNORCPQXSGVZA]/
    REG_B: /[stuvwxyzdefg]+/
    REG_C: /[LlHh]/

    pred_reg: "p" DIGIT
    gp_reg: "gp"
    sys_reg: "pc" | "sgp" DIGIT ":0"? | "r29" | "r31"
    subreg: ".uh" | ".h" | ".uw" | ".w" | ".ub" | ".b"
    dot_new: ".new"
    dot_cur: ".cur" | ".tmp"
    reg_dot: reg dot_new | pred_reg dot_new
           | reg dot_cur
           | reg subreg
    reg_brev: reg ":brev"
    reg_star: reg "*"
    not_reg: not_sign reg
    ?any_reg: reg | reg_dot | pred_reg | gp_reg | sys_reg | reg_brev | reg_star

    ?operand: const | imm | any_reg | not_reg | circ_addr

    %import common.ESCAPED_STRING
    %import common.WORD
    %import common.INT
    %import common.DIGIT
    %import common.SIGNED_NUMBER
    %import common.WS
    %ignore WS
    """

insn_parser = Lark(
    insn_grammar,
    start='exp',
    parser='earley',
    propagate_positions=True,
    maybe_placeholders=True)

TextToken = namedtuple('TextToken', ['arg1'])
InstructionToken = namedtuple('InstructionToken', ['arg1'])
RegisterToken = namedtuple('RegisterToken', ['arg1'])
GPRegisterToken = namedtuple('GPRegisterToken', ['arg1'])
CodeRelativeAddressToken = namedtuple('CodeRelativeAddressToken',
                                      ['arg1', 'arg2'])
IntegerToken = namedtuple('IntegerToken', ['arg1', 'arg2'])


class InsnTreeTransformer(Transformer):

  def __init__(self, tag, regs, imms):
    super().__init__()
    self.tag = tag
    self.beh = behdict[tag]
    self.extendable_upper_imm = False
    self.extendable_lower_imm = False
    self.seen_cmpjump_imm = False
    self.seen_loop_imm = False
    self.num_imms = len(imms)
    m = immext_casere.search(semdict[tag])
    if m:
      if m.group(1).isupper():
        self.extendable_upper_imm = True
      else:
        self.extendable_lower_imm = True
    self.seenregs = {}
    for ri, (a, b, c, d) in enumerate(regs):
      self.seenregs[b] = ri

  # ?exp: [not_sign] call [res_hint]      -> call_exp
  @v_args(inline=True)
  def call_exp(self, opt_not, call, opt_res_hint):
    opt_not = opt_not if opt_not else []
    opt_res_hint = opt_res_hint if opt_res_hint else []
    return opt_not + call + opt_res_hint

  #     | "if (" [not_sign] cond ")" exp  -> if_exp
  @v_args(inline=True)
  def if_exp(self, opt_not, cond, exp):
    opt_not = opt_not if opt_not else []
    return [
        TextToken('"if ("'),
    ] + opt_not + cond + [
        TextToken('") "'),
    ] + exp

  # | operand cmp_sign operand  -> cond2
  @v_args(inline=True)
  def cond2(self, op1, cmp_sign, op2):
    return op1 + cmp_sign + op2

  #     | insn operand                                      -> call1_no_paren
  @v_args(inline=True)
  def call1_no_paren(self, insn, op):
    return insn + [
        TextToken('" "'),
    ] + op

  #     | insn "(" operand ")"                              -> call1
  @v_args(inline=True)
  def call1(self, insn, op):
    return insn + [
        TextToken('"("'),
    ] + op + [
        TextToken('")"'),
    ]

  #     | insn "(" operand "," operand ")"                  -> call2
  @v_args(inline=True)
  def call2(self, insn, op1, op2):
    return insn + [
        TextToken('"("'),
    ] + op1 + [
        TextToken('","'),
    ] + op2 + [
        TextToken('")"'),
    ]

  #     | insn "(" operand "," rator operand ")"            -> call2_rator
  @v_args(inline=True)
  def call2_rator(self, insn, op1, rator, op2):
    return insn + [
        TextToken('"("'),
    ] + op1 + [
        TextToken('","'),
    ] + rator + op2 + [
        TextToken('")"'),
    ]

  #     | insn "(" operand "," operand "," operand ")"      -> call3
  @v_args(inline=True)
  def call3(self, insn, op1, op2, op3):
    return insn + [
        TextToken('"("'),
    ] + op1 + [
        TextToken('","'),
    ] + op2 + [
        TextToken('","'),
    ] + op3 + [
        TextToken('")"'),
    ]

  #     | insn "(" operand rator operand ")"                -> call_rator2
  @v_args(inline=True)
  def call_rator2(self, insn, op1, rator, op2):
    return insn + [
        TextToken('"("'),
    ] + op1 + rator + op2 + [
        TextToken('")"'),
    ]

  #     | insn "(" operand rator operand rator operand ")"  -> call_rator3
  @v_args(inline=True)
  def call_rator3(self, insn, op1, rator1, op2, rator2, op3):
    return insn + [
        TextToken('"("'),
    ] + op1 + rator1 + op2 + rator2 + op3 + [
        TextToken('")"'),
    ]

  #     | insn "(" call ")"                                 -> call_nested1
  @v_args(inline=True)
  def call_nested1(self, insn, call):
    return insn + [
        TextToken('"("'),
    ] + call + [
        TextToken('")"'),
    ]

  #     | insn "(" operand "," call ")"                     -> call_nested2
  @v_args(inline=True)
  def call_nested2(self, insn, op, call):
    return insn + [
        TextToken('"("'),
    ] + op + [
        TextToken('","'),
    ] + call + [
        TextToken('")"'),
    ]

  #     | insn "(" call "," operand ")"                     -> call_nested3
  @v_args(inline=True)
  def call_nested3(self, insn, call, op):
    return insn + [
        TextToken('"("'),
    ] + call + [
        TextToken('","'),
    ] + op + [
        TextToken('")"'),
    ]

  # assign_exp: operand ["," reg] [rator] "=" [rator] (operand | exp) -> assign_to_op
  @v_args(inline=True)
  def assign_to_op(self, op1, opt_reg, opt_rator1, opt_rator2, op2_or_exp):
    opt_reg = [TextToken('","')] + opt_reg if opt_reg else []
    opt_rator1 = opt_rator1 if opt_rator1 else []
    opt_rator2 = opt_rator2 if opt_rator2 else []
    return op1 + opt_reg + opt_rator1 + [
        TextToken('" = "'),
    ] + opt_rator2 + op2_or_exp

  # | operand [rator] "=" [rator] (operand | exp) ";" exp       -> assign_comma
  @v_args(inline=True)
  def assign_comma(self, op1, opt_rator1, opt_rator2, op2_or_exp, exp):
    opt_rator1 = opt_rator1 if opt_rator1 else []
    opt_rator2 = opt_rator2 if opt_rator2 else []
    return op1 + opt_rator1 + [
        TextToken('" = "'),
    ] + opt_rator2 + op2_or_exp + [
        TextToken('";"'),
    ] + exp

  # | exp [subfield] [rator] "=" [rator] (operand | exp) [subfield] -> assign_to_exp
  @v_args(inline=True)
  def assign_to_exp(self, exp1, opt_subfield1, opt_rator1, opt_rator2,
                    op_or_exp2, opt_subfield2):
    opt_subfield1 = opt_subfield1 if opt_subfield1 else []
    opt_rator1 = opt_rator1 if opt_rator1 else []
    opt_rator2 = opt_rator2 if opt_rator2 else []
    opt_subfield2 = opt_subfield2 if opt_subfield2 else []
    return exp1 + opt_subfield1 + opt_rator1 + [
        TextToken('" = "'),
    ] + opt_rator2 + op_or_exp2 + opt_subfield2

  # raw_hint: ":raw" [hilo_hint]
  @v_args(inline=True)
  def raw_hint(self, opt_hilo):
    opt_hilo = opt_hilo if opt_hilo else []
    return [TextToken('":raw"')] + opt_hilo

  # res_hint: shift_hint [res_hint]
  @v_args(inline=True)
  def res_hint(self, hint, opt_more):
    opt_more = opt_more if opt_more else []
    return hint + opt_more

  # reg:  REG_A REG_B ["."] [REG_C] INT ["S"]
  @v_args(inline=True)
  def reg(self, a, b, c, d):
    regno = self.seenregs[b]
    c = "" if not c else c
    if len(b) == 1:
      # Single register.
      return [
          RegisterToken('GetRegisterName("{0}", "{1}", insn.regno[{2}])'.format(
              a, c, regno))
      ]

    if len(b) == 2:
      # Register pair.
      assert (not c)
      return [
          RegisterToken(
              'GetRegisterName("{0}", "{1}", insn.regno[{2}]+1)'.format(
                  a, c, regno)),
          TextToken('":"'),
          RegisterToken('GetRegisterName("{0}", "{1}", insn.regno[{2}])'.format(
              a, c, regno)),
      ]

    assert (0)

  # imm: "#" IMMLETT INT [":" INT]
  @v_args(inline=True)
  def imm(self, immlett, bits, immshift):
    # When an instruction contains more than one immediate operand, the operand
    # symbols are specified in upper and lower case (e.g., #uN and #UN) to indicate
    # where they appear in the instruction encodings.
    ii = 1 if (immlett.isupper()) else 0

    res = []
    place_addr_token = False
    if self.is_jump() or self.is_call():
      place_addr_token = True
      if self.num_imms > 1:
        assert (self.num_imms == 2)
        assert (self.tag == "J4_jumpseti" or self.is_compound_comapre_jump() or
                self.is_new_value_jump())
        # Some cmp-jump instructions have two imms. Place address token only
        # on the second, jump instruction.
        place_addr_token = self.seen_cmpjump_imm
        self.seen_cmpjump_imm = True

    if self.is_write_to_loop_start():
      # Some loop instructions have two imms. Place address token only
      # on the first imm.
      place_addr_token = not self.seen_loop_imm
      self.seen_loop_imm = True

    if place_addr_token:
      res += [
          CodeRelativeAddressToken(
              'StrCat("0x", Hex(pc + insn.immed[{0}]))'.format(ii),
              'pc + insn.immed[{0}]'.format(ii)),
      ]
    else:
      if ((immlett.isupper() and self.extendable_upper_imm) or
          (immlett.islower() and self.extendable_lower_imm)):
        res += [
            TextToken('(insn.extension_valid ? "##" : "#")'),
        ]
      else:
        res += [
            TextToken('"#"'),
        ]
      res += [
          IntegerToken('StrCat("0x", Hex(insn.immed[{0}]))'.format(ii),
                       'insn.immed[{0}]'.format(ii)),
      ]
    return res

  def is_jump(self):
    return ("A_JUMP" in attribdict[self.tag])

  def is_call(self):
    return ("A_CALL" in attribdict[self.tag])

  def is_compound_comapre_jump(self):
    return ("A_NEWCMPJUMP" in attribdict[self.tag])

  def is_new_value_jump(self):
    return ("A_JUMP" in attribdict[self.tag] and
            "A_DOTNEWVALUE" in attribdict[self.tag] and
            "A_MEMLIKE_PACKET_RULES" in attribdict[self.tag])

  def is_write_to_loop_start(self):
    return ("A_IMPLICIT_WRITES_SA0" in attribdict[self.tag] or
            "A_IMPLICIT_WRITES_SA1" in attribdict[self.tag])

  # circ_addr: imm_or_circi ":circ(" reg ")"
  @v_args(inline=True)
  def circ_addr(self, imm, reg):
    return imm + [
        TextToken('":circ("'),
    ] + reg + [
        TextToken('")"'),
    ]

  # const: "#" SIGNED_NUMBER
  @v_args(inline=True)
  def const(self, num):
    return [
        TextToken('"#"'),
        IntegerToken('StrCat("0x", Hex({}))'.format(num), '{}'.format(num)),
    ]

  # pred_reg: "p" DIGIT
  @v_args(inline=True)
  def pred_reg(self, digit):
    return [RegisterToken('"{}"'.format('P' + digit))]

  # gp_reg: "gp"
  @v_args(meta=True)
  def gp_reg(self, children, meta):
    word = self.beh[meta.start_pos:meta.end_pos].upper()
    return [GPRegisterToken('"{}"'.format(word))]

  # sys_reg: "pc" | "sgp" DIGIT ":0"? | "r29" | "r31"
  @v_args(meta=True)
  def sys_reg(self, children, meta):
    word = self.beh[meta.start_pos:meta.end_pos].upper()
    if word == 'R29':
      word = 'SP'
    if word == 'R31':
      word = 'LR'
    return [RegisterToken('"{}"'.format(word))]

  #  reg_dot: reg dot_new | pred_reg dot_new
  #         | reg dot_cur
  #         | reg subreg
  @v_args(inline=True)
  def reg_dot(self, reg, dot):
    return reg + dot

  # reg_brev: reg ":brev"
  @v_args(inline=True)
  def reg_brev(self, reg):
    return reg + [
        TextToken('":brev"'),
    ]

  # reg_star: reg "*"
  @v_args(inline=True)
  def reg_star(self, reg):
    return reg + [
        TextToken('"*"'),
    ]

  #  not_reg: not_sign reg
  @v_args(inline=True)
  def not_reg(self, not_sign, reg):
    return not_sign + reg

  def wrap_full_match(self, typ, meta):
    # Read full match.
    word = self.beh[meta.start_pos:meta.end_pos]
    return [
        typ('"' + word + '"'),
    ]

  @v_args(meta=True)
  def wrap_instruction_terminal(self, children, meta):
    return self.wrap_full_match(InstructionToken, meta)

  @v_args(meta=True)
  def wrap_reg_terminal(self, children, meta):
    return self.wrap_full_match(RegisterToken, meta)

  @v_args(meta=True)
  def wrap_text_terminal(self, children, meta):
    return self.wrap_full_match(TextToken, meta)

  insn = wrap_instruction_terminal
  rator = wrap_text_terminal
  subfield = wrap_text_terminal
  shift_hint = wrap_text_terminal
  rnd_hint = wrap_text_terminal
  sat_hint = wrap_text_terminal
  hilo_hint = wrap_text_terminal
  carry_hint = wrap_text_terminal
  scale_hint = wrap_text_terminal
  lib_hint = wrap_text_terminal
  pos_hint = wrap_text_terminal
  neg_hint = wrap_text_terminal
  chop_hint = wrap_text_terminal
  scatter_hint = wrap_text_terminal
  nomatch_hint = wrap_text_terminal
  cmp_sign = wrap_text_terminal
  not_sign = wrap_text_terminal
  circ_i = wrap_text_terminal
  jump_hint = wrap_text_terminal

  dot_new = wrap_reg_terminal
  dot_cur = wrap_reg_terminal
  subreg = wrap_reg_terminal


def wrap_call(tok):
  if isinstance(tok, TextToken):
    return 'result.emplace_back(TextToken, {0.arg1});'.format(tok)
  if isinstance(tok, InstructionToken):
    return 'result.emplace_back(InstructionToken, {0.arg1});'.format(tok)
  if isinstance(tok, RegisterToken):
    return 'result.emplace_back(RegisterToken, {0.arg1});'.format(tok)
  if isinstance(tok, GPRegisterToken):
    # Global pointer relative addressing has different semantics when there's
    # a valid immediate extension.
    # #define fREAD_GP() \
    #     (insn->extension_valid ? 0 : READ_REG(HEX_REG_GP))
    return '''if (insn.extension_valid) {{
                result.emplace_back(IntegerToken, "0", 0);
            }} else {{
                result.emplace_back(RegisterToken, {0.arg1});
            }}'''.format(tok)
  if isinstance(tok, CodeRelativeAddressToken):
    return 'result.emplace_back(CodeRelativeAddressToken, {0.arg1}, {0.arg2});'.format(
        tok)
  if isinstance(tok, IntegerToken):
    return 'result.emplace_back(IntegerToken, {0.arg1}, {0.arg2});'.format(tok)
  raise ValueError(tok)


def process_insn_tokens(tag, regs, imms):
  beh = behdict[tag]
  tree = insn_parser.parse(beh)
  tokens = InsnTreeTransformer(tag, regs, imms).transform(tree)
  return tokens


def gen_insn_text_func(tag, regs, imms):
  tokens = process_insn_tokens(tag, regs, imms)
  return "\n".join(map(wrap_call, tokens))


def process_all_tags(tagregs, tagimms):
  tag_to_fbody = OrderedDict({tag: '' for tag in tags})
  print('Processing %d tags in parallel' % (len(tags)))
  with concurrent.futures.ProcessPoolExecutor(max_workers=5) as executor:
    future_to_tag = {}
    for i, tag in enumerate(tags):
      if not behdict[tag]:
        continue
      future_to_tag[executor.submit(gen_insn_text_func, tag, tagregs[tag],
                                    tagimms[tag])] = tag

    for i, future in enumerate(concurrent.futures.as_completed(future_to_tag)):
      if i % 100 == 0:
        print('Done processing tag #', i)
      tag = future_to_tag[future]
      tag_to_fbody[tag] = future.result()
  return tag_to_fbody


def main():
  read_semantics_file(sys.argv[1])
  read_attribs_file(sys.argv[2])
  calculate_attribs()
  tagregs = get_tagregs()
  tagimms = get_tagimms()

  f = StringIO()
  f.write('''
#include <vector>

#include "binaryninjaapi.h"
#include "absl/strings/str_cat.h"
#include "plugin/text_util.h"
#include "third_party/qemu-hexagon/attribs.h"
#include "third_party/qemu-hexagon/iclass.h"
#include "third_party/qemu-hexagon/insn.h"
#include "third_party/qemu-hexagon/opcodes.h"

using namespace BinaryNinja;
using absl::Hex;
using absl::StrCat;

''')

  tag_to_fbody = process_all_tags(tagregs, tagimms)
  for tag, fbody in tag_to_fbody.items():
    f.write('''/*\n{0}:  "{1}"\n*/'''.format(tag, behdict[tag]))
    f.write('''void tokenize_{0}(uint64_t pc,
                             const Packet &pkt,
                             const Insn &insn,
                             std::vector<InstructionTextToken> &result) {{\n'''
            .format(tag))
    f.write(fbody)
    f.write('}\n\n')

  f.write('''typedef void (*InsnTextFunc)(uint64_t pc,
                            const Packet &pkt,
                            const Insn &insn,
                            std::vector<InstructionTextToken> &result);\n\n''')
  f.write('extern const InsnTextFunc opcode_textptr[XX_LAST_OPCODE] = {\n')
  for tag in tags:
    if not behdict[tag]:
      return
    f.write('[{0}] = tokenize_{0},\n'.format(tag))
  f.write('};\n')

  realf = open(sys.argv[3], 'w')
  realf.write(f.getvalue())
  realf.close()
  f.close()


if __name__ == "__main__":
  main()

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

import copy
import sys
import re
import string
import itertools
from io import StringIO
from typing import Union

from lark import Lark, Transformer, Tree, v_args, Token
from pcpp import Preprocessor

from hex_common import *
from type_util import *
from gen_il_funcs_data import *

# Following grammar is based on the C grammar copied from
# https://www2.cs.arizona.edu/~debray/Teaching/CSc453/DOCS/cminusminusspec.html
semantics_grammar = r"""

fbody: stmt* -> fbody

?stmt: "if" "(" expr ")" stmt [ "else" stmt ] -> if_stmt
     | expr "?" "(" assg ")" ":" "(" assg ")" -> ternary_stmt
     | "while" "(" expr ")" stmt
     | "for" "(" [ assg ] ";" [ expr ] ";" [ assg ] ")" stmt
     | "return" [ expr ] ";"
     | assg ";" -> assg_stmt
     | id ASSGOP expr ";" -> assg_binop_stmt
     | id "(" [expr ("," expr)* ] ")" ";" -> call_stmt
     | "{" stmt* "}" -> multi_stmt
     | ";" -> empty_stmt
     | "CANCEL;" -> cancel_stmt

?assg: id "=" expr

?expr: "-" expr        -> neg_expr
     | "!" expr        -> not_expr
     | "~" expr        -> bit_not_expr
     | expr BINOP expr -> expr_binop
     | expr RELOP expr -> expr_relop
     | expr LOGOP expr
     | id
     | id "(" [expr ("," expr)* ] ")" -> call_expr
     | id "[" expr "]" -> unexpected
     | "(" expr ")"
     | INTCON
     | STRINGCON

ASSGOP.4: "+="
     |    "-="
     |    "&="
     |    "^="
     |    "|="

BINOP.3: "+"
     |   "-"
     |   "*"
     |   "/"
     |   "|"
     |   "&"
     |   "^"
     |   "<<"
     |   ">>"

RELOP.2: "=="
     |   "!="
     |   "<="
     |   "<"
     |   ">="
     |   ">"

LOGOP.1: "&&"
     |   "||"

?id: REG_OLD | REG_NEW | REG_LR | IMM | MACRO | EA | SIGN | BRANCH_TYPE | TMP
REG_OLD: REG "V"
REG_NEW: REG "N"
REG: REG_TYPE REG_ID
REG_TYPE: "C" | "N" | "P" | "R" | "M" | "Q" | "V" | "O"
REG_ID: DST_REG | DST_REG_PAIR | SRC_REG | SRC_REG_PAIR | RX_REG | RX_REG_PAIR
DST_REG: "d" | "e"
DST_REG_PAIR: "dd"
SRC_REG: "s" | "t" | "u" | "v" | "w"
SRC_REG_PAIR: "ss" | "tt" | "uu" | "vv"
RX_REG: "x" | "y"
RX_REG_PAIR: "xx" | "yy"
REG_LR: "REG_LR"
IMM: IMMLETT "iV"
IMMLETT: "r" | "R" | "s" | "S" | "u" | "U" | "m"
MACRO: /f\w+/
EA: "EA"
SIGN: "s" | "u"
BRANCH_TYPE: /COF_TYPE_\w+/
TMP: "tmp" | "width" | "offset" | "shamt"

INTCON: HEX_NUMBER | DEC_NUMBER
HEX_NUMBER: /0x[\da-f]*/i
DEC_NUMBER: /0|[1-9][\d_]*/i
STRINGCON: ESCAPED_STRING

%import common.ESCAPED_STRING
%import common.INT
%import common.WS
%ignore WS
"""

semantics_parser = Lark(
    semantics_grammar,
    start='fbody',
    parser='lalr',
    debug=True,
    propagate_positions=False,
    maybe_placeholders=False)

#
# Following classes map to Binary Ninja ExprId.
#


class IlExprId:

  def __init__(self, signed=True):
    self.signed = signed


class IlSetRegister(IlExprId):

  @type_check
  def __init__(self, size: int, reg: str, val: IlExprId):
    super().__init__(signed=val.signed)
    self.size, self.reg, self.val = size, reg, val

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.reg == other.reg and
            self.val == other.val)

  def __repr__(self):
    return '''il.SetRegister({0}, {1}, {2})'''.format(self.size, self.reg,
                                                      self.val)


class IlRegister(IlExprId):

  @type_check
  def __init__(self, size: int, reg: str):
    super().__init__()
    self.size, self.reg = size, reg

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.reg == other.reg)

  def __repr__(self):
    return '''il.Register({0}, {1})'''.format(self.size, self.reg)


class IlSetRegisterSplit(IlExprId):

  @type_check
  def __init__(self, size: int, hi: str, lo: str, val: IlExprId):
    super().__init__(signed=val.signed)
    self.size, self.hi, self.lo, self.val = size, hi, lo, val

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.hi == other.hi and
            self.lo == other.lo and self.val == other.val)

  def __repr__(self):
    return '''il.SetRegisterSplit({0}, {1}, {2}, {3})'''.format(
        self.size, self.hi, self.lo, self.val)


class IlRegisterSplit(IlExprId):

  @type_check
  def __init__(self, size: int, hi: str, lo: str):
    super().__init__()
    self.size, self.hi, self.lo = size, hi, lo

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.hi == other.hi and
            self.lo == other.lo)

  def __repr__(self):
    return '''il.RegisterSplit({0}, {1}, {2})'''.format(self.size, self.hi,
                                                        self.lo)


class IlConst(IlExprId):

  @type_check
  def __init__(self, size: int, val: Union[int, str]):
    super().__init__()
    self.size, self.val = size, val
    self.val = str(self.val) if isinstance(self.val, int) else self.val

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.val == other.val)

  def __repr__(self):
    return '''il.Const({0}, {1})'''.format(self.size, self.val)


class IlConstPointer(IlExprId):

  @type_check
  def __init__(self, size: int, val: str):
    super().__init__(signed=False)
    self.size, self.val = size, val

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.val == other.val)

  def __repr__(self):
    return '''il.ConstPointer({0}, {1})'''.format(self.size, self.val)


class IlLowPart(IlExprId):

  @type_check
  def __init__(self, size: int, a: IlExprId):
    super().__init__(signed=a.signed)
    self.size, self.a = size, a

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a)

  def __repr__(self):
    return '''il.LowPart({0}, {1})'''.format(self.size, self.a)


class IlZeroExtend(IlExprId):

  @type_check
  def __init__(self, size: int, a: IlExprId):
    super().__init__(signed=False)
    self.size, self.a = size, a

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a)

  def __repr__(self):
    return '''il.ZeroExtend({0}, {1})'''.format(self.size, self.a)


class IlSignExtend(IlExprId):

  @type_check
  def __init__(self, size: int, a: IlExprId):
    super().__init__(signed=True)
    self.size, self.a = size, a

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a)

  def __repr__(self):
    return '''il.SignExtend({0}, {1})'''.format(self.size, self.a)


class IlAdd(IlExprId):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=a.signed)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.Add({0}, {1}, {2})'''.format(self.size, self.a, self.b)


class IlSub(IlExprId):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=a.signed)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.Sub({0}, {1}, {2})'''.format(self.size, self.a, self.b)


class IlOr(IlExprId):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=False)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.Or({0}, {1}, {2})'''.format(self.size, self.a, self.b)


class IlAnd(IlExprId):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=False)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.And({0}, {1}, {2})'''.format(self.size, self.a, self.b)


class IlXor(IlExprId):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=False)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.Xor({0}, {1}, {2})'''.format(self.size, self.a, self.b)


class IlNot(IlExprId):

  @type_check
  def __init__(self, size: int, a: IlExprId):
    super().__init__(signed=False)
    self.size, self.a = size, a

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a)

  def __repr__(self):
    return '''il.Not({0}, {1})'''.format(self.size, self.a)


class IlNeg(IlExprId):

  @type_check
  def __init__(self, size: int, a: IlExprId):
    super().__init__(signed=False)
    self.size, self.a = size, a

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a)

  def __repr__(self):
    return '''il.Neg({0}, {1})'''.format(self.size, self.a)


class IlStore(IlExprId):

  @type_check
  def __init__(self, size: int, addr: IlExprId, val: IlExprId):
    super().__init__(signed=val.signed)
    self.size, self.addr, self.val = size, addr, val

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.addr == other.addr and
            self.val == other.val)

  def __repr__(self):
    return '''il.Store({0}, {1}, {2})'''.format(self.size, self.addr, self.val)


class IlLoad(IlExprId):

  @type_check
  def __init__(self, size: int, addr: IlExprId):
    super().__init__()
    self.size, self.addr = size, addr

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.addr == other.addr)

  def __repr__(self):
    return '''il.Load({0}, {1})'''.format(self.size, self.addr)


class IlBranch(IlExprId):
  pass


class IlJump(IlBranch):

  @type_check
  def __init__(self, dest: IlExprId):
    super().__init__()
    self.dest = dest

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.dest == other.dest)

  def __repr__(self):
    return '''il.Jump({0})'''.format(self.dest)


class IlCall(IlBranch):

  @type_check
  def __init__(self, dest: IlExprId):
    super().__init__()
    self.dest = dest

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.dest == other.dest)

  def __repr__(self):
    return '''il.Call({0})'''.format(self.dest)


class IlReturn(IlBranch):

  @type_check
  def __init__(self, dest: IlExprId):
    super().__init__()
    self.dest = dest

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.dest == other.dest)

  def __repr__(self):
    return '''il.Return({0})'''.format(self.dest)


class IlShiftLeft(IlExprId):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=a.signed)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.ShiftLeft({0}, {1}, {2})'''.format(self.size, self.a, self.b)


class IlLogicalShiftRight(IlExprId):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=a.signed)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.LogicalShiftRight({0}, {1}, {2})'''.format(
        self.size, self.a, self.b)


class IlArithShiftRight(IlExprId):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=a.signed)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.ArithShiftRight({0}, {1}, {2})'''.format(
        self.size, self.a, self.b)


class IlRotateLeft(IlExprId):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=a.signed)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.RotateLeft({0}, {1}, {2})'''.format(self.size, self.a, self.b)


class IlMult(IlExprId):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=a.signed)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.Mult({0}, {1}, {2})'''.format(self.size, self.a, self.b)


class IlTrap(IlExprId):

  @type_check
  def __init__(self, num: IlConst):
    super().__init__()
    self.num = num

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.num == other.num)

  def __repr__(self):
    return '''il.Trap({0})'''.format(self.num.val)


class IlSystemCall(IlExprId):

  @type_check
  def __init__(self):
    super().__init__()
    pass

  def __eq__(self, other):
    return isinstance(other, self.__class__)

  def __repr__(self):
    return '''il.SystemCall()'''


class IlBreakpoint(IlExprId):

  @type_check
  def __init__(self):
    super().__init__()
    pass

  def __eq__(self, other):
    return isinstance(other, self.__class__)

  def __repr__(self):
    return '''il.Breakpoint()'''


class IlBoolToInt(IlExprId):

  @type_check
  def __init__(self, size: int, a: IlExprId):
    super().__init__()
    self.size, self.a = size, a

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a)

  def __repr__(self):
    return '''il.BoolToInt({0}, {1})'''.format(self.size, self.a)


class IlCompareExpr(IlExprId):
  pass


class IlCompareEqual(IlCompareExpr):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=False)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.CompareEqual({0}, {1}, {2})'''.format(self.size, self.a,
                                                       self.b)


class IlCompareNotEqual(IlCompareExpr):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=False)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.CompareNotEqual({0}, {1}, {2})'''.format(
        self.size, self.a, self.b)


class IlCompareSignedGreaterThan(IlCompareExpr):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=False)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.CompareSignedGreaterThan({0}, {1}, {2})'''.format(
        self.size, self.a, self.b)


class IlCompareUnsignedGreaterThan(IlCompareExpr):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=False)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.CompareUnsignedGreaterThan({0}, {1}, {2})'''.format(
        self.size, self.a, self.b)


class IlCompareSignedGreaterEqual(IlCompareExpr):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=False)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.CompareSignedGreaterEqual({0}, {1}, {2})'''.format(
        self.size, self.a, self.b)


class IlCompareSignedLessThan(IlCompareExpr):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=False)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.CompareSignedLessThan({0}, {1}, {2})'''.format(
        self.size, self.a, self.b)


class IlCompareUnsignedGreaterEqual(IlCompareExpr):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=False)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.CompareUnsignedGreaterEqual({0}, {1}, {2})'''.format(
        self.size, self.a, self.b)


class IlCompareUnsignedLessThan(IlCompareExpr):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=False)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.CompareUnsignedLessThan({0}, {1}, {2})'''.format(
        self.size, self.a, self.b)


class IlCompareSignedLessEqual(IlCompareExpr):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=False)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.CompareSignedLessEqual({0}, {1}, {2})'''.format(
        self.size, self.a, self.b)


class IlCompareUnsignedLessEqual(IlCompareExpr):

  @type_check
  def __init__(self, size: int, a: IlExprId, b: IlExprId):
    super().__init__(signed=False)
    self.size, self.a, self.b = size, a, b

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.a == other.a and self.b == other.b)

  def __repr__(self):
    return '''il.CompareUnsignedLessEqual({0}, {1}, {2})'''.format(
        self.size, self.a, self.b)


class IlIf(IlExprId):

  @type_check
  def __init__(self, cond: IlExprId, t: str, f: str):
    super().__init__()
    self.cond, self.t, self.f = cond, t, f

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.cond == other.cond and self.t == other.t and self.f == other.f)

  def __repr__(self):
    return '''il.If({0}, {1}, {2})'''.format(self.cond, self.t, self.f)


class IlGoto(IlExprId):

  @type_check
  def __init__(self, l: str):
    super().__init__()
    self.l = l

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.l == other.l)

  def __repr__(self):
    return '''il.Goto({0})'''.format(self.l)


class IlPush(IlExprId):

  @type_check
  def __init__(self, size: int, val: IlExprId):
    super().__init__()
    self.size, self.val = size, val

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size and self.val == other.val)

  def __repr__(self):
    return '''il.Push({0}, {1})'''.format(self.size, self.val)


class IlPop(IlExprId):

  @type_check
  def __init__(self, size: int):
    super().__init__()
    self.size = size

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size)

  def __repr__(self):
    return '''il.Pop({0})'''.format(self.size)


class IlReadGP(IlExprId):

  @type_check
  def __init__(self, size: int):
    super().__init__()
    self.size = size

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    return (self.size == other.size)

  # #define fREAD_GP() \
  #     (insn->extension_valid ? 0 : READ_REG(HEX_REG_GP))
  #
  # Global pointer relative addresses can be expressed two ways in assembly language:
  #  * By explicitly adding an unsigned offset value to register GP.
  #  * By specifying only an immediate value as the instruction operand.
  def __repr__(self):
    return (
        '''(insn.extension_valid ? il.Const({0}, 0) : il.Register({0}, HEX_REG_GP))'''
        .format(self.size))


class IlLabel(str):
  pass


class RawC(str):
  pass


#
# Tag overrides.
#
behoverrides = {
    'A2_swiz': 'Rd32=swiz(Rs32)',
}
semoverrides = {
    'A2_swiz': '{ RdV = fBYTESWAP(RsV); }',
}


#
# Transforms semantics tree to serialized lifter code.
#
class SemanticsTreeTransformer(Transformer):

  def __init__(self, tag):
    super().__init__()
    self.tag = tag

  def lift_operand(self, op):
    if isinstance(op, IlExprId):
      return copy.copy(op)
    if op.type == 'REG_OLD':
      if op.startswith('P'):
        op = IlRegister(1, op)
      elif re.search(r'dd|ss|tt|uu|vv', op):
        # Pair
        op = IlRegister(8, op)
      else:
        op = IlRegister(4, op)
    elif op.type == 'REG_NEW':
      if op.startswith('P'):
        op = IlRegister(1, op)
      elif re.search(r'dd|ss|tt|uu|vv', op):
        # Pair
        op = IlRegister(8, op)
      else:
        op = IlRegister(4, op)
    elif op.type == 'EA':
      op = IlRegister(4, 'EA_REG')
    elif op.type == 'REG_LR':
      op = IlRegister(4, 'HEX_REG_LR')
    elif op.type in ['IMM', 'INTCON']:
      op = IlConst(4, op)
    elif op.type == 'TMP':
      if op.value == 'tmp':
        op = IlRegister(8, 'TMP_REG')
      elif op.value == 'width':
        op = IlRegister(8, 'WIDTH_REG')
      elif op.value == 'offset':
        op = IlRegister(8, 'OFFSET_REG')
      elif op.value == 'shamt':
        op = IlRegister(8, 'SHAMT_REG')
      else:
        assert (0)
    else:
      assert (0)
    return op

  def macro_stmt_fIMMEXT(self, args):
    # macros.h:
    #   #define fIMMEXT(IMM) (IMM = IMM)
    # no-op operation.
    assert (len(args) == 1)
    assert (args[0].type == 'IMM')
    return []

  def macro_stmt_fPCALIGN(self, args):
    # macros.h:
    #  #define fPCALIGN(IMM) IMM = (IMM & ~PCALIGN_MASK)
    assert (len(args) == 1)
    assert (args[0].type == 'IMM')
    return [RawC('''{0} = {0} & ~PCALIGN_MASK;'''.format(args[0]))]

  def macro_stmt_fBRANCH(self, args):
    # macros.h:
    # #define fBRANCH(LOC, TYPE)          fWRITE_NPC(LOC)
    assert (len(args) == 2)
    assert (args[1].type == 'BRANCH_TYPE')
    typ = args[1]
    loc = self.lift_operand(args[0])
    ret = []
    if 'A_BN_COND_J' in attribdict[self.tag]:
      ret += [IlSetRegister(1, 'BRANCH_TAKEN_ARRAY + insn_num', IlConst(1, 1))]
    if (typ in ['COF_TYPE_JUMP', 'COF_TYPE_JUMPNEW']):
      ret += [IlJump(loc)]
    elif (typ == 'COF_TYPE_JUMPR'):
      ret += [IlSetRegister(4, 'BRANCHR_DEST_ARRAY + insn_num', loc)]
      ret += [IlJump(loc)]
    elif (typ == 'COF_TYPE_CALL'):
      ret += [IlCall(loc)]
    elif (typ == 'COF_TYPE_CALLR'):
      ret += [IlSetRegister(4, 'BRANCHR_DEST_ARRAY + insn_num', loc)]
      ret += [IlCall(loc)]
    elif (typ == 'COF_TYPE_RETURN'):
      ret += [IlReturn(loc)]
    elif (typ in ['COF_TYPE_LOOPEND0', 'COF_TYPE_LOOPEND1']):
      # Loop ends are treated as a conditional branches.
      assert ('A_BN_COND_J' in attribdict[self.tag])
      ret += [IlSetRegister(4, 'BRANCHR_DEST_ARRAY + insn_num', loc)]
      ret += [IlJump(loc)]
    else:
      assert (0)
    return ret

  def macro_stmt_fJUMPR(self, args):
    # macros.h:
    # #define fJUMPR(REGNO, TARGET, TYPE) fBRANCH(TARGET, COF_TYPE_JUMPR)
    assert (len(args) == 3)
    regno, loc, typ = args
    if regno == 'REG_LR':
      typ = Token('BRANCH_TYPE', 'COF_TYPE_RETURN')
    return self.macro_stmt_fBRANCH([loc, typ])

  def macro_stmt_fTRAP(self, args):
    # macros.h:
    # #define fTRAP(TRAPTYPE, IMM) helper_raise_exception(env, HEX_EXCP_TRAP0)
    assert (len(args) == 2)
    typ, imm = list(map(self.lift_operand, args))
    return [IlSystemCall()]

  def macro_stmt_fBREAK(self, args):
    assert (len(args) == 0)
    return [IlBreakpoint()]

  def macro_stmt_fSTORE(self, args):
    # macros.h:
    # #define fSTORE(NUM, SIZE, EA, SRC) MEM_STORE##SIZE(EA, SRC, slot)
    assert (len(args) == 4)
    _, size, ea, src = args
    assert (size.type == 'INTCON')
    assert (ea.type == 'EA')
    size = int(size)
    ea, src = list(map(self.lift_operand, [ea, src]))
    return [IlStore(size, ea, src)]

  def macro_stmt_fSTORE_LOCKED(self, args):
    # macros.h:
    # #define fSTORE(NUM, SIZE, EA, SRC, PRED) \
    #    { PRED = (mem_store_conditional(thread,EA,SRC,SIZE,insn) ? 0xff : 0); }
    assert (len(args) == 5)
    pred = self.lift_operand(args[4])
    ret = []
    ret += self.macro_stmt_fSTORE(args[:4])
    ret += [IlSetRegister(pred.size, pred.reg, IlConst(1, 1))]
    return ret

  def macro_stmt_fLOAD(self, args):
    # macros.h:
    # #define fLOAD(NUM, SIZE, SIGN, EA, DST) \
    #     DST = (size##SIZE##SIGN##_t)MEM_LOAD##SIZE##SIGN(EA)
    # #endif
    assert (len(args) == 5)
    _, size, sign, ea, dst = args
    assert (size.type == 'INTCON')
    assert (sign.type == 'SIGN')
    assert (ea.type == 'EA')
    size = int(size)
    ea, dst = list(map(self.lift_operand, [ea, dst]))
    val = IlLoad(size, ea)
    if size < dst.size:
      if sign == 's':
        val = IlSignExtend(dst.size, val)
      else:
        val = IlZeroExtend(dst.size, val)
    return [IlSetRegister(dst.size, dst.reg, val)]

  def macro_stmt_fWRITE_FP(self, args):
    # macros.h:
    # #define fWRITE_FP(A) WRITE_RREG(HEX_REG_FP, A)
    assert (len(args) == 1)
    a = self.lift_operand(args[0])
    return [IlSetRegister(4, 'HEX_REG_FP', a)]

  def macro_stmt_fWRITE_LR(self, args):
    # macros.h:
    # #define fWRITE_LR(A) WRITE_RREG(HEX_REG_LR, A)
    assert (len(args) == 1)
    a = self.lift_operand(args[0])
    return [IlSetRegister(4, 'HEX_REG_LR', a)]

  def macro_stmt_fWRITE_SP(self, args):
    # macros.h:
    # #define fWRITE_SP(A) WRITE_RREG(HEX_REG_SP, A)
    assert (len(args) == 1)
    a = self.lift_operand(args[0])
    return [IlSetRegister(4, 'HEX_REG_SP', a)]

  def macro_stmt_fWRITE_P0(self, args):
    # macros.h:
    # #define fWRITE_P0(VAL) WRITE_PREG(0, VAL)
    assert (len(args) == 1)
    val = self.lift_operand(args[0])
    return [IlSetRegister(1, 'Pd0', val)]

  def macro_stmt_fWRITE_P1(self, args):
    # macros.h:
    # #define fWRITE_P1(VAL) WRITE_PREG(1, VAL)
    assert (len(args) == 1)
    val = self.lift_operand(args[0])
    return [IlSetRegister(1, 'Pd1', val)]

  def macro_stmt_fWRITE_P2(self, args):
    # macros.h:
    # #define fWRITE_P2(VAL) WRITE_PREG(2, VAL)
    assert (len(args) == 1)
    val = self.lift_operand(args[0])
    return [IlSetRegister(1, 'Pd2', val)]

  def macro_stmt_fWRITE_P3(self, args):
    # macros.h:
    # #define fWRITE_P3(VAL) WRITE_PREG(3, VAL)
    assert (len(args) == 1)
    val = self.lift_operand(args[0])
    return [IlSetRegister(1, 'Pd3', val)]

  def macro_stmt_fWRITE_LOOP_REGS(self, args):
    # macros.h
    # #define fWRITE_LOOP_REGS0(START, COUNT) \
    #     do { \
    #         WRITE_RREG(HEX_REG_LC0, COUNT);  \
    #         WRITE_RREG(HEX_REG_SA0, START); \
    #     } while (0)
    # or
    # #define fWRITE_LOOP_REGS1(START, COUNT) \
    #     do { \
    #         WRITE_RREG(HEX_REG_LC1, COUNT);  \
    #         WRITE_RREG(HEX_REG_SA1, START); \
    #     } while (0)
    assert (len(args) == 3)
    assert (args[0].type == 'INTCON')
    n = int(args[0])
    start, count = list(map(self.lift_operand, args[1:]))
    ret = []
    if n == 0:
      ret += [IlSetRegister(4, 'HEX_REG_LC0', count)]
      ret += [IlSetRegister(4, 'HEX_REG_SA0', start)]
    elif n == 1:
      ret += [IlSetRegister(4, 'HEX_REG_LC1', count)]
      ret += [IlSetRegister(4, 'HEX_REG_SA1', start)]
    else:
      assert (0)
    return ret

  def macro_stmt_fSET_LPCFG(self, args):
    # macros.h
    # #define fSET_LPCFG(VAL) SET_USR_FIELD(USR_LPCFG, (VAL))
    # #define SET_USR_FIELD(FIELD, VAL) \
    #     fINSERT_BITS(env->gpr[HEX_REG_USR], reg_field_info[FIELD].width, \
    #                  reg_field_info[FIELD].offset, (VAL))
    assert (len(args) == 1)
    val = self.lift_operand(args[0])
    return [IlSetRegister(1, 'HEX_REG_USR_LPCFG', val)]

  def macro_stmt_fWRITE_LC(self, args):
    # macros.h
    # #define fWRITE_LC0(VAL) WRITE_RREG(HEX_REG_LC0, VAL)
    # #define fWRITE_LC1(VAL) WRITE_RREG(HEX_REG_LC1, VAL)
    assert (len(args) == 2)
    assert (args[0].type == 'INTCON')
    n = int(args[0])
    val = self.lift_operand(args[1])
    if n == 0:
      return [IlSetRegister(4, 'HEX_REG_LC0', val)]
    if n == 1:
      return [IlSetRegister(4, 'HEX_REG_LC1', val)]
    assert (0)

  def macro_expr_fGETBYTE(self, args):
    # macros.h:
    # #define fGETBYTE(N, SRC) ((int8_t)((SRC >> ((N) * 8)) & 0xff))
    assert (len(args) == 2)
    assert (args[0].type == 'INTCON')
    n = int(args[0])
    src = self.lift_operand(args[1])
    src.signed = True
    if n == 0:
      return IlLowPart(1, src)
    return IlLowPart(1, IlArithShiftRight(src.size, src, IlConst(1, n * 8)))

  def macro_expr_fGETUBYTE(self, args):
    # macros.h:
    # #define fGETBYTE(N, SRC) ((uint8_t)((SRC >> ((N) * 8)) & 0xff))
    assert (len(args) == 2)
    assert (args[0].type == 'INTCON')
    n = int(args[0])
    src = self.lift_operand(args[1])
    src.signed = False
    if n == 0:
      return IlLowPart(1, src)
    return IlLowPart(1, IlLogicalShiftRight(src.size, src, IlConst(1, n * 8)))

  def macro_expr_fGETHALF(self, args):
    # macros.h:
    # #define fGETHALF(N, SRC) ((int16_t)((SRC >> ((N) * 16)) & 0xffff))
    assert (len(args) == 2)
    assert (args[0].type == 'INTCON')
    n = int(args[0])
    src = self.lift_operand(args[1])
    src.signed = True
    if n == 0:
      half = IlLowPart(2, src)
    else:
      half = IlLowPart(2, IlArithShiftRight(src.size, src, IlConst(1, n * 16)))
    return IlSignExtend(src.size, half)

  def macro_expr_fGETUHALF(self, args):
    # macros.h:
    # #define fGETUHALF(N, SRC) ((uint16_t)((SRC >> ((N) * 16)) & 0xffff))
    assert (len(args) == 2)
    assert (args[0].type == 'INTCON')
    n = int(args[0])
    src = self.lift_operand(args[1])
    src.signed = False
    if n == 0:
      half = IlLowPart(2, src)
    else:
      half = IlLowPart(2, IlLogicalShiftRight(src.size, src, IlConst(1,
                                                                     n * 16)))
    return IlZeroExtend(src.size, half)

  def macro_expr_fGETWORD(self, args):
    # macros.h:
    # #define fGETWORD(N, SRC) \
    #     ((int64_t)((int32_t)((SRC >> ((N) * 32)) & 0x0ffffffffLL)))
    assert (len(args) == 2)
    assert (args[0].type == 'INTCON')
    n = int(args[0])
    src = self.lift_operand(args[1])
    assert (src.size == 8)
    src.signed = True
    if n == 0:
      word = IlLowPart(4, src)
    else:
      word = IlLowPart(4, IlArithShiftRight(src.size, src, IlConst(1, n * 32)))
    return IlSignExtend(src.size, word)

  def macro_expr_fGETUWORD(self, args):
    # macros.h:
    # #define fGETWORD(N, SRC) \
    #     ((uint64_t)((uint32_t)((SRC >> ((N) * 32)) & 0x0ffffffffLL)))
    assert (len(args) == 2)
    assert (args[0].type == 'INTCON')
    n = int(args[0])
    src = self.lift_operand(args[1])
    assert (src.size == 8)
    src.signed = False
    if n == 0:
      word = IlLowPart(4, src)
    else:
      word = IlLowPart(4, IlLogicalShiftRight(src.size, src, IlConst(1,
                                                                     n * 32)))
    return IlZeroExtend(src.size, word)

  def macro_expr_fROTL4_4u(self, args):
    assert (len(args) == 2)
    src, shamt = list(map(self.lift_operand, args))
    assert (src.size == 4)
    return IlRotateLeft(src.size, src, shamt)

  def macro_expr_fROTL8_8u(self, args):
    assert (len(args) == 2)
    src, shamt = list(map(self.lift_operand, args))
    assert (src.size == 8)
    return IlRotateLeft(src.size, src, shamt)

  def macro_stmt_fSETHALF(self, args):
    # macros.h:
    # #define fSETHALF(N, DST, VAL) \
    #     do { \
    #         DST = (DST & ~(0x0ffffLL << ((N) * 16))) | \
    #         (((uint64_t)((VAL) & 0x0ffff)) << ((N) * 16)); \
    #     } while (0)
    assert (len(args) == 3)
    assert (args[0].type == 'INTCON')
    n = int(args[0])
    dst, val = list(map(self.lift_operand, args[1:]))
    assert (isinstance(dst, IlRegister) and dst.size == 4)
    old = IlAnd(
        dst.size, dst,
        IlNot(dst.size,
              IlShiftLeft(dst.size, IlConst(4, 0xffff), IlConst(1, n * 16))))
    new = IlShiftLeft(dst.size, IlAnd(dst.size, val, IlConst(4, 0xffff)),
                      IlConst(1, n * 16))
    return [IlSetRegister(dst.size, dst.reg, IlOr(dst.size, old, new))]

  def macro_stmt_fSETWORD(self, args):
    # macros.h:
    # #define fSETWORD(N, DST, VAL) \
    #     do { \
    #         DST = (DST & ~(0x0ffffffffLL << ((N) * 32))) | \
    #               (((VAL) & 0x0ffffffffLL) << ((N) * 32)); \
    #     } while (0)
    assert (len(args) == 3)
    assert (args[0].type == 'INTCON')
    n = int(args[0])
    dst, val = list(map(self.lift_operand, args[1:]))
    assert (isinstance(dst, IlRegister) and dst.size == 8)
    old = IlAnd(
        dst.size, dst,
        IlNot(dst.size,
              IlShiftLeft(dst.size, IlConst(4, 0xffffffff), IlConst(1,
                                                                    n * 32))))
    new = IlShiftLeft(dst.size, IlAnd(dst.size, val, IlConst(4, 0xffffffff)),
                      IlConst(1, n * 32))
    return [IlSetRegister(dst.size, dst.reg, IlOr(dst.size, old, new))]

  def macro_expr_fFRAME_SCRAMBLE(self, args):
    # This macro is always invoked with the same arguments:
    #   fFRAME_SCRAMBLE((fCAST8_8u(fREAD_LR()) << 32) | fCAST4_4u(fREAD_FP()))
    # Return a simpler expression using RegisterSplit.
    return IlRegisterSplit(4, 'HEX_REG_LR', 'HEX_REG_FP')

  def macro_expr_fREAD_PC(self, args):
    # macros.h:
    # #define fREAD_PC() (READ_REG(HEX_REG_PC))
    assert (len(args) == 0)
    return IlConstPointer(4, 'pc')

  def macro_expr_fREAD_LR(self, args):
    # macros.h:
    # #define fREAD_LR() (READ_REG(HEX_REG_LR))
    return IlRegister(4, 'HEX_REG_LR')

  def macro_expr_fREAD_FP(self, args):
    # macros.h:
    # #define fREAD_FP() (READ_REG(HEX_REG_FP))
    return IlRegister(4, 'HEX_REG_FP')

  def macro_expr_fREAD_SP(self, args):
    # macros.h:
    # #define fREAD_SP() (READ_REG(HEX_REG_SP))
    return IlRegister(4, 'HEX_REG_SP')

  def macro_expr_fREAD_GP(self, args):
    # macros.h:
    # #define fREAD_GP() \
    #     (insn->extension_valid ? 0 : READ_REG(HEX_REG_GP))
    #
    # Global pointer relative addresses can be expressed two ways in assembly language:
    #  * By explicitly adding an unsigned offset value to register GP.
    #  * By specifying only an immediate value as the instruction operand.
    return IlReadGP(4)

  def macro_expr_fREAD_P0(self, args):
    assert (len(args) == 0)
    return IlRegister(1, 'Pd0')

  def macro_expr_fREAD_LPCFG(self, args):
    assert (len(args) == 0)
    return IlRegister(1, 'HEX_REG_USR_LPCFG')

  def macro_expr_fREAD_LC(self, args):
    # macros.h
    # #define fREAD_LC0 (READ_REG(tmp, HEX_REG_LC0))
    # #define fREAD_LC1 (READ_REG(tmp, HEX_REG_LC1))
    assert (len(args) == 1)
    assert (args[0].type == 'INTCON')
    n = int(args[0])
    if n == 0:
      return IlRegister(4, 'HEX_REG_LC0')
    if n == 1:
      return IlRegister(4, 'HEX_REG_LC1')
    assert (0)

  def macro_expr_fREAD_SA(self, args):
    # macros.h
    # #define fREAD_SA0 (READ_REG(tmp, HEX_REG_SA0))
    # #define fREAD_SA1 (READ_REG(tmp, HEX_REG_SA1))
    assert (len(args) == 1)
    assert (args[0].type == 'INTCON')
    n = int(args[0])
    if n == 0:
      return IlRegister(4, 'HEX_REG_SA0')
    if n == 1:
      return IlRegister(4, 'HEX_REG_SA1')
    assert (0)

  def macro_expr_fCAST4s(self, args):
    # macros.h:
    # #define fCAST4s(A) ((int32_t)(A))
    assert (len(args) == 1)
    val = self.lift_operand(args[0])
    if val.size > 4:
      # cast down by truncating value.
      val.signed = True
      return IlLowPart(4, val)

    if val.size == 4:
      val.signed = True
      return val

    return IlSignExtend(4, val)

  def macro_expr_fCAST4u(self, args):
    # macros.h:
    # #define fCAST4u(A) ((uint32_t)(A))
    assert (len(args) == 1)
    val = self.lift_operand(args[0])
    if val.size > 4:
      # cast down by truncating value.
      val.signed = False
      return IlLowPart(4, val)

    if val.size == 4:
      val.signed = False
      return val

    return IlZeroExtend(4, val)

  def macro_expr_fCAST8s(self, args):
    # macros.h:
    # #define fCAST8s(A) ((int64_t)(A))
    assert (len(args) == 1)
    val = self.lift_operand(args[0])
    assert (val.size <= 8)
    if val.size == 8:
      val.signed = True
      return val
    return IlSignExtend(8, val)

  def macro_expr_fCAST8u(self, args):
    # macros.h:
    # #define fCAST8u(A) ((uint64_t)(A))
    assert (len(args) == 1)
    val = self.lift_operand(args[0])
    assert (val.size <= 8)
    if val.size == 8:
      val.signed = False
      return val
    return IlZeroExtend(8, val)

  def macro_expr_f8BITSOF(self, args):
    # macros.h
    # #define f8BITSOF(VAL) ((VAL) ? 0xff : 0x00)
    #
    # This macro is only used to write either 0/ff to an 8b predicate register:
    #   PdV = f8BITSOF((RsV & (1<<uiV)) != 0);
    # or,
    #   fWRITE_P0(f8BITSOF((fCAST4u(RsV)>RtV)))
    #
    # Predicate registers are only used as boolean registers, so instead of
    # storing the semantically correct 0/ff, store the result of a compare
    # operation - a boolean value.
    assert (len(args) == 1)
    val = self.lift_operand(args[0])
    is_bool = isinstance(val, IlCompareExpr)
    is_bool = is_bool or (isinstance(val, IlAnd) and val.b == IlConst(4, 1))
    assert (is_bool)
    return val

  def macro_expr_fLSBOLD(self, args):
    # macros.h
    # #define fLSBOLD(VAL)  ((VAL) & 1)
    # This is only used on predicate registers, and these have boolean
    # values (see comment in f8BITSOF).
    assert (len(args) == 1)
    val = self.lift_operand(args[0])
    assert (isinstance(val, IlRegister) and val.reg.startswith('P'))
    return val

  def macro_expr_fNEWREG_ST(self, args):
    assert (len(args) == 1)
    assert (args[0].type == 'REG_NEW')
    return self.lift_operand(args[0])

  def macro_expr_fNEWREG(self, args):
    assert (len(args) == 1)
    assert (args[0].type == 'REG_NEW')
    return self.lift_operand(args[0])

  def macro_expr_fLSBNEW(self, args):
    # macros.h:
    # #define fLSBNEW(PVAL)   (PVAL)
    assert (len(args) == 1)
    pval = self.lift_operand(args[0])
    if isinstance(pval, IlConst):
      if pval.val == '0':
        return IlRegister(1, 'Pd0')
      if pval.val == '1':
        return IlRegister(1, 'Pd1')
    return pval

  def macro_expr_fIMMEXT(self, args):
    # macros.h:
    #   #define fIMMEXT(IMM) (IMM = IMM)
    # no-op operation.
    assert (len(args) == 1)
    assert (args[0].type == 'IMM')
    return self.lift_operand(args[0])

  def macro_expr_fMAX(self, args):
    # macros.h:
    # #define fMAX(A, B) (((A) > (B)) ? (A) : (B))
    # IL does not support a ternary operator. Instead compute the following:
    # int max = (a >= b) * a + (a < b) * b;
    assert (len(args) == 2)
    a, b = list(map(self.lift_operand, args))
    assert (a.size == b.size)
    size = a.size
    if a.signed:
      return IlAdd(
          size,
          IlMult(size, IlBoolToInt(size,
                                   IlCompareSignedGreaterEqual(size, a, b)), a),
          IlMult(size, IlBoolToInt(size, IlCompareSignedLessThan(size, a, b)),
                 b))
    else:
      return IlAdd(
          size,
          IlMult(size,
                 IlBoolToInt(size, IlCompareUnsignedGreaterEqual(size, a, b)),
                 a),
          IlMult(size, IlBoolToInt(size, IlCompareUnsignedLessThan(size, a, b)),
                 b))

  def macro_expr_fMIN(self, args):
    # macros.h:
    # #define fMIN(A, B) (((A) < (B)) ? (A) : (B))
    # IL does not support a ternary operator. Instead compute the following:
    # int min = (a <= b) * a + (a > b) * b;
    assert (len(args) == 2)
    a, b = list(map(self.lift_operand, args))
    assert (a.size == b.size)
    size = a.size
    if a.signed:
      return IlAdd(
          size,
          IlMult(size, IlBoolToInt(size, IlCompareSignedLessEqual(size, a, b)),
                 a),
          IlMult(size, IlBoolToInt(size, IlCompareSignedGreaterThan(size, a,
                                                                    b)), b))
    else:
      return IlAdd(
          size,
          IlMult(size, IlBoolToInt(size, IlCompareUnsignedLessEqual(size, a,
                                                                    b)), a),
          IlMult(size,
                 IlBoolToInt(size, IlCompareUnsignedGreaterThan(size, a, b)),
                 b))

  def macro_expr_fABS(self, args):
    # macros.h:
    # #define fABS(A) (((A) < 0) ? (-(A)) : (A))
    # IL does not support a ternary operator. Instead compute the following:
    # int abs = (1 - 2*(a < 0)) * a;
    assert (len(args) == 1)
    a = self.lift_operand(args[0])
    if not a.signed:
      return a

    size = a.size
    return IlMult(
        size,
        IlSub(
            size, IlConst(size, 1),
            IlMult(
                size, IlConst(size, 2),
                IlBoolToInt(size,
                            IlCompareSignedLessThan(size, a, IlConst(size,
                                                                     0))))), a)

  def macro_expr_fBYTESWAP(self, args):
    assert (len(args) == 1)
    # Swizzle the bytes of a word.
    # uint32_t Byte0 = value & 0x000000FF;
    # uint32_t Byte1 = value & 0x0000FF00;
    # uint32_t Byte2 = value & 0x00FF0000;
    # uint32_t Byte3 = value & 0xFF000000;
    # return (Byte0 << 24) | (Byte1 << 8) | (Byte2 >> 8) | (Byte3 >> 24);
    x = self.lift_operand(args[0])
    assert (x.size == 4)
    b0 = IlAnd(x.size, x, IlConst(4, 0x000000ff))
    b1 = IlAnd(x.size, x, IlConst(4, 0x0000ff00))
    b2 = IlAnd(x.size, x, IlConst(4, 0x00ff0000))
    b3 = IlAnd(x.size, x, IlConst(4, 0xff000000))
    return IlOr(
        x.size, IlShiftLeft(x.size, b0, IlConst(1, 24)),
        IlOr(
            x.size, IlShiftLeft(x.size, b1, IlConst(1, 8)),
            IlOr(x.size, IlLogicalShiftRight(x.size, b2, IlConst(1, 8)),
                 IlLogicalShiftRight(x.size, b3, IlConst(1, 24)))))

  # | id "(" [expr ("," expr)* ] ")" ";" -> call_stmt
  @v_args(inline=False)
  def call_stmt(self, args):
    ident = args[0]
    if ident.type == 'MACRO':
      return getattr(self, 'macro_stmt_' + ident.value)(args[1:])
    assert (0)

  # | id "(" [expr ("," expr )* ] ")" -> call_expr
  @v_args(inline=False)
  def call_expr(self, args):
    ident = args[0]
    if ident.type == 'MACRO':
      return getattr(self, 'macro_expr_' + ident.value)(args[1:])
    assert (0)

  @v_args(inline=False)
  def fbody(self, args):
    # args is a list of lists of il instructions.
    # Unpack, and return a single list of il instructions.
    #  In : a = [[1, 2], ['a', 'b', 'c'], [3]]
    #  In : list(itertools.chain(*a))
    #  Out: [1, 2, 'a', 'b', 'c', 3]
    return list(itertools.chain(*args))

  # | "{" stmt* "}" -> multi_stmt
  @v_args(inline=False)
  def multi_stmt(self, args):
    # args is a list of lists of il instructions.
    # Unpack, and return a single list of il instructions.
    #  In : a = [[1, 2], ['a', 'b', 'c'], [3]]
    #  In : list(itertools.chain(*a))
    #  Out: [1, 2, 'a', 'b', 'c', 3]
    return list(itertools.chain(*args))

  # | "CANCEL;" -> cancel_stmt
  @v_args(inline=False)
  def cancel_stmt(self, args):
    return []

  # | ";" -> empty_stmt
  @v_args(inline=False)
  def empty_stmt(self, args):
    return []

  # ?stmt: "if" "(" expr ")" stmt [ "else" stmt ] -> if_stmt
  @v_args(inline=False)
  def if_stmt(self, args):
    assert (len(args) in [2, 3])
    cond, tstmt = args[:2]
    fstmt = args[2] if len(args) == 3 else []
    ret = []
    if fstmt:
      ret += [RawC('''{ LowLevelILLabel true_case, false_case, done;''')]
      ret += [IlIf(cond, 'true_case', 'false_case')]
      ret += [IlLabel('true_case')]
      ret += tstmt
      ret += [IlGoto('done')]
      ret += [IlLabel('false_case')]
      ret += fstmt
      ret += [IlLabel('done')]
      ret += [RawC('''}''')]
    else:
      ret += [RawC('''{ LowLevelILLabel true_case, done;''')]
      ret += [IlIf(cond, 'true_case', 'done')]
      ret += [IlLabel('true_case')]
      ret += tstmt
      ret += [IlLabel('done')]
      ret += [RawC('''}''')]
    return ret

  #   | expr "?" "(" assg ")" ":" "(" assg ")" -> ternary_stmt
  @v_args(inline=False)
  def ternary_stmt(self, args):
    assert (len(args) == 3)
    return self.if_stmt(args)

  #   | assg ";" -> assg_stmt
  @v_args(inline=True)
  def assg_stmt(self, stmt):
    return stmt

  # | id ASSGOP expr ";" -> assg_binop_stmt
  @v_args(inline=True)
  def assg_binop_stmt(self, lvalue, op, rvalue):
    lvalue = self.lift_operand(lvalue)
    rvalue = self.lift_operand(rvalue)
    if op == '+=':
      # a += b => a = a + b;
      return self.assg(lvalue, IlAdd(lvalue.size, lvalue, rvalue))
    if op == '-=':
      # a -= b => a = a - b;
      return self.assg(lvalue, IlSub(lvalue.size, lvalue, rvalue))
    if op == '&=':
      # a &= b => a = a & b;
      return self.assg(lvalue, IlAnd(lvalue.size, lvalue, rvalue))
    if op == '^=':
      # a ^= b => a = a ^ b;
      return self.assg(lvalue, IlXor(lvalue.size, lvalue, rvalue))
    if op == '|=':
      # a |= b => a = a | b;
      return self.assg(lvalue, IlOr(lvalue.size, lvalue, rvalue))
    assert (0)

  # ?assg: id "=" expr
  @v_args(inline=True)
  def assg(self, lvalue, rvalue):
    lvalue = self.lift_operand(lvalue)
    rvalue = self.lift_operand(rvalue)
    assert (isinstance(lvalue, IlRegister))
    return [IlSetRegister(lvalue.size, lvalue.reg, rvalue)]

  # ?expr: "-" expr        -> neg_expr
  @v_args(inline=False)
  def neg_expr(self, args):
    assert (len(args) == 1)
    val = self.lift_operand(args[0])
    return IlNeg(val.size, val)

  # | "!" expr        -> not_expr
  def not_expr(self, args):
    assert (len(args) == 1)
    val = self.lift_operand(args[0])
    return IlNot(val.size, val)

  # | "~" expr        -> bit_not_expr
  def bit_not_expr(self, args):
    assert (len(args) == 1)
    val = self.lift_operand(args[0])
    return IlNot(val.size, val)

  # | expr BINOP expr -> expr_binop
  @v_args(inline=True)
  def expr_binop(self, op1, binop, op2):
    assert (binop.type == 'BINOP')
    op1, op2 = list(map(self.lift_operand, [op1, op2]))

    if (binop.value == '+'):
      return IlAdd(op1.size, op1, op2)

    if (binop.value == '-'):
      return IlSub(op1.size, op1, op2)

    if (binop.value == '*'):
      return IlMult(op1.size, op1, op2)

    if (binop.value == '|'):
      return IlOr(op1.size, op1, op2)

    if (binop.value == '&'):
      return IlAnd(op1.size, op1, op2)

    if (binop.value == '^'):
      return IlXor(op1.size, op1, op2)

    if (binop.value == '<<'):
      return IlShiftLeft(op1.size, op1, op2)

    if (binop.value == '>>'):
      if op1.signed:
        return IlArithShiftRight(op1.size, op1, op2)
      else:
        return IlLogicalShiftRight(op1.size, op1, op2)

    assert (0)

  # | expr RELOP expr -> expr_relop
  @v_args(inline=True)
  def expr_relop(self, op1, relop, op2):
    assert (relop.type == 'RELOP')
    op1, op2 = list(map(self.lift_operand, [op1, op2]))

    if (relop.value == '=='):
      return IlCompareEqual(op1.size, op1, op2)

    if (relop.value == '!='):
      return IlCompareNotEqual(op1.size, op1, op2)

    if (relop.value == '<='):
      if op1.signed:
        return IlCompareSignedLessEqual(op1.size, op1, op2)
      else:
        return IlCompareUnsignedLessEqual(op1.size, op1, op2)

    if (relop.value == '<'):
      if op1.signed:
        return IlCompareSignedLessThan(op1.size, op1, op2)
      else:
        return IlCompareUnsignedLessThan(op1.size, op1, op2)

    if (relop.value == '>='):
      if op1.signed:
        return IlCompareSignedGreaterEqual(op1.size, op1, op2)
      else:
        return IlCompareUnsignedGreaterEqual(op1.size, op1, op2)

    if (relop.value == '>'):
      if op1.signed:
        return IlCompareSignedGreaterThan(op1.size, op1, op2)
      else:
        return IlCompareUnsignedGreaterThan(op1.size, op1, op2)

    assert (0)

  # | id "[" expr "]" -> unexpected
  @v_args(inline=False)
  def unexpected(self, args):
    raise ValueError('Unexpected grammar rule in insn semantics')


def genptr_decl(tag, regtype, regid, regno):
  mapped_regno = 'MapRegNum(\'{0}\', insn.regno[{1}])'.format(regtype, regno)
  if (regtype == 'R'):
    # GPT register
    if (regid in {'ss', 'tt'}):
      # Source register pair (read-only).
      return [
          RawC('''SourcePairReg tmp_{0}{1}V({2}, il);
                  const int {0}{1}V = tmp_{0}{1}V.Reg();'''.format(
              regtype, regid, mapped_regno))
      ]

    if (regid in {'dd', 'ee'}):
      # Destination register pair (write-only).
      return [
          RawC('''const int {0}{1}V = ctx.AddDestWriteOnlyRegPair({2});'''
               .format(regtype, regid, mapped_regno))
      ]

    if (regid in {'xx', 'yy'}):
      # Destination register pair (read-write).
      return [
          RawC('''const int {0}{1}V = ctx.AddDestReadWriteRegPair({2});'''
               .format(regtype, regid, mapped_regno))
      ]

    if (regid in {'s', 't', 'u', 'v'}):
      # Source register (read-only).
      return [
          RawC('''const int {0}{1}V = {2};'''.format(regtype, regid,
                                                     mapped_regno))
      ]

    if (regid in {'d', 'e'}):
      # Destination register (write-only).
      return [
          RawC('''const int {0}{1}V = ctx.AddDestWriteOnlyReg({2});'''.format(
              regtype, regid, mapped_regno))
      ]

    if (regid in {'x', 'y'}):
      # Destination register (read-write).
      return [
          RawC('''const int {0}{1}V = ctx.AddDestReadWriteReg({2});'''.format(
              regtype, regid, mapped_regno))
      ]

  if (regtype == 'P'):
    if (regid in {'s', 't', 'u', 'v'}):
      # Source register (read-only).
      return [
          RawC('''const int {0}{1}V = {2};'''.format(regtype, regid,
                                                     mapped_regno))
      ]

    if (regid in {'d', 'e'}):
      # Destination register (write-only).
      return [
          RawC('''const int {0}{1}V = ctx.AddDestWriteOnlyPredReg({2});'''
               .format(regtype, regid, mapped_regno))
      ]

    if (regid in {'x'}):
      # Destination register (read-write).
      return [
          RawC('''const int {0}{1}V = ctx.AddDestReadWritePredReg({2});'''
               .format(regtype, regid, mapped_regno))
      ]

  if (regtype == 'C'):
    # Control register
    if (regid in {'ss'}):
      # Source register pair (read-only).
      return [
          RawC('''SourcePairReg tmp_{0}{1}V({2}, il);
                  const int {0}{1}V = tmp_{0}{1}V.Reg();'''.format(
              regtype, regid, mapped_regno))
      ]

    if (regid in {'dd'}):
      # Destination register pair (write-only).
      return [
          RawC('''const int {0}{1}V = ctx.AddDestWriteOnlyRegPair({2});'''
               .format(regtype, regid, mapped_regno))
      ]

    if (regid in {'s'}):
      # Source register (read-only).
      return [
          RawC('''const int {0}{1}V = {2};'''.format(regtype, regid,
                                                     mapped_regno))
      ]

    if (regid in {'d'}):
      # Destination register (write-only).
      return [
          RawC('''const int {0}{1}V = ctx.AddDestWriteOnlyReg({2});'''.format(
              regtype, regid, mapped_regno))
      ]

  assert (0)


def genptr_decl_new(regtype, regid, regno):
  mapped_regno = 'MapRegNum(\'{0}\', insn.regno[{1}])'.format(regtype, regno)
  if (regtype == 'N'):
    # GPT register
    assert (regid in {'s', 't'})
    return [
        RawC('''const int {0}{1}N = ctx.AddDestWriteOnlyReg({2});'''.format(
            regtype, regid, mapped_regno))
    ]

  if (regtype == 'P'):
    assert (regid in {'t', 'u', 'v'})
    return [
        RawC('''const int {0}{1}N = ctx.AddDestWriteOnlyPredReg({2});'''.format(
            regtype, regid, mapped_regno))
    ]

  assert (0)


def genptr_decl_opn(tag, regtype, regid, toss, numregs, i):
  if (is_pair(regid)):
    return genptr_decl(tag, regtype, regid, i)

  assert (is_single(regid))
  if is_old_val(regtype, regid, tag):
    return genptr_decl(tag, regtype, regid, i)

  assert (is_new_val(regtype, regid, tag))
  return genptr_decl_new(regtype, regid, i)


def genptr_decl_imm(immlett):
  i = 1 if immlett.isupper() else 0
  return [RawC('''int {0} = insn.immed[{1}];'''.format(imm_name(immlett), i))]


def set_overrides():
  for tag in behoverrides:
    behdict[tag] = behoverrides[tag]
  for tag in semoverrides:
    semdict[tag] = semoverrides[tag]


def preprocess_semantics(tag):
  sem = semdict[tag]

  cpreprocessor = Preprocessor()

  # Remove no-op macros.
  cpreprocessor.define(
      'fBRANCH_SPECULATE_STALL(DOTNEWVAL, JUMP_COND, SPEC_DIR, HINTBITNUM, STRBITNUM)'
  )
  cpreprocessor.define('fHIDE(A)')
  cpreprocessor.define('CANCEL')
  cpreprocessor.define('LOAD_CANCEL(A)')
  cpreprocessor.define('STORE_CANCEL(A)')
  cpreprocessor.define('fFRAMECHECK(ADDR, EA)')
  cpreprocessor.define('fBARRIER()')
  cpreprocessor.define('fSYNCH()')
  cpreprocessor.define('fISYNC()')
  cpreprocessor.define('fICFETCH(REG)')
  cpreprocessor.define('fDCFETCH(REG)')
  cpreprocessor.define('fICINVA(REG)')
  cpreprocessor.define('fL2FETCH(ADDR, HEIGHT, WIDTH, STRIDE, FLAGS)')
  cpreprocessor.define('fDCCLEANA(REG)')
  cpreprocessor.define('fDCCLEANINVA(REG)')
  cpreprocessor.define('fDCINVA(REG)')

  # Refactor and simplify macros.
  cpreprocessor.define('fFRAME_UNSCRAMBLE(VAL) VAL')
  cpreprocessor.define('fECHO(A) A')
  cpreprocessor.define('fLSBOLDNOT(VAL) !fLSBOLD(VAL)')
  cpreprocessor.define('fCONSTLL(A) fCAST8s(A)')
  cpreprocessor.define('fPAUSE(IMM)')

  # zero/sign extend.
  cpreprocessor.define('fZXTN(N, M, VAL) ((VAL) & ((1<<(N))-1))')
  cpreprocessor.define(
      'fSXTN(N, M, VAL) ((fZXTN(N,M,VAL) ^ (1<<((N)-1))) - (1<<((N)-1)))')

  # Special branch macros.
  cpreprocessor.define('fCALL(A) { fBRANCH(A, COF_TYPE_CALL); }')
  cpreprocessor.define('fCALLR(A) { fBRANCH(A, COF_TYPE_CALLR); }')

  # Effective Address (EA) register macros.
  cpreprocessor.define('fEA_RI(REG, IMM) { EA = REG + IMM; }')
  cpreprocessor.define(
      'fEA_RRs(REG, REG2, SCALE) { EA = REG + (REG2 << SCALE); }')
  cpreprocessor.define(
      'fEA_IRs(IMM, REG, SCALE) { EA = IMM + (REG << SCALE); }')
  cpreprocessor.define('fEA_IMM(IMM) { EA = (IMM); }')
  cpreprocessor.define('fEA_REG(REG) { EA = (REG); }')
  cpreprocessor.define('fEA_GPI(IMM) { EA = (fREAD_GP() + (IMM)); }')
  cpreprocessor.define('fPM_I(REG, IMM) { REG = REG + (IMM); }')
  cpreprocessor.define('fPM_M(REG, MVAL) { REG = REG + (MVAL); }')

  # Bit operations.
  cpreprocessor.define('fCAST4_4s(A) fCAST4s(A)')
  cpreprocessor.define('fCAST4_4u(A) fCAST4u(A)')
  cpreprocessor.define('fCAST8_8s(A) fCAST8s(A)')
  cpreprocessor.define('fCAST8_8u(A) fCAST8u(A)')
  cpreprocessor.define(
      'fASHIFTL(SRC, SHAMT, REGSTYPE) (fCAST##REGSTYPE##s(SRC) << (SHAMT))')
  cpreprocessor.define(
      'fASHIFTR(SRC, SHAMT, REGSTYPE) (fCAST##REGSTYPE##s(SRC) >> (SHAMT))')
  cpreprocessor.define(
      'fLSHIFTR(SRC, SHAMT, REGSTYPE) (fCAST##REGSTYPE##u(SRC) >> (SHAMT))')
  cpreprocessor.define(
      'fROTL(SRC, SHAMT, REGSTYPE) (fROTL##REGSTYPE##u(SRC, SHAMT))')

  # Multiply operations.
  cpreprocessor.define('fSE32_64(A) (fCAST8s(fCAST4s(A)))')
  cpreprocessor.define('fZE32_64(A) (fCAST8u(fCAST4u(A)))')
  cpreprocessor.define('fMPY32SS(A, B) (fSE32_64(A) * fSE32_64(B))')
  cpreprocessor.define('fMPY32UU(A, B) (fZE32_64(A) * fZE32_64(B))')
  cpreprocessor.define('fMPY32SU(A, B) (fSE32_64(A) * fZE32_64(B))')

  # Replace macro identifiers with call expressions.
  cpreprocessor.define('fLSBNEW0 fLSBNEW(0)')
  cpreprocessor.define('fLSBNEW1 fLSBNEW(1)')
  cpreprocessor.define('fLSBNEW0NOT !fLSBNEW(0)')
  cpreprocessor.define('fLSBNEW1NOT !fLSBNEW(1)')
  cpreprocessor.define('fLSBNEWNOT(PNUM) !fLSBNEW(PNUM)')
  cpreprocessor.define('fGET_LPCFG fREAD_LPCFG()')
  cpreprocessor.define('fREAD_SA0 fREAD_SA(0)')
  cpreprocessor.define('fREAD_SA1 fREAD_SA(1)')
  cpreprocessor.define('fREAD_LC0 fREAD_LC(0)')
  cpreprocessor.define('fREAD_LC1 fREAD_LC(1)')
  cpreprocessor.define('fWRITE_LC0(VAL) fWRITE_LC(0, VAL)')
  cpreprocessor.define('fWRITE_LC1(VAL) fWRITE_LC(1, VAL)')
  cpreprocessor.define(
      'fWRITE_LOOP_REGS0(START, COUNT) fWRITE_LOOP_REGS(0, START, COUNT)')
  cpreprocessor.define(
      'fWRITE_LOOP_REGS1(START, COUNT) fWRITE_LOOP_REGS(1, START, COUNT)')

  # Locked load/store.
  cpreprocessor.define(
      'fLOAD_LOCKED(NUM, SIZE, SIGN, EA, DST) fLOAD(NUM, SIZE, SIGN, EA, DST);')
  cpreprocessor.define(
      'fSTORE_LOCKED(NUM, SIZE, EA, SRC, PRED) fSTORE_LOCKED(NUM, SIZE, EA, SRC, PRED);'
  )

  # Immext.
  cpreprocessor.define('fMUST_IMMEXT(IMM) fIMMEXT(IMM)')

  parts = []
  if 'A_NEWCMPJUMP' in attribdict[tag]:
    # Extract compare part of a compare-jump instruction.
    cpreprocessor.define('fPART1(WORK) */{ WORK; }/*')
    clean = ''.join([tok.value for tok in cpreprocessor.parsegen(sem)])
    clean = ''.join(
        [tok.value for tok in cpreprocessor.parsegen('/*' + clean + '*/')])
    parts.append(clean)

  # Remove compare part of a compound compare-jump instruction.
  cpreprocessor.define('fPART1(WORK)')
  clean = ''.join([tok.value for tok in cpreprocessor.parsegen(sem)])
  clean = ''.join([tok.value for tok in cpreprocessor.parsegen(clean)])
  parts.append(clean)
  return parts


def genptr_decl_fixed_pred(parts):
  ret = []
  seen = set()

  cpreprocessor = Preprocessor()
  cpreprocessor.define('fLSBNEW(PVAL) */PVAL/*')
  cpreprocessor.define('fWRITE_P0(PVAL) */0/*')
  cpreprocessor.define('fWRITE_P1(PVAL) */1/*')
  cpreprocessor.define('fWRITE_P2(PVAL) */2/*')
  cpreprocessor.define('fWRITE_P3(PVAL) */3/*')
  cpreprocessor.define('fREAD_P0(PVAL)  */0/*')
  for sem in parts:
    clean = ''.join([tok.value for tok in cpreprocessor.parsegen(sem)])
    clean = ''.join(
        [tok.value for tok in cpreprocessor.parsegen('/*' + clean + '*/')])
    pid = clean.strip()
    if pid != '' and pid in '0123' and pid not in seen:
      ret += [
          RawC(
              '''const int Pd{0} = ctx.AddDestReadWritePredReg(MapRegNum('P', {0}));'''
              .format(pid))
      ]
      seen.add(pid)
  return ret


def process_semantics(tag, sem):
  tree = semantics_parser.parse(sem)
  return SemanticsTreeTransformer(tag).transform(tree)


def gen_il_func(tag, regs, imms):
  ## Declare all the operands (regs and immediates)
  prog = []
  for i, (regtype, regid, toss, numregs) in enumerate(regs):
    prog += genptr_decl_opn(tag, regtype, regid, toss, numregs, i)
  for immlett, bits, immshift in imms:
    prog += genptr_decl_imm(immlett)

  parts = preprocess_semantics(tag)
  prog += genptr_decl_fixed_pred(parts)

  if len(parts) > 1:
    part1, part2 = parts
    prog += [RawC('''if (insn.part1) {''')]
    prog += process_semantics(tag, part1)
    prog += [RawC('''} else {''')]
    prog += process_semantics(tag, part2)
    prog += [RawC('''}''')]

  else:
    prog += process_semantics(tag, parts[0])

  lines = []
  for il_insn in prog:
    if isinstance(il_insn, IlBranch):
      # Branch instructions are deferred to the end of the packet.
      continue
    elif isinstance(il_insn, IlExprId):
      lines.append('''il.AddInstruction({0});'''.format(il_insn))
    elif isinstance(il_insn, IlLabel):
      lines.append('''il.MarkLabel({0});'''.format(il_insn))
    elif isinstance(il_insn, RawC):
      lines.append(il_insn)
    else:
      assert (0)

  return '\n'.join(lines)


def main():
  read_semantics_file(sys.argv[1])
  read_attribs_file(sys.argv[2])
  set_overrides()
  calculate_attribs()
  tagregs = get_tagregs()
  tagimms = get_tagimms()

  f = StringIO()

  f.write('''
#include "binaryninjaapi.h"
#include "third_party/qemu-hexagon/attribs.h"
#include "third_party/qemu-hexagon/iclass.h"
#include "third_party/qemu-hexagon/insn.h"
#include "third_party/qemu-hexagon/opcodes.h"
#include "plugin/packet_context.h"
#include "plugin/hex_regs.h"
#include "glog/logging.h"

using namespace BinaryNinja;

#define PCALIGN 4
#define PCALIGN_MASK (PCALIGN - 1)

#define EA_REG  LLIL_TEMP(100)
#define TMP_REG LLIL_TEMP(101)
#define WIDTH_REG LLIL_TEMP(104)
#define OFFSET_REG LLIL_TEMP(105)
#define SHAMT_REG LLIL_TEMP(106)

''')

  for tag in SUPPORTED_TAGS:
    f.write('''/*\n{0}:\n{1}\n{2}\n*/\n'''.format(tag, behdict[tag],
                                                  semdict[tag]))
    f.write('''void lift_{0}(Architecture *arch,
                             uint64_t pc,
                             const Packet &pkt,
                             const Insn &insn,
                             int insn_num,
                             PacketContext &ctx) {{
                LowLevelILFunction &il = ctx.IL();\n'''.format(tag))
    f.write(gen_il_func(tag, tagregs[tag], tagimms[tag]))
    f.write('}\n\n')

  f.write('''typedef void (*IlLiftFunc)(Architecture *arch,
                                        uint64_t pc,
                                        const Packet &pkt,
                                        const Insn &insn,
                                        int insn_num,
                                        PacketContext &ctx);\n\n''')
  f.write('extern const IlLiftFunc opcode_liftptr[XX_LAST_OPCODE] = {\n')
  supported_set = set(SUPPORTED_TAGS)
  for tag in tags:
    if tag in supported_set:
      f.write('[{0}] = lift_{0},\n'.format(tag))
    else:
      f.write('[{0}] = nullptr,\n'.format(tag))
  f.write('};\n')

  realf = open(sys.argv[3], 'w')
  realf.write(f.getvalue())
  realf.close()
  f.close()


if __name__ == '__main__':
  main()

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

import unittest
import os

try:
  import binaryninja as binja
except ImportError:
  print('Failed to import binaryninja Python API.')
  print('Add ${BN_INSTALL_DIR}/python to PYTHONPATH.')
  sys.exit(1)


# E2E test for Hexagon llil plugin.
# This test uses Binary Ninja headless API, analyses test_binaries/bn_llil_test_app.s
# and checks the LLIL output.
class TestPluginIl(unittest.TestCase):
  TARGET_FILE = None

  @classmethod
  def setUpClass(cls):
    assert (cls.TARGET_FILE is not None)
    binja.log.log_to_stdout(True)
    cls.bv = binja.BinaryViewType.get_view_of_file(cls.TARGET_FILE)
    cls.maxDiff = None

  def get_function(self, name):
    sym = TestPluginIl.bv.get_symbol_by_raw_name(name)
    return TestPluginIl.bv.get_function_at(sym.address)

  def list_asm(self, func):
    ret = ['']
    for block in func.basic_blocks:
      for insn in block:
        # Assemble tokens
        ret.append(''.join(list(map(str, insn[0]))).strip())
    return '\n'.join(ret)

  def list_llil(self, func):
    ret = ['']
    for block in func.llil:
      for insn in block:
        ret.append('{0}: {1}'.format(insn.instr_index, insn))
    return '\n'.join(ret)

  # Tests allocframe, deallocframe, return tag overrides.
  def test_allocframe(self):
    func = self.get_function('test_allocframe')
    self.assertEqual(
        self.list_asm(func), '''
{ allocframe(SP,#0x8):raw }
{ R0 = #0x100 }
{ LR:FP = dealloc_return(FP):raw }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp29.d = SP {arg_0}
1: temp100.d = temp29.d - 8
2: [temp100.d {var_8}].q = LR:FP
3: FP = temp100.d
4: temp29.d = temp100.d - 8 {var_10}
5: SP = temp29.d
6: temp0.d = 0x100
7: R0 = temp0.d
8: temp100.d = FP {var_8}
9: temp101.q = [temp100.d {var_8}].q
10: temp30.q = temp101.q
11: SP = temp100.d + 8
12: LR:FP = temp30.q
13: <return> jump(LR)''')

  # Source pair operations use temporary 64b registers.
  def test_pair_operations(self):
    func = self.get_function('test_pair_operations')
    self.assertEqual(
        self.list_asm(func), '''
{ R5:R4 = add(R3:R2,R9:R8) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp102.q = R3:R2
1: temp108.q = R9:R8
2: temp4.q = temp102.q + temp108.q
3: R5:R4 = temp4.q
4: temp200.d = LR
5: <return> jump(LR)''')

  # Tests writes to P0 predicate register go to a temporary register.
  # Result is written back at the end of the packet.
  def test_cmp_to_predicate(self):
    func = self.get_function('test_cmp_to_predicate')
    self.assertEqual(
        self.list_asm(func), '''
{ P0 = cmp.eq(R0,#0x1) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp90.b = R0 == 1
1: P0 = temp90.b
2: temp200.d = LR
3: <return> jump(LR)''')

  def test_memory_load(self):
    func = self.get_function('test_memory_load')
    self.assertEqual(
        self.list_asm(func), '''
{ immext(#0x30400)
R1 = ##0x30400 }
{ R2 = memb(R1+#0x1) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp1.d = 0x30400
1: R1 = temp1.d
2: temp100.d = R1 + 1
3: temp2.d = sx.d([temp100.d {0x30401}].b)
4: R2 = temp2.d
5: temp200.d = LR
6: <return> jump(LR)''')

  def test_memory_store(self):
    func = self.get_function('test_memory_store')
    self.assertEqual(
        self.list_asm(func), '''
{ immext(#0x123440)
memw(R1+#0x0) = ##0x123456 }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp100.d = R1
1: [temp100.d].d = 0x123456
2: temp200.d = LR
3: <return> jump(LR)''')

  # r3.new operand in the second instruction packet uses the temporary
  # register for r3.
  def test_store_dotnew(self):
    func = self.get_function('test_store_dotnew')
    self.assertEqual(
        self.list_asm(func), '''
{ R3 = add(R1,R2)
memw(R5+#0x0) = R3.new }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp3.d = R1 + R2
1: temp100.d = R5
2: [temp100.d].d = temp3.d
3: R3 = temp3.d
4: temp200.d = LR
5: <return> jump(LR)''')

  def test_mux(self):
    func = self.get_function('test_mux')
    self.assertEqual(
        self.list_asm(func), '''
{ R0 = mux(P0,#0x1,#0x0) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: if (P0) then 1 else 3
1: temp0.d = 1
2: goto 5
3: temp0.d = 0
4: goto 5
5: R0 = temp0.d
6: temp200.d = LR
7: <return> jump(LR)''')

  def test_tstbit(self):
    func = self.get_function('test_tstbit')
    self.assertEqual(
        self.list_asm(func), '''
{ P0 = tstbit(R0,#0x0) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp90.b = (R0 & 1 << 0) != 0
1: P0 = temp90.b
2: temp200.d = LR
3: <return> jump(LR)''')

  def test_dualjump_direct_jump(self):
    func = self.get_function('test_dualjump_direct_jump')
    self.assertEqual(
        self.list_asm(func), '''
{ R1 = add(R1,R1)
jump 0x20174 }
{ R0 = #0x1; jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp1.d = R1 + R1
1: R1 = temp1.d
2: jump(0x20174 => 3 @ 0x20174)
3: temp0.d = 1
4: R0 = temp0.d
5: <return> jump(LR)''')

  def test_dualjump_cond_jump(self):
    func = self.get_function('test_dualjump_cond_jump')
    self.assertEqual(
        self.list_asm(func), '''
{ R1 = add(R1,R1)
if (P0) jump:t 0x20184 }
{ R0 = #0x1; jumpr LR }
{ R0 = #0x0; jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp211.b = 0
1: temp1.d = R1 + R1
2: if (P0) then 3 else 5
3: temp211.b = 1
4: goto 5
5: R1 = temp1.d
6: if (temp211.b == 1) then 7 else 8
7: jump(0x20184 => 9 @ 0x20184)
8: goto 12 @ 0x20180
9: temp0.d = 1
10: R0 = temp0.d
11: <return> jump(LR)
12: temp0.d = 0
13: R0 = temp0.d
14: <return> jump(LR)''')

  def test_dualjump_cond_jump_with_direct_jump(self):
    func = self.get_function('test_dualjump_cond_jump_with_direct_jump')
    self.assertEqual(
        self.list_asm(func), '''
{ if (P0) jump:t 0x20194
jump 0x20198
R1 = add(R1,R1) }
{ R0 = #0x1; jumpr LR }
{ R0 = #0x2; jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp210.b = 0
1: if (P0) then 2 else 4
2: temp210.b = 1
3: goto 4
4: temp1.d = R1 + R1
5: R1 = temp1.d
6: if (temp210.b == 1) then 7 else 8
7: jump(0x20194 => 9 @ 0x20194, 12 @ 0x20198)
8: jump(0x20198)
9: temp0.d = 1
10: R0 = temp0.d
11: <return> jump(LR)
12: temp0.d = 2
13: R0 = temp0.d
14: <return> jump(LR)''')

  def test_dualjump_two_cond_jumps(self):
    func = self.get_function('test_dualjump_two_cond_jumps')
    self.assertEqual(
        self.list_asm(func), '''
{ if (P0) jump:t 0x201ac
if (!P1) jump:t 0x201b0
R1 = add(R1,R1) }
{ R0 = #0x1; jumpr LR }
{ R0 = #0x0; jumpr LR }
{ R1 = #0x2; jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp210.b = 0
1: temp211.b = 0
2: if (P0) then 3 else 5
3: temp210.b = 1
4: goto 5
5: if (not.b(P1)) then 6 else 8
6: temp211.b = 1
7: goto 8
8: temp1.d = R1 + R1
9: R1 = temp1.d
10: if (temp210.b == 1) then 11 else 12
11: jump(0x201ac => 13 @ 0x201ac, 16 @ 0x201b0)
12: if (temp211.b == 1) then 19 else 20
13: temp0.d = 1
14: R0 = temp0.d
15: <return> jump(LR)
16: temp1.d = 2
17: R1 = temp1.d
18: <return> jump(LR)
19: jump(0x201b0)
20: goto 21 @ 0x201a8
21: temp0.d = 0
22: R0 = temp0.d
23: <return> jump(LR)''')

  def test_dualjump_direct_call(self):
    func = self.get_function('test_dualjump_direct_call')
    self.assertEqual(
        self.list_asm(func), '''
{ call 0x201c4
R0 = add(R1,R0) }
{ nop
jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp0.d = R1 + R0
1: R0 = temp0.d
2: call(0x201c4)
3: goto 4 @ 0x201bc
4: temp201.d = LR
5: <return> jump(LR)''')

  def test_dualjump_direct_call_reorder(self):
    func = self.get_function('test_dualjump_direct_call_reorder')
    self.assertEqual(
        self.list_asm(func), '''
{ call 0x201d8
memw(R2+#0x0) = R3 }
{ nop
jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp100.d = R2
1: [temp100.d].d = R3
2: call(0x201d8)
3: goto 4 @ 0x201d0
4: temp201.d = LR
5: <return> jump(LR)''')

  def test_dualjump_cond_call(self):
    func = self.get_function('test_dualjump_cond_call')
    self.assertEqual(
        self.list_asm(func), '''
{ if (P0) call 0x201e8
R1 = add(R1,R1) }
{ R0 = #0x0; jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp210.b = 0
1: if (P0) then 2 else 4
2: temp210.b = 1
3: goto 4
4: temp1.d = R1 + R1
5: R1 = temp1.d
6: if (temp210.b == 1) then 7 else 9 @ 0x201e4
7: call(0x201e8)
8: goto 9 @ 0x201e4
9: temp0.d = 0
10: R0 = temp0.d
11: <return> jump(LR)''')

  def test_dualjump_cond_call_with_direct_jump(self):
    func = self.get_function('test_dualjump_cond_call_with_direct_jump')
    self.assertEqual(
        self.list_asm(func), '''
{ if (P0) call 0x201f8
jump 0x201fc
R1 = add(R1,R1) }
{ R0 = #0x2; jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp210.b = 0
1: if (P0) then 2 else 4
2: temp210.b = 1
3: goto 4
4: temp1.d = R1 + R1
5: R1 = temp1.d
6: if (temp210.b == 1) then 7 else 9
7: call(0x201f8)
8: goto 10
9: jump(0x201fc => 11 @ 0x201fc)
10: <return> tailcall(0x201f8)
11: temp0.d = 2
12: R0 = temp0.d
13: <return> jump(LR)''')

  def test_dualjump_cmp_jump(self):
    func = self.get_function('test_dualjump_cmp_jump')
    self.assertEqual(
        self.list_asm(func), '''
{ R1 = add(R1,R1)
P0 = cmp.eq(R3,#0x2);if (P0.new) jump:t 0x2020c }
{ R0 = #0x1; jumpr LR }
{ R0 = #0x0; jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp212.b = 0
1: temp90.b = P0
2: temp90.b = R3 == 2
3: temp1.d = R1 + R1
4: if (temp90.b) then 5 else 7
5: temp212.b = 1
6: goto 7
7: R1 = temp1.d
8: P0 = temp90.b
9: if (temp212.b == 1) then 10 else 11
10: jump(0x2020c => 12 @ 0x2020c)
11: goto 15 @ 0x20208
12: temp0.d = 1
13: R0 = temp0.d
14: <return> jump(LR)
15: temp0.d = 0
16: R0 = temp0.d
17: <return> jump(LR)''')

  def test_dualjump_cmp_jump_with_direct_jump(self):
    func = self.get_function('test_dualjump_cmp_jump_with_direct_jump')
    self.assertEqual(
        self.list_asm(func), '''
{ P0 = cmp.eq(R3,#0x2);if (P0.new) jump:t 0x2021c
jump 0x20220
R1 = add(R1,R1) }
{ R0 = #0x1; jumpr LR }
{ R0 = #0x2; jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp211.b = 0
1: temp90.b = P0
2: temp90.b = R3 == 2
3: if (temp90.b) then 4 else 6
4: temp211.b = 1
5: goto 6
6: temp1.d = R1 + R1
7: R1 = temp1.d
8: P0 = temp90.b
9: if (temp211.b == 1) then 10 else 11
10: jump(0x2021c => 12 @ 0x2021c, 15 @ 0x20220)
11: jump(0x20220)
12: temp0.d = 1
13: R0 = temp0.d
14: <return> jump(LR)
15: temp0.d = 2
16: R0 = temp0.d
17: <return> jump(LR)''')

  def test_dualjump_two_cmp_jumps(self):
    func = self.get_function('test_dualjump_two_cmp_jumps')
    self.assertEqual(
        self.list_asm(func), '''
{ P0 = cmp.eq(R3,#0x2);if (P0.new) jump:t 0x20234
P1 = cmp.eq(R3,#0x2);if (P1.new) jump:t 0x20238
R1 = add(R1,R1) }
{ R0 = #0x1; jumpr LR }
{ R0 = #0x0; jumpr LR }
{ R0 = #0x2; jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp212.b = 0
1: temp213.b = 0
2: temp91.b = P1
3: temp91.b = R3 == 2
4: temp90.b = P0
5: temp90.b = R3 == 2
6: if (temp90.b) then 7 else 9
7: temp212.b = 1
8: goto 9
9: if (temp91.b) then 10 else 12
10: temp213.b = 1
11: goto 12
12: temp1.d = R1 + R1
13: R1 = temp1.d
14: P0 = temp90.b
15: P1 = temp91.b
16: if (temp212.b == 1) then 17 else 18
17: jump(0x20234 => 19 @ 0x20234, 22 @ 0x20238)
18: if (temp213.b == 1) then 25 else 26
19: temp0.d = 1
20: R0 = temp0.d
21: <return> jump(LR)
22: temp0.d = 2
23: R0 = temp0.d
24: <return> jump(LR)
25: jump(0x20238)
26: goto 27 @ 0x20230
27: temp0.d = 0
28: R0 = temp0.d
29: <return> jump(LR)''')

  def test_dualjump_newval_cmp_jump(self):
    func = self.get_function('test_dualjump_newval_cmp_jump')
    self.assertEqual(
        self.list_asm(func), '''
{ R1 = add(R1,R1)
if (cmp.eq(R1.new,R2)) jump:t 0x20248 }
{ R0 = #0x1; jumpr LR }
{ R0 = #0x0; jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp211.b = 0
1: temp1.d = R1 + R1
2: if (temp1.d == R2) then 3 else 5
3: temp211.b = 1
4: goto 5
5: R1 = temp1.d
6: if (temp211.b == 1) then 7 else 8
7: jump(0x20248 => 9 @ 0x20248)
8: goto 12 @ 0x20244
9: temp0.d = 1
10: R0 = temp0.d
11: <return> jump(LR)
12: temp0.d = 0
13: R0 = temp0.d
14: <return> jump(LR)''')

  def test_dualjump_indirect_jump(self):
    func = self.get_function('test_dualjump_indirect_jump')
    self.assertEqual(self.list_asm(func), '''
{ R1 = add(R1,R1)
jumpr R0 }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp1.d = R1 + R1
1: temp201.d = R0
2: R1 = temp1.d
3: jump(temp201.d)''')

  def test_dualjump_indirect_jump_reorder(self):
    func = self.get_function('test_dualjump_indirect_jump_reorder')
    self.assertEqual(self.list_asm(func), '''
{ R1 = add(R1,R1)
jumpr R0 }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp1.d = R1 + R1
1: temp201.d = R0
2: R1 = temp1.d
3: jump(temp201.d)''')

  def test_dualjump_cond_indirect_jump(self):
    func = self.get_function('test_dualjump_cond_indirect_jump')
    self.assertEqual(
        self.list_asm(func), '''
{ R1 = add(R1,R1)
if (P0) jumpr:nt R0 }
{ R0 = #0x0; jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp211.b = 0
1: temp1.d = R1 + R1
2: if (P0) then 3 else 6
3: temp211.b = 1
4: temp201.d = R0
5: goto 6
6: R1 = temp1.d
7: if (temp211.b == 1) then 8 else 9 @ 0x20264
8: jump(temp201.d)
9: temp0.d = 0
10: R0 = temp0.d
11: <return> jump(LR)''')

  def test_dualjump_indirect_call(self):
    func = self.get_function('test_dualjump_indirect_call')
    self.assertEqual(self.list_asm(func), '''
{ R1 = add(R1,R1)
callr R0 }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp1.d = R1 + R1
1: temp201.d = R0
2: R1 = temp1.d
3: call(temp201.d)
4: goto 5
5: <return> tailcall(0x20270)''')

  def test_dualjump_cond_indirect_call(self):
    func = self.get_function('test_dualjump_cond_indirect_call')
    self.assertEqual(
        self.list_asm(func), '''
{ R1 = add(R1,R1)
if (P0) callr R0 }
{ R0 = #0x0; jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp211.b = 0
1: temp1.d = R1 + R1
2: if (P0) then 3 else 6
3: temp211.b = 1
4: temp201.d = R0
5: goto 6
6: R1 = temp1.d
7: if (temp211.b == 1) then 8 else 10 @ 0x20278
8: call(temp201.d)
9: goto 10 @ 0x20278
10: temp0.d = 0
11: R0 = temp0.d
12: <return> jump(LR)''')

  def test_dualjump_cond_return(self):
    func = self.get_function('test_dualjump_cond_return')
    self.assertEqual(
        self.list_asm(func), '''
{ R1 = add(R1,R1); if (P0) dealloc_return }
{ R0 = #0x0; jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp211.b = 0
1: temp1.d = R1
2: temp1.d = temp1.d + R1
3: temp90.b = P0
4: temp100.d = FP
5: if (temp90.b) then 6 else 13
6: temp101.q = [temp100.d].q
7: temp101.q = temp101.q
8: LR = sx.q((temp101.q s>> 0x20).d)
9: FP = sx.q(temp101.q.d)
10: SP = temp100.d + 8
11: temp211.b = 1
12: goto 13
13: P0 = temp90.b
14: R1 = temp1.d
15: if (temp211.b == 1) then 16 else 17 @ 0x20280
16: <return> jump(LR)
17: temp0.d = 0
18: R0 = temp0.d
19: <return> jump(LR)''')

  def test_control_regs(self):
    func = self.get_function('test_control_regs')
    self.assertEqual(
        self.list_asm(func), '''
{ P0 = cmp.eq(R0,#0x1) }
{ R1 = P3:0 }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp90.b = R0 == 1
1: P0 = temp90.b
2: temp1.d = P3:0
3: R1 = temp1.d
4: temp200.d = LR
5: <return> jump(LR)''')

  def test_halfwords(self):
    func = self.get_function('test_halfwords')
    self.assertEqual(
        self.list_asm(func), '''
{ R0.H = #0xc
R1.L = #0x22 }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp0.d = R0
1: temp0.d = (temp0.d & not.d(0xffff << 0x10)) | (0xc & 0xffff) << 0x10
2: temp1.d = R1
3: temp1.d = (temp1.d & not.d(0xffff << 0)) | (0x22 & 0xffff) << 0
4: R1 = temp1.d
5: R0 = temp0.d
6: temp200.d = LR
7: <return> jump(LR)''')

  def test_insert(self):
    func = self.get_function('test_insert')
    self.assertEqual(
        self.list_asm(func), '''
{ R1 = insert(R0,#0x1,#0x6) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp1.d = R1
1: temp104.q = 1
2: temp105.q = 6
3: temp1.d = temp1.d & not.q(((sx.q(1) << temp104.q) - 1) << temp105.q)
4: temp1.d = temp1.d | (R0 & ((sx.q(1) << temp104.q) - 1)) << temp105.q
5: R1 = temp1.d
6: temp200.d = LR
7: <return> jump(LR)''')

  def test_extract(self):
    func = self.get_function('test_extract')
    self.assertEqual(
        self.list_asm(func), '''
{ R1 = extractu(R0,#0x2,#0x14) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp104.q = 2
1: temp105.q = 0x14
2: temp1.d = R0 u>> temp105.q & ((1 << temp104.q) - 1)
3: R1 = temp1.d
4: temp200.d = LR
5: <return> jump(LR)''')

  def test_global_pointer_relative_offset(self):
    func = self.get_function('test_global_pointer_relative_offset')
    self.assertEqual(
        self.list_asm(func), '''
{ R1 = memw(GP+#0x10) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp100.d = GP + 0x10
1: temp1.d = [temp100.d].d
2: R1 = temp1.d
3: temp200.d = LR
4: <return> jump(LR)''')

  def test_global_pointer_relative_imm(self):
    func = self.get_function('test_global_pointer_relative_imm')
    self.assertEqual(
        self.list_asm(func), '''
{ R1 = memw(GP+#0x10) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp100.d = GP + 0x10
1: temp1.d = [temp100.d].d
2: R1 = temp1.d
3: temp200.d = LR
4: <return> jump(LR)''')

  def test_global_pointer_relative_immext(self):
    func = self.get_function('test_global_pointer_relative_immext')
    self.assertEqual(
        self.list_asm(func), '''
{ immext(#0x123440)
R1 = memw(0+##0x123450) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp100.d = 0x123450
1: temp1.d = [temp100.d {0x123450}].d
2: R1 = temp1.d
3: temp200.d = LR
4: <return> jump(LR)''')

  def test_swiz(self):
    func = self.get_function('test_swiz')
    self.assertEqual(self.list_asm(func), '''
{ R1 = swiz(R0) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp1.d = (R0 & 0xff) << 0x18 | (R0 & 0xff00) << 8 | (R0 & 0xff0000) u>> 8 | (R0 & 0xff000000) u>> 0x18
1: R1 = temp1.d
2: temp200.d = LR
3: <return> jump(LR)''')

  def test_combine_zero_and_reg(self):
    func = self.get_function('test_combine_zero_and_reg')
    self.assertEqual(
        self.list_asm(func), '''
{ R0 = #0x1 }
{ R3:R2 = combine(#0x0,R0) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp0.d = 1
1: R0 = temp0.d
2: temp2.q = (temp2.q & not.q(0xffffffff << 0)) | (R0 & 0xffffffff) << 0
3: temp2.q = (temp2.q & not.q(0xffffffff << 0x20)) | 0 << 0x20
4: R3:R2 = temp2.q
5: temp200.d = LR
6: <return> jump(LR)''')

  def test_combine_reg_and_zero(self):
    func = self.get_function('test_combine_reg_and_zero')
    self.assertEqual(
        self.list_asm(func), '''
{ R0 = #0x1 }
{ R3:R2 = combine(R0,#0x0) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp0.d = 1
1: R0 = temp0.d
2: temp2.q = (temp2.q & not.q(0xffffffff << 0)) | 0 << 0
3: temp2.q = (temp2.q & not.q(0xffffffff << 0x20)) | (R0 & 0xffffffff) << 0x20
4: R3:R2 = temp2.q
5: temp200.d = LR
6: <return> jump(LR)''')

  def test_combine_imms(self):
    func = self.get_function('test_combine_imms')
    self.assertEqual(
        self.list_asm(func), '''
{ immext(#0x30400)
R3:R2 = combine(#0x1,##0x30400) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp2.q = (temp2.q & not.q(0xffffffff << 0)) | (0x30400 & 0xffffffff) << 0
1: temp2.q = (temp2.q & not.q(0xffffffff << 0x20)) | (1 & 0xffffffff) << 0x20
2: R3:R2 = temp2.q
3: temp200.d = LR
4: <return> jump(LR)''')

  def test_combine_regs(self):
    func = self.get_function('test_combine_regs')
    self.assertEqual(
        self.list_asm(func), '''
{ R0 = #0x1; R1 = #0x2 }
{ R3:R2 = combine(R0,R1) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp0.d = 1
1: temp1.d = 2
2: R1 = temp1.d
3: R0 = temp0.d
4: temp2.q = (temp2.q & not.q(0xffffffff << 0)) | (R1 & 0xffffffff) << 0
5: temp2.q = (temp2.q & not.q(0xffffffff << 0x20)) | (R0 & 0xffffffff) << 0x20
6: R3:R2 = temp2.q
7: temp200.d = LR
8: <return> jump(LR)''')

  def test_rol(self):
    func = self.get_function('test_rol')
    self.assertEqual(
        self.list_asm(func), '''
{ R5 = rol(R1,#0x1c) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp5.d = rol.d(R1, 0x1c)
1: R5 = temp5.d
2: temp200.d = LR
3: <return> jump(LR)''')

  def test_rol_pair(self):
    func = self.get_function('test_rol_pair')
    self.assertEqual(
        self.list_asm(func), '''
{ R5:R4 = rol(R1:R0,#0xc) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp100.q = R1:R0
1: temp4.q = rol.q(temp100.q, 0xc)
2: R5:R4 = temp4.q
3: temp200.d = LR
4: <return> jump(LR)''')

  def test_clobbered_pair(self):
    func = self.get_function('test_clobbered_pair')
    self.assertEqual(
        self.list_asm(func), '''
{ R17:R16 = combine(R0,R1)
memd(SP+#0xfffffff0) = R17:R16; allocframe(#0x18) }
{ jumpr LR }''')
    self.assertEqual(
        self.list_llil(func), '''
0: temp16.q = (temp16.q & not.q(0xffffffff << 0)) | (R1 & 0xffffffff) << 0
1: temp16.q = (temp16.q & not.q(0xffffffff << 0x20)) | (R0 & 0xffffffff) << 0x20
2: temp116.q = R17:R16
3: temp100.d = SP - 0x10
4: [temp100.d {var_10}].q = temp116.q
5: temp100.d = SP - 8
6: [temp100.d {var_8}].q = LR:FP
7: FP = temp100.d
8: SP = temp100.d - 0x18
9: R17:R16 = temp16.q
10: temp200.d = LR
11: <return> jump(LR)''')

if __name__ == '__main__':
  TestPluginIl.TARGET_FILE = os.environ.get('TEST_TARGET_FILE')
  unittest.main()

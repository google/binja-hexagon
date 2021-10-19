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


# E2E test for Hexagon hlil plugin.
# This test uses Binary Ninja headless API, analyses test_binaries/bn_hlil_test_app.s
# and checks the HLIL output.
class TestPluginIl(unittest.TestCase):
  TARGET_FILE = None

  @classmethod
  def setUpClass(cls):
    assert (cls.TARGET_FILE is not None)
    binja.log.log_to_stdout(True)
    cls.bv = binja.BinaryViewType.get_view_of_file(cls.TARGET_FILE)

  def get_function(self, name):
    sym = TestPluginIl.bv.get_symbol_by_raw_name(name)
    return TestPluginIl.bv.get_function_at(sym.address)

  def list_hlil(self, func):
    ret = ['']
    for line in func.hlil.root.lines:
      ret.append('{0}'.format(line))
    return '\n'.join(ret)

  def test_add_int(self):
    func = self.get_function('test_add_int')
    self.assertEqual(self.list_hlil(func), '''
uint32_t temp0 = arg2 + arg1
g_res = temp0
return temp0''')

  def test_cmp_signed_int(self):
    func = self.get_function('test_cmp_signed_int')
    self.assertEqual(
        self.list_hlil(func), '''
bool temp90 = arg2 s> arg1
uint32_t temp1
if (temp90)
    temp1 = 0x8765
if (not.b(temp90))
    temp1 = 0x1234
g_res = temp1''')

  def test_cmp_unsigned_int(self):
    func = self.get_function('test_cmp_unsigned_int')
    self.assertEqual(
        self.list_hlil(func), '''
bool temp90 = arg2 u> arg1
uint32_t temp1
if (temp90)
    temp1 = 0x8765
if (not.b(temp90))
    temp1 = 0x1234
g_res = temp1''')

  def test_mul_int(self):
    func = self.get_function('test_mul_int')
    self.assertEqual(self.list_hlil(func), '''
uint32_t temp0 = arg2 * arg1
g_res = temp0
return temp0''')

  def test_func_call(self):
    func = self.get_function('test_func_call')
    self.assertEqual(
        self.list_hlil(func), '''
uint32_t R0 = arg1(arg2, arg2, arg1)
g_res = R0
int32_t FP
int32_t LR
int32_t LR_1
LR_1:FP = LR:arg3
return R0''')

  def test_struct(self):
    func = self.get_function('test_struct')
    self.assertEqual(self.list_hlil(func), '''
uint32_t temp0 = *(arg1 + 8) + arg2
g_res = temp0
return temp0''')

  def test_fact(self):
    func = self.get_function('test_fact')
    self.assertEqual(
        self.list_hlil(func), '''
int32_t LR
int64_t var_8 = LR:arg2
char temp210 = 0
if (arg1 != 0)
    temp210 = 1
int32_t var_c
if (temp210 != 1)
    var_c = 1
else
    var_c = test_fact(arg1 - 1) * arg1
int32_t FP
int32_t LR_1
LR_1:FP = var_8
return var_c''')

  def test_and_int(self):
    func = self.get_function('test_and_int')
    self.assertEqual(self.list_hlil(func), '''
uint32_t temp0 = arg2 & arg1
g_res = temp0
return temp0''')

  def test_or_int(self):
    func = self.get_function('test_or_int')
    self.assertEqual(self.list_hlil(func), '''
uint32_t temp0 = arg2 | arg1
g_res = temp0
return temp0''')

  def test_xor_int(self):
    func = self.get_function('test_xor_int')
    self.assertEqual(self.list_hlil(func), '''
uint32_t temp0 = arg2 ^ arg1
g_res = temp0
return temp0''')

  def test_not_int(self):
    func = self.get_function('test_not_int')
    self.assertEqual(self.list_hlil(func), '''
g_res = 0xffffffff - arg1
return 0xffffffff - arg1''')

  def test_collatz(self):
    func = self.get_function('test_collatz')
    self.assertEqual(
        self.list_hlil(func), '''
int32_t LR
int64_t var_8 = LR:arg2
int32_t var_c = arg1
while (true)
    char temp210_1 = 0
    if (var_c == 1)
        temp210_1 = 1
    if (temp210_1 == 1)
        break
    char temp210_2 = 0
    if ((var_c & 1) != 0)
        temp210_2 = 1
    if (temp210_2 == 1)
        var_c = 1 + var_c * 3
    else
        var_c = var_c s>> 1
int32_t FP
int32_t LR_1
LR_1:FP = var_8
return var_c''')

  def test_max_signed_int(self):
    func = self.get_function('test_max_signed_int')
    self.assertEqual(
        self.list_hlil(func), '''
int32_t temp0 = (arg1 s>= arg2 ? 1 : 0) * arg1 + (arg1 s< arg2 ? 1 : 0) * arg2
g_res = temp0
return temp0''')

  def test_max_unsigned_int(self):
    func = self.get_function('test_max_unsigned_int')
    self.assertEqual(
        self.list_hlil(func), '''
int32_t temp0 = (arg1 u>= arg2 ? 1 : 0) * arg1 + (arg1 u< arg2 ? 1 : 0) * arg2
g_res = temp0
return temp0''')

  def test_min_signed_int(self):
    func = self.get_function('test_min_signed_int')
    self.assertEqual(
        self.list_hlil(func), '''
int32_t temp0 = (arg1 s<= arg2 ? 1 : 0) * arg1 + (arg1 s> arg2 ? 1 : 0) * arg2
g_res = temp0
return temp0''')

  def test_min_unsigned_int(self):
    func = self.get_function('test_min_unsigned_int')
    self.assertEqual(
        self.list_hlil(func), '''
int32_t temp0 = (arg1 u<= arg2 ? 1 : 0) * arg1 + (arg1 u> arg2 ? 1 : 0) * arg2
g_res = temp0
return temp0''')


if __name__ == '__main__':
  TestPluginIl.TARGET_FILE = os.environ.get('TEST_TARGET_FILE')
  unittest.main()

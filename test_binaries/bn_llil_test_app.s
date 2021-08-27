/*
 * Copyright (C) 2020 Google LLC
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

  .text
  .globl start

test_allocframe:
  { allocframe(r29,#8):raw }
  { r0=#256 }
  { dealloc_return }

test_pair_operations:
  { r5:4=add(r3:2,r9:8) }
  { jumpr lr }

test_cmp_to_predicate:
  { p0 = cmp.eq(r0,#1) }
  { jumpr lr  }

test_memory_load:
  { r1=##buffer }
  { r2=memb(r1+#1) }
  { jumpr lr }

test_memory_store:
  { memw(r1)=#1193046 }
  { jumpr lr }

test_store_dotnew:
  { r3=add(r1,r2)
    memw(r5) = r3.new }
  { jumpr lr }

test_mux:
  { r0 = mux(p0,#1,#0) }
  { jumpr lr }

test_tstbit:
  { p0 = tstbit(r0,#0) }
  { jumpr lr }

//
// Test for dual jump instructions (Table 8-12).
//
// Direct jump:
//   first jump in packet: No
//   second jump in packet: Yes
test_dualjump_direct_jump:
  { r1 = add(r1, r1)
    jump 1f }
  { nop }
1:
  { r0 = #1
    jumpr r31 }

// Conditional jump:
//   first jump in packet: Yes
//   second jump in packet: Yes
test_dualjump_cond_jump:
  { r1 = add(r1, r1)
    if (p0) jump:t 1f }
  { r0 = #0
    jumpr r31 }
1:
  { r0 = #1
    jumpr r31 }

test_dualjump_cond_jump_with_direct_jump:
  { r1 = add(r1, r1)
    if (p0) jump:t 1f
    jump 2f }
1:
  { r0 = #1
    jumpr r31 }
2:
  { r0 = #2
    jumpr r31 }

test_dualjump_two_cond_jumps:
  { r1 = add(r1, r1)
    if (p0) jump:t 1f
    if (!p1) jump:t 2f }
  { r0 = #0
    jumpr r31 }
1:
  { r0 = #1
    jumpr r31 }
2:
  { r1 = #2
    jumpr r31 }

// Direct calls:
//   first jump in packet: No
//   second jump in packet: Yes
test_dualjump_direct_call:
  { r0 = add(r1,r0)
    call 1f }

  { nop
    jumpr r31 }
1:
  { r0 = #1
    jumpr r31 }

test_dualjump_direct_call_reorder:
  { call 1f
    memw(r2+#0) = r3 }

  { nop
    jumpr r31 }
1:
  { r0 = #1
    jumpr r31 }

test_dualjump_cond_call:
  { r1 = add(r1, r1)
    if (p0) call 1f }
  { r0 = #0
    jumpr r31 }
1:
  { r0 = #1
    jumpr r31 }

test_dualjump_cond_call_with_direct_jump:
  { r1 = add(r1, r1)
    if (p0) call 1f
    jump 2f }
1:
  { r0 = #1
    jumpr r31 }
2:
  { r0 = #2
    jumpr r31 }

// Compare jump:
//   first jump in packet: Yes
//   second jump in packet: Yes
test_dualjump_cmp_jump:
  { r1 = add(r1, r1)
    p0 = cmp.eq(r3, #2); if (p0.new) jump:t 1f }
  { r0 = #0
    jumpr r31 }
1:
  { r0 = #1
    jumpr r31 }

test_dualjump_cmp_jump_with_direct_jump:
  { r1 = add(r1, r1)
    p0 = cmp.eq(r3, #2); if (p0.new) jump:t 1f
    jump 2f }
1:
  { r0 = #1
    jumpr r31 }
2:
  { r0 = #2
    jumpr r31 }

test_dualjump_two_cmp_jumps:
  { r1 = add(r1, r1)
    p0 = cmp.eq(r3, #2); if (p0.new) jump:t 1f
    p1 = cmp.eq(r3, #2); if (p1.new) jump:t 2f }
  { r0 = #0
    jumpr r31 }
1:
  { r0 = #1
    jumpr r31 }
2:
  { r0 = #2
    jumpr r31 }

// New-value compare jump:
//   first jump in packet: No
//   second jump in packet: No
test_dualjump_newval_cmp_jump:
  { r1 = add(r1, r1)
    if (cmp.eq(r1.new, r2)) jump:t 1f }
  { r0 = #0
    jumpr r31 }
1:
  { r0 = #1
    jumpr r31 }

// Indirect jumps:
//   first jump in packet: No
//   second jump in packet: No
test_dualjump_indirect_jump:
  { r1 = add(r1, r1)
    jumpr r0 }

test_dualjump_indirect_jump_reorder:
  { jumpr r0
    r1 = add(r1, r1) }

test_dualjump_cond_indirect_jump:
  { r1 = add(r1, r1)
    if (p0) jumpr r0 }
  { r0 = #0
    jumpr r31 }

// Indirect calls:
//   first jump in packet: No
//   second jump in packet: No
test_dualjump_indirect_call:
  { r1 = add(r1, r1)
    callr r0 }

test_dualjump_cond_indirect_call:
  { r1 = add(r1, r1)
    if (p0) callr r0 }
  { r0 = #0
    jumpr r31 }


// dealloc_return:
//   first jump in packet: No
//   second jump in packet: No
test_dualjump_cond_return:
  { r1 = add(r1, r1)
    if (p0) dealloc_return }
  { r0 = #0
    jumpr r31 }

test_hwloop:
  { loop0(1f, #10)
    r1 = #0 }

1:
  { r1 = add(r1, #1)
    nop
  }:endloop0

  { jumpr lr }

test_control_regs:
  { p0 = cmp.eq(r0, #1) }
  { r1 = c4 }
  { jumpr lr }

test_halfwords:
  { r0.h = #12
    r1.l = #34 }
  { jumpr lr }

test_insert:
  { r1 = insert(r0, #1, #6) }
  { jumpr lr }

test_extract:
  { r1 = extractu(r0, #2, #20) }
  { jumpr lr }

test_global_pointer_relative_offset:
  { r1 = memw(gp + #16) }
  { jumpr lr }

test_global_pointer_relative_imm:
  { r1 = memw(#16) }
  { jumpr lr }

test_global_pointer_relative_immext:
  { r1 = memw(##0x123450) }
  { jumpr lr }

test_swiz:
  { r1 = swiz(r0) }
  { jumpr lr }

test_combine_zero_and_reg:
  { r0 = #1 }
  { r3:2 = combine(#0, r0) }
  { jumpr lr }

test_combine_reg_and_zero:
  { r0 = #1 }
  { r3:2 = combine(r0, #0) }
  { jumpr lr }

test_combine_imms:
  { r3:2 = combine(#1, ##buffer) }
  { jumpr lr }

test_combine_regs:
  { r0 = #1
    r1 = #2 }
  { r3:2 = combine(r0, r1) }
  { jumpr lr }

test_rol:
  { r5 = rol(r1,#0x1c) }
  { jumpr lr }

test_rol_pair:
  { r5:4 = rol(r1:0,#0xc) }
  { jumpr lr }

// https://github.com/google/binja-hexagon/issues/5 regression test.
test_clobbered_pair:
  { R17:16 = combine(R0,R1)
    memd(SP+#0xfffffff0) = R17:16; allocframe(#0x18) }
  { jumpr lr }

start:
  { call test_allocframe }
  { call test_pair_operations }
  { call test_cmp_to_predicate }
  { call test_memory_load }
  { call test_memory_store }
  { call test_store_dotnew }
  { call test_mux }
  { call test_tstbit }
  { call test_dualjump_direct_jump }
  { call test_dualjump_cond_jump }
  { call test_dualjump_cond_jump_with_direct_jump }
  { call test_dualjump_two_cond_jumps }
  { call test_dualjump_direct_call }
  { call test_dualjump_direct_call_reorder }
  { call test_dualjump_cond_call }
  { call test_dualjump_cond_call_with_direct_jump }
  { call test_dualjump_cmp_jump }
  { call test_dualjump_cmp_jump_with_direct_jump }
  { call test_dualjump_two_cmp_jumps }
  { call test_dualjump_newval_cmp_jump }
  { call test_dualjump_indirect_jump }
  { call test_dualjump_indirect_jump_reorder }
  { call test_dualjump_cond_indirect_jump }
  { call test_dualjump_indirect_call }
  { call test_dualjump_cond_indirect_call }
  { call test_dualjump_cond_return }
  { call test_hwloop }
  { call test_control_regs }
  { call test_halfwords }
  { call test_insert }
  { call test_extract }
  { call test_global_pointer_relative_offset }
  { call test_global_pointer_relative_imm }
  { call test_global_pointer_relative_immext }
  { call test_swiz }
  { call test_combine_zero_and_reg }
  { call test_combine_reg_and_zero }
  { call test_combine_imms }
  { call test_combine_regs }
  { call test_rol }
  { call test_rol_pair }
  { call test_clobbered_pair }

  { jumpr lr }


  .data
  .globl buffer
.p2align 8
buffer:
  .string "Hello world!\n"
  .size buffer, 14

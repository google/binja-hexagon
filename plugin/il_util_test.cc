// Copyright (C) 2020 Google LLC
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License along
// with this program; if not, write to the Free Software Foundation, Inc.,
// 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

#include "plugin/il_util.h"

#include "absl/status/status.h"
#include "plugin/status_matchers.h"
#include "gtest/gtest.h"

namespace {

using absl::IsOk;
using absl::MakeSpan;
using testing::Eq;
using testing::Not;

TEST(IlUtilTest, RemovesImmExtender) {
  // 13c:       c0 76 ea 0d 0dea76c0 {  immext(#3735924736)
  // 140:       11 28 b3 28 28b32811    r3 = ##3735924747;      r1 = #1 }
  std::vector<uint32_t> words = {0x0dea76c0, 0x28b32811};
  ASSERT_OK_AND_ASSIGN(Packet src, Decoder::Get().DecodePacket(words));
  EXPECT_EQ(src.num_insns, 3);
  EXPECT_EQ(src.insn[0].opcode, A4_ext);
  Packet pkt = PreparePacketForLifting(src);
  EXPECT_EQ(pkt.num_insns, 2);
  EXPECT_NE(pkt.insn[0].opcode, A4_ext);
  EXPECT_NE(pkt.insn[1].opcode, A4_ext);
}

TEST(IlUtilTest, MovesStoresToEnd) {
  // TODO: Update this test.
}

TEST(IlUtilTest, MovesComparesToBeginning) {
  // 5c:       04 40 00 00 00004004 {  immext(#256)
  // 60:       70 58 00 5c 5c005870    if (p0.new) jump:t 0x194 <pass>
  // 64:       a4 40 00 58 580040a4    jump 0x1a4 <fail>
  // 68:       a0 fb 23 75 7523fba0    p0 = cmp.eq(r3,#-35) }
  std::vector<uint32_t> words = {0x00004004, 0x5c005870, 0x580040a4,
                                 0x7523fba0};
  ASSERT_OK_AND_ASSIGN(Packet src, Decoder::Get().DecodePacket(words));
  EXPECT_EQ(src.num_insns, 4);
  EXPECT_EQ(src.insn[0].opcode, A4_ext);
  EXPECT_EQ(src.insn[1].opcode, J2_jumptnewpt);
  EXPECT_EQ(src.insn[2].opcode, J2_jump);
  EXPECT_EQ(src.insn[3].opcode, C2_cmpeqi);
  Packet pkt = PreparePacketForLifting(src);
  EXPECT_EQ(pkt.num_insns, 3);
  EXPECT_EQ(pkt.insn[0].opcode, C2_cmpeqi);
  EXPECT_EQ(pkt.insn[1].opcode, J2_jumptnewpt);
  EXPECT_EQ(pkt.insn[2].opcode, J2_jump);
}

TEST(IlUtilTest, SplitsCmpJump) {
  // 15c:       ff 7f ff 0f 0fff7fff {  immext(#4294967232)
  // 160:       18 6a 02 10 10026a18    p0 = cmp.eq(r2,#10); if (p0.new) jump:t
  // 164:       ee ff ff 59 59ffffee    jump 0x138 <fail> }
  std::vector<uint32_t> words = {0x0fff7fff, 0x10026a18, 0x59ffffee};
  ASSERT_OK_AND_ASSIGN(Packet src, Decoder::Get().DecodePacket(words));
  EXPECT_EQ(src.num_insns, 3);
  EXPECT_EQ(src.insn[0].opcode, A4_ext);
  EXPECT_EQ(src.insn[1].opcode, J4_cmpeqi_tp0_jump_t);
  EXPECT_EQ(src.insn[2].opcode, J2_jump);
  Packet pkt = PreparePacketForLifting(src);
  EXPECT_EQ(pkt.num_insns, 3);
  EXPECT_EQ(pkt.insn[0].opcode, J4_cmpeqi_tp0_jump_t);
  EXPECT_TRUE(pkt.insn[0].part1);
  EXPECT_EQ(pkt.insn[1].opcode, J4_cmpeqi_tp0_jump_t);
  EXPECT_FALSE(pkt.insn[1].part1);
  EXPECT_EQ(pkt.insn[2].opcode, J2_jump);
}

TEST(IlUtilTest, KeepsDualJumpOrder) {
  // 000000b4  0650005c           { if (P0) jump:t data_c0    {data_c4}
  // 000000b8  08400058             jump data_c4
  // 000000bc  01c101f3             R1 = add(R1,R1) }
  std::vector<uint32_t> words = {0x5c005006, 0x58004008, 0xf301c101};
  ASSERT_OK_AND_ASSIGN(Packet src, Decoder::Get().DecodePacket(words));
  EXPECT_EQ(src.num_insns, 3);
  EXPECT_EQ(src.insn[0].opcode, J2_jumptpt);
  EXPECT_EQ(src.insn[1].opcode, J2_jump);
  EXPECT_EQ(src.insn[2].opcode, A2_add);
  Packet pkt = PreparePacketForLifting(src);
  EXPECT_EQ(pkt.num_insns, 3);
  EXPECT_EQ(pkt.insn[0].opcode, J2_jumptpt);
  EXPECT_EQ(pkt.insn[1].opcode, J2_jump);
  EXPECT_EQ(pkt.insn[2].opcode, A2_add);
}

} // namespace

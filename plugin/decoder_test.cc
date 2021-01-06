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

#include "plugin/decoder.h"

#include "plugin/status_matchers.h"
#include "gtest/gtest.h"

namespace {

TEST(DecoderTest, DecodesSingleAluInstruction) {
  // 00 e0 00 78 7800e000 {  r0 = #256 }
  // alu.idef:
  // Q6INSN(A2_tfrsi,"Rd32=#s16",ATTRIBS(),
  //"transfer signed immediate to register",{ fIMMEXT(siV); RdV=siV;})
  std::vector<uint32_t> words = {0x7800e000};
  ASSERT_OK_AND_ASSIGN(Packet pkt, Decoder::Get().DecodePacket(words));
  EXPECT_EQ(pkt.num_insns, 1);
  EXPECT_EQ(pkt.encod_pkt_size_in_bytes, 4);
  EXPECT_EQ(pkt.insn[0].opcode, A2_tfrsi);
  EXPECT_EQ(pkt.insn[0].iclass, ICLASS_ALU32_2op);
  EXPECT_EQ(pkt.insn[0].slot, 3);
  EXPECT_EQ(pkt.insn[0].regno[0], 0);
  EXPECT_EQ(pkt.insn[0].immed[0], 256);
}

TEST(DecoderTest, DecodesTwoAluSubInstructions) {
  // 02 28 01 28 28012802 {  r1 = #0;        r2 = #0 }
  // subinsns.idef:
  // Q6INSN(SA1_seti,     "Rd16=#u6",              ATTRIBS(A_SUBINSN),"Set
  // immed",  { fIMMEXT(uiV); RdV=uiV;})
  std::vector<uint32_t> words = {0x28012802};
  ASSERT_OK_AND_ASSIGN(Packet pkt, Decoder::Get().DecodePacket(words));
  EXPECT_EQ(pkt.num_insns, 2);
  EXPECT_EQ(pkt.encod_pkt_size_in_bytes, 4);
  EXPECT_EQ(pkt.insn[0].opcode, SA1_seti);
  EXPECT_EQ(pkt.insn[0].iclass, ICLASS_EXTENDER + 16);
  EXPECT_EQ(pkt.insn[0].slot, 1);
  EXPECT_EQ(pkt.insn[0].regno[0], 1);
  EXPECT_EQ(pkt.insn[0].immed[0], 0);
  EXPECT_EQ(pkt.insn[1].opcode, SA1_seti);
  EXPECT_EQ(pkt.insn[1].iclass, ICLASS_EXTENDER + 16);
  EXPECT_EQ(pkt.insn[1].slot, 0);
  EXPECT_EQ(pkt.insn[1].regno[0], 2);
  EXPECT_EQ(pkt.insn[1].immed[0], 0);
}

TEST(DecoderTest, DecodesTwoImmExt) {
  // 13c:       c0 76 ea 0d 0dea76c0 {  immext(#3735924736)
  // 140:       11 28 b3 28 28b32811    r3 = ##3735924747;      r1 = #1 }
  std::vector<uint32_t> words = {0x0dea76c0, 0x28b32811};
  ASSERT_OK_AND_ASSIGN(Packet pkt, Decoder::Get().DecodePacket(words));
  EXPECT_EQ(pkt.num_insns, 3);
  EXPECT_EQ(pkt.encod_pkt_size_in_bytes, 8);
  EXPECT_EQ(pkt.insn[0].opcode, A4_ext);
  EXPECT_TRUE(pkt.insn[1].extension_valid);
  EXPECT_EQ(pkt.insn[1].which_extended, 0);
  EXPECT_EQ(pkt.insn[1].immed[0], static_cast<int32_t>(3735924747));
  EXPECT_EQ(pkt.insn[1].regno[0], 3);
  EXPECT_EQ(pkt.insn[2].immed[0], 1);
  EXPECT_EQ(pkt.insn[2].regno[0], 1);
}

TEST(DecoderTest, DecodesCall) {
  // 148:       5c ff ff 5b 5bffff5c {  call 0x0 <init> }
  std::vector<uint32_t> words = {0x5bffff5c};
  ASSERT_OK_AND_ASSIGN(Packet pkt, Decoder::Get().DecodePacket(words));
  EXPECT_EQ(pkt.num_insns, 1);
  EXPECT_EQ(pkt.insn[0].opcode, J2_call);
  EXPECT_EQ(pkt.insn[0].iclass, ICLASS_J);
  EXPECT_EQ(pkt.insn[0].immed[0], static_cast<int32_t>(0 - 0x148));
}

TEST(DecoderTest, DecodesDeallocReturn) {
  // c:       1e c0 1e 96 961ec01e {  dealloc_return }
  std::vector<uint32_t> words = {0x961ec01e};
  ASSERT_OK_AND_ASSIGN(Packet pkt, Decoder::Get().DecodePacket(words));
  EXPECT_EQ(pkt.num_insns, 1);
  EXPECT_EQ(pkt.insn[0].opcode, L4_return);
  EXPECT_EQ(pkt.insn[0].iclass, ICLASS_LD);
}

TEST(DecoderTest, DecodesMultipleBranches) {
  // 154:       ff 7f ff 0f 0fff7fff {  immext(#4294967232)
  // 158:       28 60 03 10 10036028    p0 = cmp.eq(r3,#0); if (p0.new) jump:t
  // 0x128 <pass>
  // 15c:       f2 ff ff 59 59fffff2    jump 0x138 <fail> }
  std::vector<uint32_t> words = {0x0fff7fff, 0x10036028, 0x59fffff2};
  ASSERT_OK_AND_ASSIGN(Packet pkt, Decoder::Get().DecodePacket(words));
  EXPECT_EQ(pkt.num_insns, 3);
  EXPECT_EQ(pkt.insn[0].opcode, A4_ext);
  EXPECT_EQ(pkt.insn[1].opcode, J4_cmpeqi_tp0_jump_t);
  EXPECT_EQ(pkt.insn[1].iclass, ICLASS_CJ);
  EXPECT_TRUE(pkt.insn[1].extension_valid);
  EXPECT_EQ(pkt.insn[1].which_extended, 0);
  EXPECT_EQ(pkt.insn[1].immed[0], static_cast<int32_t>(0x128 - 0x154));
  EXPECT_EQ(pkt.insn[2].iclass, ICLASS_J);
  EXPECT_EQ(pkt.insn[2].immed[0], static_cast<int32_t>(0x138 - 0x154));
}

TEST(DecoderTest, FailsOnShortPacket) {
  // 154:       ff 7f ff 0f 0fff7fff {  immext(#4294967232)
  // 158:       28 60 03 10 10036028    p0 = cmp.eq(r3,#0); if (p0.new) jump:t
  // 0x128 <pass>
  // 15c:       f2 ff ff 59 59fffff2    jump 0x138 <fail> }
  std::vector<uint32_t> words = {0x0fff7fff, 0x10036028};
  EXPECT_THAT(Decoder::Get().DecodePacket(words),
              absl::StatusIs(absl::StatusCode::kFailedPrecondition));
}

TEST(DecoderTest, DecodesDotnewStoreRegression) {
  //   872c:       02 40 00 78 78004002 {  r2 = #0
  //   8730:       a7 43 00 00 000043a7    immext(#59840)
  //   8734:       30 c2 a0 48 48a0c230    memb(##59888) = r2.new }
  std::vector<uint32_t> words = {0x78004002, 0x000043a7, 0x48a0c230};
  ASSERT_OK_AND_ASSIGN(Packet pkt, Decoder::Get().DecodePacket(words));
  EXPECT_EQ(pkt.num_insns, 3);
  EXPECT_EQ(pkt.insn[0].opcode, A2_tfrsi);
  EXPECT_EQ(pkt.insn[1].opcode, A4_ext);
  EXPECT_EQ(pkt.insn[2].immed[0], static_cast<int32_t>(59888));
  EXPECT_EQ(pkt.insn[2].opcode, S2_storerbnewgp);
}

TEST(DecoderTest, FailsSafeOnInvalidCode) {
  std::vector<uint32_t> words = {0x00006000, 0x0000007f, 0x00000004};
  EXPECT_THAT(Decoder::Get().DecodePacket(words),
              absl::StatusIs(absl::StatusCode::kInternal));
}

TEST(DecoderTest, DecodesAddsEndLoopInsn) {
  //      1c8:       22 80 02 b0 b0028022 {  r2 = add(r2,#1)
  //      1cc:       00 c0 00 7f 7f00c000    nop }  :endloop0
  std::vector<uint32_t> words = {0xb0028022, 0x7f00c000};
  ASSERT_OK_AND_ASSIGN(Packet pkt, Decoder::Get().DecodePacket(words));
  EXPECT_EQ(pkt.num_insns, 3);
  EXPECT_EQ(pkt.insn[0].opcode, A2_addi);
  EXPECT_EQ(pkt.insn[1].opcode, A2_nop);
  EXPECT_EQ(pkt.insn[2].opcode, J2_endloop0);
}

TEST(DecoderTest, FailsSafeOnInvalidAsciiStringRegression1) {
  // ASCII string: "_CLK failed".
  std::vector<uint32_t> words = {0x4b4c435f, 0x69616620, 0x2164656c, 0};
  EXPECT_THAT(Decoder::Get().DecodePacket(words),
              absl::StatusIs(absl::StatusCode::kInternal));
}

TEST(DecoderTest, FailsSafeOnInvalidAsciiStringRegression2) {
  // ASCII string: "ub-ID:%d".
  // Second word has end-of-packet marker and duplex instructions.
  // However, the second sub-instruction fails to decode.
  std::vector<uint32_t> words = {0x492D6275, 0x64253A44};
  EXPECT_THAT(Decoder::Get().DecodePacket(words),
              absl::StatusIs(absl::StatusCode::kInternal));
}

} // namespace

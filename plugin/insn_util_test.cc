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

#include "plugin/insn_util.h"

#include "absl/status/status.h"
#include "absl/strings/str_cat.h"
#include "plugin/status_matchers.h"
#include "gtest/gtest.h"

namespace {

using namespace BinaryNinja;
using absl::IsOk;
using absl::MakeSpan;
using testing::Eq;
using testing::Not;

//_start:
//       0:       14 c0 00 5a 5a00c014 {  call 0x28 <init> }
//       4:       80 c0 00 78 7800c080 {  r0 = #4 }
//       8:       00 40 00 00 00004000 {  immext(#0)
//       c:       01 c3 00 78 7800c301    r1 = ##24 }
//      10:       00 c0 00 54 5400c000 {  trap0(#0) }
//      14:       9e c0 00 58 5800c09e {  jump 0x150 <pass> }
constexpr uint64_t kProgramPart1Address = 0x0;
constexpr uint8_t kProgramPart1[] = {
    0x14, 0xc0, 0x00, 0x5a, 0x80, 0xc0, 0x00, 0x78, 0x00, 0x40, 0x00, 0x00,
    0x01, 0xc3, 0x00, 0x78, 0x00, 0xc0, 0x00, 0x54, 0x9e, 0xc0, 0x00, 0x58,
};
// init:
//       28:       00 c0 9d a0 a09dc000 {  allocframe(#0) }
//       2c:       00 e0 00 78 7800e000 {  r0 = #256 }
//       30:       10 c0 00 67 6700c010 {  evb = r0 }
//       34:       1e c0 1e 96 961ec01e {  dealloc_return }
//
constexpr uint64_t kProgramPart2Address = 0x28;
constexpr uint8_t kProgramPart2[] = {
    0x00, 0xc0, 0x9d, 0xa0, 0x00, 0xe0, 0x00, 0x78,
    0x10, 0xc0, 0x00, 0x67, 0x1e, 0xc0, 0x1e, 0x96,
};

// test3:
//      40:       40 40 00 00 00004040 {  immext(#4096)
//      44:       00 c0 00 78 7800c000    r0 = ##4096 }
//      48:       0c c0 20 62 6220c00c {  cs0 = r0 }
//      4c:       23 c0 00 99 9900c023 {  r3 = memb(r0++#1:circ(m0)) }
//      50:       23 c0 00 99 9900c023 {  r3 = memb(r0++#1:circ(m0)) }
//      54:       23 c0 00 99 9900c023 {  r3 = memb(r0++#1:circ(m0)) }
//      58:       23 c0 00 99 9900c023 {  r3 = memb(r0++#1:circ(m0)) }
//      5c:       04 40 00 00 00004004 {  immext(#256)
//      60:       70 58 00 5c 5c005870    if (p0.new) jump:t 0x194 <pass>
//      64:       a4 40 00 58 580040a4    jump 0x1a4 <fail>
//      68:       a0 fb 23 75 7523fba0    p0 = cmp.eq(r3,#-35) }
constexpr uint64_t kProgramPart3Address = 0x40;
constexpr uint8_t kProgramPart3[] = {
    0x40, 0x40, 0x00, 0x00, 0x00, 0xc0, 0x00, 0x78, 0x0c, 0xc0, 0x20,
    0x62, 0x23, 0xc0, 0x00, 0x99, 0x23, 0xc0, 0x00, 0x99, 0x23, 0xc0,
    0x00, 0x99, 0x23, 0xc0, 0x00, 0x99, 0x04, 0x40, 0x00, 0x00, 0x70,
    0x58, 0x00, 0x5c, 0xa4, 0x40, 0x00, 0x58, 0xa0, 0xfb, 0x23, 0x75,
};

// 00000134  014101f3           { R1 = add(R1,R1)
// 00000138  00c04053             if (P0) jumpr:nt R0 }
constexpr uint64_t kProgramPart4Address = 0x134;
constexpr uint8_t kProgramPart4[] = {0x01, 0x41, 0x01, 0xf3,
                                     0x00, 0xc0, 0x40, 0x53};

//      148:       5c ff ff 5b 5bffff5c {  call 0x0 <init> }
//      14c:       02 28 01 28 28012802 {  r1 = #0;        r2 = #0 }
//      150:       03 c3 02 f3 f302c303 {  r3 = add(r2,r3) }
constexpr uint64_t kProgramPart5Address = 0x148;
constexpr uint8_t kProgramPart5[] = {
    0x5c, 0xff, 0xff, 0x5b, 0x02, 0x28, 0x01, 0x28, 0x03, 0xc3, 0x02, 0xf3,
};

//      158:       00 40 44 85 85444000 {  p0 = r4
//      15c:       06 c8 00 5c 5c00c806    if (p0.new) jump:nt 0x164 <skip>
constexpr uint64_t kProgramPart6Address = 0x158;
constexpr uint8_t kProgramPart6[] = {
    0x00, 0x40, 0x44, 0x85, 0x06, 0xc8, 0x00, 0x5c,
};

//     1c0:       52 40 00 69 69004052 {  loop0(0x1c8,#10)
//     1c4:       02 c0 00 78 7800c002    r2 = #0 }
//     1c8:       22 80 02 b0 b0028022 {  r2 = add(r2,#1)
//     1cc:       00 c0 00 7f 7f00c000    nop }  :endloop0
constexpr uint64_t kProgramPart7Address = 0x1c0;
constexpr uint8_t kProgramPart7[] = {
    0x52, 0x40, 0x00, 0x69, 0x02, 0xc0, 0x00, 0x78,
    0x22, 0x80, 0x02, 0xb0, 0x00, 0xc0, 0x00, 0x7f,
};

//    60ec:       38 42 00 00 00004238 {  immext(#36352)
//    60f0:       10 4e 49 6a 6a494e10    r16 = add(pc,##36380)
//    60f4:       ff 43 00 00 000043ff    immext(#65472)
//    60f8:       82 e0 9f 7c 7c9fe082    r3:2 = combine(#4,##65535) }
constexpr uint64_t kProgramPart8Address = 0x60ec;
constexpr uint8_t kProgramPart8[] = {
    0x38, 0x42, 0x00, 0x00, 0x10, 0x4e, 0x49, 0x6a,
    0xff, 0x43, 0x00, 0x00, 0x82, 0xe0, 0x9f, 0x7c,
};

// 6104:       40 3f 00 48 48003f40 {  r0 = #0;        dealloc_return }
constexpr uint64_t kProgramPart9Address = 0x6104;
constexpr uint8_t kProgramPart9[] = {0x40, 0x3f, 0x00, 0x48};

// 7160: 10 40 60 70 70604010 {  r16 = r0
// 7164: 20 1c f4 eb ebf41c20    memd(r29+#-16) = r17:16;  allocframe(#16) }
constexpr uint64_t kProgramPart10Address = 0x7160;
constexpr uint8_t kProgramPart10[] = {
    0x10, 0x40, 0x60, 0x70, 0x20, 0x1c, 0xf4, 0xeb,
};

// LOAD:B0000024 0B 40 20 62    { gp = r0
// LOAD:B0000028 00 C0 A1 50      callr r1 }
// LOAD:B000002C FF 7F FF 04    { immext (#0x4FFFFFC0)
// LOAD:B0000030 00 CA 49 6A      r0 = add (pc, ##0x4FFFFFD4) }
constexpr uint64_t kProgramPart11Address = 0xb0000024;
constexpr uint8_t kProgramPart11[] = {
    0x0B, 0x40, 0x20, 0x62, 0x00, 0xC0, 0xA1, 0x50,
    0xFF, 0x7F, 0xFF, 0x04, 0x00, 0xCA, 0x49, 0x6A,
};

constexpr uint64_t kCallAddress = 0x0;
constexpr uint64_t kCallDest = 0x28;
constexpr uint64_t kTrapAddress = 0x10;
constexpr uint64_t kUncondJumpAddress = 0x14;
constexpr uint64_t kUncondJumpDest = 0x150;
constexpr uint64_t kReturnAddress = 0x34;
constexpr uint64_t kCondJumpAddress = 0x60;
constexpr uint64_t kCondJumpLastInstAddress = 0x68;
constexpr uint64_t kCondJumpDest = 0x194;
constexpr uint64_t kCondJumpElseDest = 0x1a4;
constexpr uint64_t kCondJumpNoElseLastInstAddress = 0x15c;
constexpr uint64_t kCondJumpNoElseDest = 0x164;
constexpr uint64_t kCondJumpNoElseElseDest = 0x160;
constexpr uint64_t kSubReturnAddress = 0x6104;
constexpr uint64_t kIndirectCallAddress = 0xB0000028;
constexpr uint64_t kCondIndirectJump = 0x138;

class InsnUtilTest : public ::testing::Test {
protected:
  void SetUp() override {
    ASSERT_THAT(db_.AddBytes(kProgramPart1, kProgramPart1Address), IsOk());
    ASSERT_THAT(db_.AddBytes(kProgramPart2, kProgramPart2Address), IsOk());
    ASSERT_THAT(db_.AddBytes(kProgramPart3, kProgramPart3Address), IsOk());
    ASSERT_THAT(db_.AddBytes(kProgramPart4, kProgramPart4Address), IsOk());
    ASSERT_THAT(db_.AddBytes(kProgramPart5, kProgramPart5Address), IsOk());
    ASSERT_THAT(db_.AddBytes(kProgramPart6, kProgramPart6Address), IsOk());
    ASSERT_THAT(db_.AddBytes(kProgramPart7, kProgramPart7Address), IsOk());
    ASSERT_THAT(db_.AddBytes(kProgramPart8, kProgramPart8Address), IsOk());
    ASSERT_THAT(db_.AddBytes(kProgramPart9, kProgramPart9Address), IsOk());
    ASSERT_THAT(db_.AddBytes(kProgramPart10, kProgramPart10Address), IsOk());
    ASSERT_THAT(db_.AddBytes(kProgramPart11, kProgramPart11Address), IsOk());
  }

  std::string Disasm(const PacketDb::InsnInfo &input) {
    size_t len = 0;
    std::vector<InstructionTextToken> result;
    EXPECT_THAT(FillBnInstructionTextTokens(input, len, result), IsOk());
    EXPECT_EQ(len, 4);
    std::string disasm;
    for (const auto &tok : result) {
      absl::StrAppend(&disasm, tok.text);
    }
    return disasm;
  }

  PacketDb db_;
};

TEST_F(InsnUtilTest, FillsCallInfo) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match, db_.Lookup(kCallAddress));
  InstructionInfo result;
  EXPECT_THAT(FillBnInstructionInfo(match, result), IsOk());
  EXPECT_EQ(result.length, 4);
  EXPECT_EQ(result.branchCount, 1);
  EXPECT_EQ(result.branchType[0], CallDestination);
  EXPECT_EQ(result.branchTarget[0], kCallDest);
}

TEST_F(InsnUtilTest, SkipsNonLastInstruction) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match, db_.Lookup(kCondJumpAddress));
  InstructionInfo result;
  EXPECT_THAT(FillBnInstructionInfo(match, result), IsOk());
  EXPECT_EQ(result.length, 4);
  EXPECT_EQ(result.branchCount, 0);
}

TEST_F(InsnUtilTest, FillsTrapInfo) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match, db_.Lookup(kTrapAddress));
  InstructionInfo result;
  EXPECT_THAT(FillBnInstructionInfo(match, result), IsOk());
  EXPECT_EQ(result.length, 4);
  EXPECT_EQ(result.branchCount, 1);
  EXPECT_EQ(result.branchType[0], SystemCall);
}

TEST_F(InsnUtilTest, FillsUncondJumpInfo) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match,
                       db_.Lookup(kUncondJumpAddress));
  InstructionInfo result;
  EXPECT_THAT(FillBnInstructionInfo(match, result), IsOk());
  EXPECT_EQ(result.length, 4);
  EXPECT_EQ(result.branchCount, 1);
  EXPECT_EQ(result.branchType[0], UnconditionalBranch);
  EXPECT_EQ(result.branchTarget[0], kUncondJumpDest);
}

TEST_F(InsnUtilTest, FillsReturnInfo) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match, db_.Lookup(kReturnAddress));
  InstructionInfo result;
  EXPECT_THAT(FillBnInstructionInfo(match, result), IsOk());
  EXPECT_EQ(result.length, 4);
  EXPECT_EQ(result.branchCount, 1);
  EXPECT_EQ(result.branchType[0], FunctionReturn);
}

TEST_F(InsnUtilTest, FillsSubReturnInfo) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match, db_.Lookup(kSubReturnAddress));
  InstructionInfo result;
  EXPECT_THAT(FillBnInstructionInfo(match, result), IsOk());
  EXPECT_EQ(result.length, 4);
  EXPECT_EQ(result.branchCount, 1);
  EXPECT_EQ(result.branchType[0], FunctionReturn);
}

TEST_F(InsnUtilTest, FillsCondJumpInfo) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match,
                       db_.Lookup(kCondJumpLastInstAddress));
  InstructionInfo result;
  EXPECT_THAT(FillBnInstructionInfo(match, result), IsOk());
  EXPECT_EQ(result.length, 4);
  EXPECT_EQ(result.branchCount, 2);
  EXPECT_EQ(result.branchType[0], TrueBranch);
  EXPECT_EQ(result.branchTarget[0], kCondJumpDest);
  EXPECT_EQ(result.branchType[1], FalseBranch);
  EXPECT_EQ(result.branchTarget[1], kCondJumpElseDest);
}

TEST_F(InsnUtilTest, FillsCondJumpImplicitElseInfo) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match,
                       db_.Lookup(kCondJumpNoElseLastInstAddress));
  InstructionInfo result;
  EXPECT_THAT(FillBnInstructionInfo(match, result), IsOk());
  EXPECT_EQ(result.length, 4);
  EXPECT_EQ(result.branchCount, 2);
  EXPECT_EQ(result.branchType[0], TrueBranch);
  EXPECT_EQ(result.branchTarget[0], kCondJumpNoElseDest);
  EXPECT_EQ(result.branchType[1], FalseBranch);
  EXPECT_EQ(result.branchTarget[1], kCondJumpNoElseElseDest);
}

TEST_F(InsnUtilTest, DisasmsCallInsn) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match, db_.Lookup(0));
  EXPECT_THAT(Disasm(match), Eq("{ call 0x28 }"));
}

TEST_F(InsnUtilTest, DisasmsTrapInsn) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match, db_.Lookup(0x10));
  EXPECT_THAT(Disasm(match), Eq("{ trap0(#0x0) }"));
}

TEST_F(InsnUtilTest, DisasmsJumpInsn) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match, db_.Lookup(0x14));
  EXPECT_THAT(Disasm(match), Eq("{ jump 0x150 }"));
}

TEST_F(InsnUtilTest, DisasmsIfInsn) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match, db_.Lookup(0x60));
  EXPECT_THAT(Disasm(match), Eq("  if (P0.new) jump:t 0x194  "));
}

TEST_F(InsnUtilTest, DisasmsSubInsn) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match, db_.Lookup(0x14c));
  EXPECT_THAT(Disasm(match), Eq("{ R1 = #0x0; R2 = #0x0 }"));
}

TEST_F(InsnUtilTest, DisasmsImmext) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match, db_.Lookup(0x8));
  EXPECT_THAT(Disasm(match), Eq("{ immext(#0x0)  "));
  ASSERT_OK_AND_ASSIGN(match, db_.Lookup(0xc));
  EXPECT_THAT(Disasm(match), Eq("  R1 = ##0x18 }"));
}

TEST_F(InsnUtilTest, DisasmsCombineTwoImmexts) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match, db_.Lookup(0x60f8));
  EXPECT_THAT(Disasm(match), Eq("  R3:R2 = combine(#0x4,##0xffff) }"));
}

TEST_F(InsnUtilTest, DisasmsMemd) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match, db_.Lookup(0x7164));
  EXPECT_THAT(Disasm(match),
              Eq("  memd(SP+#0xfffffff0) = R17:R16; allocframe(#0x10) }"));
}

TEST_F(InsnUtilTest, DisasmsLoop) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match, db_.Lookup(0x1c0));
  EXPECT_THAT(Disasm(match), Eq("{ loop0(0x1c8,#0xa)  "));
  ASSERT_OK_AND_ASSIGN(match, db_.Lookup(0x1cc));
  EXPECT_THAT(Disasm(match), Eq("  nop }  :endloop0"));
}

TEST_F(InsnUtilTest, DoesNotAnnotateIndirectCalls) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match,
                       db_.Lookup(kIndirectCallAddress));
  InstructionInfo result;
  EXPECT_THAT(FillBnInstructionInfo(match, result), IsOk());
  EXPECT_EQ(result.branchCount, 0);
}

TEST_F(InsnUtilTest, DoesNotAnnotateCondIndirectJumps) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match, db_.Lookup(kCondIndirectJump));
  InstructionInfo result;
  EXPECT_THAT(FillBnInstructionInfo(match, result), IsOk());
  EXPECT_EQ(result.branchCount, 0);
}

TEST_F(InsnUtilTest, DisasmsIndirectJumps) {
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo match, db_.Lookup(kCondIndirectJump));
  EXPECT_THAT(Disasm(match), Eq("  if (P0) jumpr:nt R0 }"));
}

} // namespace

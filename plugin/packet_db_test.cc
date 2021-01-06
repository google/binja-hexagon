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

#include "plugin/packet_db.h"

#include "absl/status/status.h"
#include "plugin/status_matchers.h"
#include "gtest/gtest.h"

namespace {

using absl::IsOk;
using absl::MakeSpan;
using testing::Eq;
using testing::Not;

constexpr uint64_t kAddress = 0x1000;

TEST(PacketDbTest, FailsIfDataLessThanFour) {
  PacketDb db;
  std::vector<uint8_t> data(2);
  EXPECT_THAT(db.AddBytes(data, kAddress),
              absl::StatusIs(absl::StatusCode::kFailedPrecondition));
}

TEST(PacketDbTest, FailsIfDataNotMultipleOfFour) {
  PacketDb db;
  std::vector<uint8_t> data(5);
  EXPECT_THAT(db.AddBytes(data, kAddress),
              absl::StatusIs(absl::StatusCode::kFailedPrecondition));
}

TEST(PacketDbTest, FailsIfInsufficientData) {
  PacketDb db;
  // 13c:       c0 76 ea 0d 0dea76c0 {  immext(#3735924736)
  // 140:       11 28 b3 28 28b32811    r3 = ##3735924747;      r1 = #1 }
  std::vector<uint8_t> data = {0xc0, 0x76, 0xea, 0x0d};
  EXPECT_THAT(db.AddBytes(data, kAddress),
              absl::StatusIs(absl::StatusCode::kFailedPrecondition));
}

TEST(PacketDbTest, SucceedsIfAtLeastOnePacketAdded) {
  PacketDb db;
  //            00 e0 00 78 7800e000 {  r0 = #256 }
  // 13c:       c0 76 ea 0d 0dea76c0 {  immext(#3735924736)
  // 140:       11 28 b3 28 28b32811    r3 = ##3735924747;      r1 = #1 }
  std::vector<uint8_t> data = {0x00, 0xe0, 0x00, 0x78, 0xc0, 0x76, 0xea, 0x0d};
  EXPECT_THAT(db.AddBytes(data, kAddress), IsOk());
}

TEST(PacketDbTest, AddsAndLookupsSinglePacketOneInstruction) {
  PacketDb db;
  // 00 e0 00 78 7800e000 {  r0 = #256 }
  std::vector<uint8_t> data = {0x00, 0xe0, 0x00, 0x78};
  EXPECT_THAT(db.AddBytes(data, kAddress), IsOk());

  EXPECT_THAT(db.Lookup(kAddress - 1),
              absl::StatusIs(absl::StatusCode::kNotFound));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i0, db.Lookup(kAddress));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i1, db.Lookup(kAddress + 1));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i2, db.Lookup(kAddress + 2));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i3, db.Lookup(kAddress + 3));
  EXPECT_THAT(db.Lookup(kAddress + 4),
              absl::StatusIs(absl::StatusCode::kNotFound));
  EXPECT_THAT(i0.pc, kAddress);
  EXPECT_THAT(i1.pc, kAddress);
  EXPECT_THAT(i2.pc, kAddress);
  EXPECT_THAT(i3.pc, kAddress);
  EXPECT_THAT(i0.pkt, Eq(i1.pkt));
  EXPECT_THAT(i1.pkt, Eq(i2.pkt));
  EXPECT_THAT(i2.pkt, Eq(i3.pkt));
  EXPECT_THAT(i0.insn_addr, kAddress);
  EXPECT_THAT(i1.insn_addr, kAddress);
  EXPECT_THAT(i2.insn_addr, kAddress);
  EXPECT_THAT(i3.insn_addr, kAddress);
}

TEST(PacketDbTest, AddsAndLookupsSinglePacketTwoInstructions) {
  PacketDb db;
  // 13c:       c0 76 ea 0d 0dea76c0 {  immext(#3735924736)
  // 140:       11 28 b3 28 28b32811    r3 = ##3735924747;      r1 = #1 }
  std::vector<uint8_t> data = {0xc0, 0x76, 0xea, 0x0d, 0x11, 0x28, 0xb3, 0x28};
  EXPECT_THAT(db.AddBytes(data, kAddress), IsOk());

  EXPECT_THAT(db.Lookup(kAddress - 1),
              absl::StatusIs(absl::StatusCode::kNotFound));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i0, db.Lookup(kAddress));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i1, db.Lookup(kAddress + 1));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i2, db.Lookup(kAddress + 2));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i3, db.Lookup(kAddress + 3));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i4, db.Lookup(kAddress + 4));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i5, db.Lookup(kAddress + 5));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i6, db.Lookup(kAddress + 6));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i7, db.Lookup(kAddress + 7));
  EXPECT_THAT(db.Lookup(kAddress + 8),
              absl::StatusIs(absl::StatusCode::kNotFound));
  EXPECT_THAT(i0.pc, kAddress);
  EXPECT_THAT(i1.pc, kAddress);
  EXPECT_THAT(i2.pc, kAddress);
  EXPECT_THAT(i3.pc, kAddress);
  EXPECT_THAT(i4.pc, kAddress);
  EXPECT_THAT(i5.pc, kAddress);
  EXPECT_THAT(i6.pc, kAddress);
  EXPECT_THAT(i7.pc, kAddress);
  EXPECT_THAT(i0.pkt, Eq(i1.pkt));
  EXPECT_THAT(i1.pkt, Eq(i2.pkt));
  EXPECT_THAT(i2.pkt, Eq(i3.pkt));
  EXPECT_THAT(i3.pkt, Eq(i4.pkt));
  EXPECT_THAT(i4.pkt, Eq(i5.pkt));
  EXPECT_THAT(i5.pkt, Eq(i6.pkt));
  EXPECT_THAT(i6.pkt, Eq(i7.pkt));
  EXPECT_THAT(i0.insn_num, 0);
  EXPECT_THAT(i1.insn_num, 0);
  EXPECT_THAT(i2.insn_num, 0);
  EXPECT_THAT(i3.insn_num, 0);
  EXPECT_THAT(i4.insn_num, 1);
  EXPECT_THAT(i5.insn_num, 1);
  EXPECT_THAT(i6.insn_num, 2);
  EXPECT_THAT(i7.insn_num, 2);
  EXPECT_THAT(i0.insn_addr, kAddress);
  EXPECT_THAT(i1.insn_addr, kAddress);
  EXPECT_THAT(i2.insn_addr, kAddress);
  EXPECT_THAT(i3.insn_addr, kAddress);
  EXPECT_THAT(i4.insn_addr, kAddress + 4);
  EXPECT_THAT(i5.insn_addr, kAddress + 4);
  EXPECT_THAT(i6.insn_addr, kAddress + 6);
  EXPECT_THAT(i7.insn_addr, kAddress + 6);
}

TEST(PacketDbTest, AddsAndLookupsTwoAdjacentPackets) {
  PacketDb db;
  // 148:       5c ff ff 5b 5bffff5c {  call 0x0 <init> }
  //   c:       1e c0 1e 96 961ec01e {  dealloc_return }
  std::vector<uint8_t> data = {0x5c, 0xff, 0xff, 0x5b, 0x1e, 0xc0, 0x1e, 0x96};
  EXPECT_THAT(db.AddBytes(data, kAddress), IsOk());

  EXPECT_THAT(db.Lookup(kAddress - 1),
              absl::StatusIs(absl::StatusCode::kNotFound));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i0, db.Lookup(kAddress));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i1, db.Lookup(kAddress + 1));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i2, db.Lookup(kAddress + 2));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i3, db.Lookup(kAddress + 3));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i4, db.Lookup(kAddress + 4));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i5, db.Lookup(kAddress + 5));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i6, db.Lookup(kAddress + 6));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i7, db.Lookup(kAddress + 7));
  EXPECT_THAT(db.Lookup(kAddress + 8),
              absl::StatusIs(absl::StatusCode::kNotFound));
  EXPECT_THAT(i0.pc, kAddress);
  EXPECT_THAT(i1.pc, kAddress);
  EXPECT_THAT(i2.pc, kAddress);
  EXPECT_THAT(i3.pc, kAddress);
  EXPECT_THAT(i4.pc, kAddress + 4);
  EXPECT_THAT(i5.pc, kAddress + 4);
  EXPECT_THAT(i6.pc, kAddress + 4);
  EXPECT_THAT(i7.pc, kAddress + 4);
  EXPECT_THAT(i0.pkt, Eq(i1.pkt));
  EXPECT_THAT(i1.pkt, Eq(i2.pkt));
  EXPECT_THAT(i2.pkt, Eq(i3.pkt));
  EXPECT_THAT(i3.pkt, Not(Eq(i4.pkt)));
  EXPECT_THAT(i4.pkt, Eq(i5.pkt));
  EXPECT_THAT(i5.pkt, Eq(i6.pkt));
  EXPECT_THAT(i6.pkt, Eq(i7.pkt));
  EXPECT_THAT(i0.insn_addr, kAddress);
  EXPECT_THAT(i1.insn_addr, kAddress);
  EXPECT_THAT(i2.insn_addr, kAddress);
  EXPECT_THAT(i3.insn_addr, kAddress);
  EXPECT_THAT(i4.insn_addr, kAddress + 4);
  EXPECT_THAT(i5.insn_addr, kAddress + 4);
  EXPECT_THAT(i6.insn_addr, kAddress + 4);
  EXPECT_THAT(i7.insn_addr, kAddress + 4);
}

TEST(PacketDbTest, AddsAndLookupsTwoSeparatePackets) {
  constexpr uint64_t kAddress1 = 0x1000;
  constexpr uint64_t kAddress2 = 0x2000;
  PacketDb db;
  // 148:       5c ff ff 5b 5bffff5c {  call 0x0 <init> }
  //   c:       1e c0 1e 96 961ec01e {  dealloc_return }
  std::vector<uint8_t> data1 = {0x5c, 0xff, 0xff, 0x5b};
  std::vector<uint8_t> data2 = {0x1e, 0xc0, 0x1e, 0x96};
  EXPECT_THAT(db.AddBytes(data1, kAddress1), IsOk());
  EXPECT_THAT(db.AddBytes(data2, kAddress2), IsOk());

  EXPECT_THAT(db.Lookup(kAddress1 - 1),
              absl::StatusIs(absl::StatusCode::kNotFound));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i0, db.Lookup(kAddress1));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i1, db.Lookup(kAddress1 + 1));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i2, db.Lookup(kAddress1 + 2));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i3, db.Lookup(kAddress1 + 3));
  EXPECT_THAT(db.Lookup(kAddress1 + 4),
              absl::StatusIs(absl::StatusCode::kNotFound));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i4, db.Lookup(kAddress2));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i5, db.Lookup(kAddress2 + 1));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i6, db.Lookup(kAddress2 + 2));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i7, db.Lookup(kAddress2 + 3));
  EXPECT_THAT(db.Lookup(kAddress2 + 4),
              absl::StatusIs(absl::StatusCode::kNotFound));
  EXPECT_THAT(i0.pc, kAddress1);
  EXPECT_THAT(i1.pc, kAddress1);
  EXPECT_THAT(i2.pc, kAddress1);
  EXPECT_THAT(i3.pc, kAddress1);
  EXPECT_THAT(i4.pc, kAddress2);
  EXPECT_THAT(i5.pc, kAddress2);
  EXPECT_THAT(i6.pc, kAddress2);
  EXPECT_THAT(i7.pc, kAddress2);
  EXPECT_THAT(i0.pkt, Eq(i1.pkt));
  EXPECT_THAT(i1.pkt, Eq(i2.pkt));
  EXPECT_THAT(i2.pkt, Eq(i3.pkt));
  EXPECT_THAT(i3.pkt, Not(Eq(i4.pkt)));
  EXPECT_THAT(i4.pkt, Eq(i5.pkt));
  EXPECT_THAT(i5.pkt, Eq(i6.pkt));
  EXPECT_THAT(i6.pkt, Eq(i7.pkt));
  EXPECT_THAT(i0.insn_addr, kAddress1);
  EXPECT_THAT(i1.insn_addr, kAddress1);
  EXPECT_THAT(i2.insn_addr, kAddress1);
  EXPECT_THAT(i3.insn_addr, kAddress1);
  EXPECT_THAT(i4.insn_addr, kAddress2);
  EXPECT_THAT(i5.insn_addr, kAddress2);
  EXPECT_THAT(i6.insn_addr, kAddress2);
  EXPECT_THAT(i7.insn_addr, kAddress2);
}

TEST(PacketDbTest, OverwritesPacketInMap) {
  PacketDb db;
  // 148:       5c ff ff 5b 5bffff5c {  call 0x0 <init> }
  std::vector<uint8_t> data = {0x5c, 0xff, 0xff, 0x5b};
  EXPECT_THAT(db.AddBytes(data, kAddress), IsOk());
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i0, db.Lookup(kAddress));

  //   c:       1e c0 1e 96 961ec01e {  dealloc_return }
  data = {0x1e, 0xc0, 0x1e, 0x96};
  EXPECT_THAT(db.AddBytes(data, kAddress), IsOk());
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i1, db.Lookup(kAddress));
  EXPECT_THAT(i0.pkt, Not(Eq(i1.pkt)));
  EXPECT_THAT(i0.pkt.insn[0].iclass, Not(Eq(i1.pkt.insn[0].iclass)));
}

TEST(PacketDbTest, PacketWithEndLoop) {
  PacketDb db;
  // 1c8:       22 80 02 b0 b0028022 {  r2 = add(r2,#1)
  // 1cc:       00 c0 00 7f 7f00c000    nop }  :endloop0
  std::vector<uint8_t> data = {0x22, 0x80, 0x02, 0xb0, 0x00, 0xc0, 0x00, 0x7f};
  EXPECT_THAT(db.AddBytes(data, kAddress), IsOk());

  EXPECT_THAT(db.Lookup(kAddress - 1),
              absl::StatusIs(absl::StatusCode::kNotFound));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i0, db.Lookup(kAddress));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i4, db.Lookup(kAddress + 4));
  ASSERT_OK_AND_ASSIGN(PacketDb::InsnInfo i7, db.Lookup(kAddress + 7));
  EXPECT_THAT(db.Lookup(kAddress + 8),
              absl::StatusIs(absl::StatusCode::kNotFound));
  EXPECT_THAT(i0.pc, kAddress);
  EXPECT_THAT(i4.pc, kAddress);
  EXPECT_THAT(i7.pc, kAddress);
  EXPECT_THAT(i0.pkt, Eq(i4.pkt));
  EXPECT_THAT(i4.pkt, Eq(i7.pkt));
  EXPECT_THAT(i4.pkt.num_insns, 3);
  EXPECT_THAT(i4.insn_num, 1);
  // Returns the last instruction ('nop'), and not the pseudo
  // endloop instruction.
  EXPECT_THAT(i7.pkt.num_insns, 3);
  EXPECT_THAT(i7.insn_num, 1);
}

} // namespace

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

#include "plugin/packet_context.h"

#include "absl/memory/memory.h"
#include "plugin/hex_regs.h"
#include "third_party/qemu-hexagon/attribs.h"
#include "third_party/qemu-hexagon/iclass.h"
#include "third_party/qemu-hexagon/insn.h"
#include "third_party/qemu-hexagon/opcodes.h"

#include "glog/logging.h"

namespace {

using namespace BinaryNinja;

std::unique_ptr<TempReg> MakeTempReg(bool rw, int size, int reg,
                                     LowLevelILFunction &il) {
  if (rw) {
    return absl::make_unique<DestReadWriteReg>(size, reg, il);
  } else {
    return absl::make_unique<DestWriteOnlyReg>(size, reg);
  }
}

} // namespace

int MapRegNum(char regtype, int regno) {
  if (regtype == 'R' || regtype == 'N') {
    return HEX_REG_R00 + regno;
  }
  if (regtype == 'C') {
    return HEX_REG_C00 + regno;
  }
  if (regtype == 'P') {
    return HEX_REG_P0 + regno;
  }
  LOG(FATAL) << "Unknown regtype " << static_cast<int>(regtype);
  return -1;
}

void TempReg::CopyToTemp(BinaryNinja::LowLevelILFunction &il) {
  ExprId expr;
  if (size_ == 1) {
    expr = il.SetRegister(1, Reg(), il.Register(1, reg_));
  } else if (size_ == 4) {
    expr = il.SetRegister(4, Reg(), il.Register(4, reg_));
  } else {
    CHECK_EQ(size_, 8);
    expr = il.SetRegister(8, Reg(), il.RegisterSplit(4, reg_ + 1, reg_));
  }
  il.AddInstruction(expr);
}

void TempReg::CopyFromTemp(BinaryNinja::LowLevelILFunction &il) {
  ExprId expr;
  if (size_ == 1) {
    expr = il.SetRegister(1, reg_, il.Register(1, Reg()));
  } else if (size_ == 4) {
    expr = il.SetRegister(4, reg_, il.Register(4, Reg()));
  } else {
    CHECK_EQ(size_, 8);
    expr = il.SetRegisterSplit(4, reg_ + 1, reg_, il.Register(8, Reg()));
  }
  il.AddInstruction(expr);
}

PacketContext::PacketContext(BinaryNinja::LowLevelILFunction &il) : il_(il) {}

PacketContext::~PacketContext() {}

int PacketContext::AddDestWriteOnlyRegPair(int reg) {
  return AddDestReg(false, 8, reg);
}

int PacketContext::AddDestReadWriteRegPair(int reg) {
  return AddDestReg(true, 8, reg);
}
int PacketContext::AddDestWriteOnlyReg(int reg) {
  return AddDestReg(false, 4, reg);
}
int PacketContext::AddDestReadWriteReg(int reg) {
  return AddDestReg(true, 4, reg);
}
int PacketContext::AddDestWriteOnlyPredReg(int reg) {
  CHECK(reg == HEX_REG_P0 || reg == HEX_REG_P1 || reg == HEX_REG_P2 ||
        reg == HEX_REG_P3);
  return AddDestReg(false, 1, reg);
}
int PacketContext::AddDestReadWritePredReg(int reg) {
  CHECK(reg == HEX_REG_P0 || reg == HEX_REG_P1 || reg == HEX_REG_P2 ||
        reg == HEX_REG_P3);
  return AddDestReg(true, 1, reg);
}

int PacketContext::AddDestReg(bool rw, int size, int reg) {
  auto it = regs_.find(reg);
  if (it == regs_.end()) {
    auto out = regs_.emplace(reg, MakeTempReg(rw, size, reg, il_));
    DCHECK(out.second);
    it = out.first;
  } else {
    // TODO: handle the case where a dest register appears as a single 32b
    // register, and a 64b pair. For example,
    //
    //   {  if (p0) r0 = #0
    //      if (p0) r1 = #0
    //      if (!p0) r1:0 = memd(r3+#0) }
    //
    if (size != it->second->Size()) {
      LOG(WARNING) << "Req to add DestReg " << reg << " of size " << size
                   << " when it is already registered with size "
                   << it->second->Size();
    }
  }
  return it->second->Reg();
}

void PacketContext::WriteClobberedRegs() {
  for (auto &r : regs_) {
    r.second->CopyFromTemp(il_);
  }
}

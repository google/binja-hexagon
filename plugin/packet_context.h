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

#pragma once

#include <unordered_map>
#include <vector>

#include "absl/memory/memory.h"
#include "absl/types/optional.h"
#include "binaryninjaapi.h"
#include "plugin/hex_regs.h"
#include "third_party/qemu-hexagon/insn.h"

// Holds indirect branch destinations.
#define BRANCHR_DEST_ARRAY LLIL_TEMP(200)

// Holds conditional branch results.
#define BRANCH_TAKEN_ARRAY LLIL_TEMP(210)

// Maps insn.regno and regtype ('R', 'P') from insn type
// to HEX_REG enum value:
//   MapRegNum('R', 1) ->  HEX_REG_R01
//   MapRegNum('R', 8) ->  HEX_REG_R08
//   MapRegNum('P', 0) ->  HEX_REG_P0
//   MapRegNum('P', 1) ->  HEX_REG_P1
int MapRegNum(char regtype, int regno);

// Temporary source/dest register.
// Maps HEX_REG register to LLIL_TEMP register space:
//   HEX_REG_R00 -> LLIL_TEMP(HEX_REG_R00).
class TempReg {
public:
  TempReg(int size, int reg, int ss) : size_(size), reg_(reg), subspace_(ss) {}
  virtual ~TempReg() = default;
  TempReg(const TempReg &) = delete;
  TempReg &operator=(const TempReg &) = delete;

  int Size() const { return size_; }

  // Returns the register index in the LLIL_TEMP register space.
  int Reg() const { return LLIL_TEMP(subspace_ * NUM_HEX_REGS + reg_); }

  // Adds an IL SetRegister expression that copies the original register
  // value to LLIL_TEMP register.
  void CopyToTemp(BinaryNinja::LowLevelILFunction &il);

  // Adds an IL SetRegister expression that copies the LLIL_TEMP register
  // value to the original register.
  void CopyFromTemp(BinaryNinja::LowLevelILFunction &il);

protected:
  const int size_;
  const int reg_;
  const int subspace_;
};

// Register value is copied on construction.
class SourceReg : public TempReg {
public:
  SourceReg(int size, int reg, BinaryNinja::LowLevelILFunction &il)
      : TempReg(size, reg, /*subspace=*/0) {
    CopyToTemp(il);
  }
  ~SourceReg() override = default;
  SourceReg(const SourceReg &) = delete;
  SourceReg &operator=(const SourceReg &) = delete;
};

// Reads a register pair value on construction.
// Uses a separate LLIL_TEMP subspace to avoid collision with other temporary
// register pairs in the packet.
// See https://github.com/google/binja-hexagon/issues/5 for details.
class SourcePairReg : public TempReg {
public:
  SourcePairReg(int reg, BinaryNinja::LowLevelILFunction &il)
      : TempReg(/*size=*/8, reg, /*subspace=*/1) {
    CopyToTemp(il);
  }
  ~SourcePairReg() override = default;
  SourcePairReg(const SourcePairReg &) = delete;
  SourcePairReg &operator=(const SourcePairReg &) = delete;
};

class DestWriteOnlyReg : public TempReg {
public:
  DestWriteOnlyReg(int size, int reg) : TempReg(size, reg, /*subspace=*/0) {}
  ~DestWriteOnlyReg() override = default;
  DestWriteOnlyReg(const DestWriteOnlyReg &) = delete;
  DestWriteOnlyReg &operator=(const DestWriteOnlyReg &) = delete;
};

// Register value is copied on construction.
// LLIL_TEMP register value is copied back to normal register space
// when PacketContext.WriteClobberedRegs() is called.
class DestReadWriteReg : public SourceReg {
public:
  DestReadWriteReg(int size, int reg, BinaryNinja::LowLevelILFunction &il)
      : SourceReg(size, reg, il) {}
  ~DestReadWriteReg() override = default;
  DestReadWriteReg(const DestReadWriteReg &) = delete;
  DestReadWriteReg &operator=(const DestReadWriteReg &) = delete;
};

// Holds all temporary dest registers in the packet.
// Copies all dest registers back to original registers when
// WriteClobberedRegs() is called on packet destruction.
// Managing dest registers in LLIL_TEMP space helps implement the '.new'
// semantics.
class PacketContext {
public:
  PacketContext(BinaryNinja::LowLevelILFunction &il);
  ~PacketContext();
  PacketContext(const PacketContext &) = delete;
  PacketContext &operator=(const PacketContext &) = delete;

  BinaryNinja::LowLevelILFunction &IL() { return il_; }

  // Creates new DestReg and inserts it to |regs_| map if doesn't exist.
  // Returns the register index in the LLIL_TEMP register space.
  int AddDestWriteOnlyRegPair(int reg);
  int AddDestReadWriteRegPair(int reg);
  int AddDestWriteOnlyReg(int reg);
  int AddDestReadWriteReg(int reg);
  int AddDestWriteOnlyPredReg(int reg);
  int AddDestReadWritePredReg(int reg);

  // Adds IL instructions that write back all clobbered registers.
  void WriteClobberedRegs();

private:
  int AddDestReg(bool rw, int size, int reg);

  BinaryNinja::LowLevelILFunction &il_;
  std::unordered_map<int, std::unique_ptr<TempReg>> regs_;
};

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

#include "absl/strings/str_format.h"
#include "absl/types/span.h"
#include "binaryninjaapi.h"
#include "glog/logging.h"
#include "lowlevelilinstruction.h"
#include "plugin/hex_regs.h"
#include "plugin/il_util.h"
#include "plugin/insn_util.h"
#include "plugin/packet_db.h"

using namespace BinaryNinja;

class HexagonCallingConvention : public CallingConvention {
public:
  HexagonCallingConvention(Architecture *arch)
      : CallingConvention(arch, "regparam") {}

  virtual std::vector<uint32_t> GetIntegerArgumentRegisters() override {
    return std::vector<uint32_t>{HEX_REG_R00, HEX_REG_R01, HEX_REG_R02,
                                 HEX_REG_R03, HEX_REG_R04, HEX_REG_R05,
                                 HEX_REG_R06, HEX_REG_R07, HEX_REG_R08};
  }

  virtual std::vector<uint32_t> GetCallerSavedRegisters() override {
    return std::vector<uint32_t>{};
  }

  virtual std::vector<uint32_t> GetCalleeSavedRegisters() override {
    return std::vector<uint32_t>{HEX_REG_FP, HEX_REG_LR};
  }

  virtual uint32_t GetGlobalPointerRegister() override { return HEX_REG_GP; }

  virtual uint32_t GetIntegerReturnValueRegister() override {
    return HEX_REG_R00;
  }

  virtual uint32_t GetHighIntegerReturnValueRegister() override {
    return HEX_REG_R01;
  }

  virtual bool IsStackAdjustedOnReturn() override { return true; }
};

class HexagonArchitecture : public Architecture {
protected:
public:
  HexagonArchitecture(const std::string &name) : Architecture(name) {}

  size_t GetAddressSize() const override { return 4; }
  BNEndianness GetEndianness() const override { return LittleEndian; }
  size_t GetInstructionAlignment() const override { return 4; }
  size_t GetMaxInstructionLength() const override {
    return 16; // Up to four instructions in a packet.
  }

  bool GetInstructionInfo(const uint8_t *data, uint64_t addr, size_t maxLen,
                          InstructionInfo &result) override {
    auto match_or = packet_db_.Lookup(addr);
    if (!match_or.ok()) {
      if (!packet_db_.AddBytes(absl::MakeConstSpan(data, maxLen), addr).ok()) {
        return false;
      }
      match_or = packet_db_.Lookup(addr);
      CHECK(match_or.ok()) << "Lookup() failed after AddBytes()";
    }
    auto status = FillBnInstructionInfo(match_or.value(), result);
    if (!status.ok()) {
      LOG(WARNING) << "FillBnInstructionInfo failed " << status;
      return false;
    }
    return true;
  }

  bool GetInstructionText(const uint8_t *data, uint64_t addr, size_t &len,
                          std::vector<InstructionTextToken> &result) override {
    auto match_or = packet_db_.Lookup(addr);
    if (!match_or.ok()) {
      if (!packet_db_.AddBytes(absl::MakeConstSpan(data, len), addr).ok()) {
        return false;
      }
      match_or = packet_db_.Lookup(addr);
      CHECK(match_or.ok()) << "Lookup() failed after AddBytes()";
    }
    auto status = FillBnInstructionTextTokens(match_or.value(), len, result);
    if (!status.ok()) {
      LOG(WARNING) << "FillBnInstructionTextTokens failed " << status;
      return false;
    }
    return true;
  }

  bool GetInstructionLowLevelIL(const uint8_t *data, uint64_t addr, size_t &len,
                                LowLevelILFunction &il) override {
    auto match_or = packet_db_.Lookup(addr);
    if (!match_or.ok()) {
      if (!packet_db_.AddBytes(absl::MakeConstSpan(data, len), addr).ok()) {
        return false;
      }
      match_or = packet_db_.Lookup(addr);
      CHECK(match_or.ok()) << "Lookup() failed after AddBytes()";
    }
    auto status = FillBnInstructionLowLevelIL(this, match_or.value(), len, il);
    if (!status.ok()) {
      LOG(WARNING) << "FillBnInstructionLowLevelIL failed " << status;
      return false;
    }
    return true;
  }

  std::vector<uint32_t> GetFullWidthRegisters() override {
    // TODO: add VRegs, QRegs.
    return std::vector<uint32_t>{
        HEX_REG_R00, HEX_REG_R01, HEX_REG_R02, HEX_REG_R03, HEX_REG_R04,
        HEX_REG_R05, HEX_REG_R06, HEX_REG_R07, HEX_REG_R08, HEX_REG_R09,
        HEX_REG_R10, HEX_REG_R11, HEX_REG_R12, HEX_REG_R13, HEX_REG_R14,
        HEX_REG_R15, HEX_REG_R16, HEX_REG_R17, HEX_REG_R18, HEX_REG_R19,
        HEX_REG_R20, HEX_REG_R21, HEX_REG_R22, HEX_REG_R23, HEX_REG_R24,
        HEX_REG_R25, HEX_REG_R26, HEX_REG_R27, HEX_REG_R28, HEX_REG_R29,
        HEX_REG_R30, HEX_REG_R31, HEX_REG_C00, HEX_REG_C01, HEX_REG_C02,
        HEX_REG_C03, HEX_REG_C04, HEX_REG_C05, HEX_REG_C06, HEX_REG_C07,
        HEX_REG_C08, HEX_REG_C09, HEX_REG_C10, HEX_REG_C11, HEX_REG_C12,
        HEX_REG_C13, HEX_REG_C14, HEX_REG_C15, HEX_REG_C16, HEX_REG_C17,
        HEX_REG_C18, HEX_REG_C19, HEX_REG_C20, HEX_REG_C21, HEX_REG_C22,
        HEX_REG_C23, HEX_REG_C24, HEX_REG_C25, HEX_REG_C26, HEX_REG_C27,
        HEX_REG_C28, HEX_REG_C29, HEX_REG_C30, HEX_REG_C31,
    };
  }

  std::vector<uint32_t> GetAllRegisters() override {
    // TODO: add VRegs, QRegs.
    return std::vector<uint32_t>{
        HEX_REG_R00, HEX_REG_R01, HEX_REG_R02, HEX_REG_R03,      HEX_REG_R04,
        HEX_REG_R05, HEX_REG_R06, HEX_REG_R07, HEX_REG_R08,      HEX_REG_R09,
        HEX_REG_R10, HEX_REG_R11, HEX_REG_R12, HEX_REG_R13,      HEX_REG_R14,
        HEX_REG_R15, HEX_REG_R16, HEX_REG_R17, HEX_REG_R18,      HEX_REG_R19,
        HEX_REG_R20, HEX_REG_R21, HEX_REG_R22, HEX_REG_R23,      HEX_REG_R24,
        HEX_REG_R25, HEX_REG_R26, HEX_REG_R27, HEX_REG_R28,      HEX_REG_R29,
        HEX_REG_R30, HEX_REG_R31, HEX_REG_C00, HEX_REG_C01,      HEX_REG_C02,
        HEX_REG_C03, HEX_REG_C04, HEX_REG_C05, HEX_REG_C06,      HEX_REG_C07,
        HEX_REG_C08, HEX_REG_C09, HEX_REG_C10, HEX_REG_C11,      HEX_REG_C12,
        HEX_REG_C13, HEX_REG_C14, HEX_REG_C15, HEX_REG_C16,      HEX_REG_C17,
        HEX_REG_C18, HEX_REG_C19, HEX_REG_C20, HEX_REG_C21,      HEX_REG_C22,
        HEX_REG_C23, HEX_REG_C24, HEX_REG_C25, HEX_REG_C26,      HEX_REG_C27,
        HEX_REG_C28, HEX_REG_C29, HEX_REG_C30, HEX_REG_C31,      HEX_REG_P0,
        HEX_REG_P1,  HEX_REG_P2,  HEX_REG_P3,  HEX_REG_USR_LPCFG};
  }

  std::vector<uint32_t> GetAllFlags() override {
    return std::vector<uint32_t>{};
  }

  std::string GetRegisterName(uint32_t reg) override {
    switch (reg) {
    case HEX_REG_R00 ... HEX_REG_R28:
      return absl::StrFormat("R%d", reg - HEX_REG_R00);
    case HEX_REG_SP: // R29
      return "SP";
    case HEX_REG_FP: // R30
      return "FP";
    case HEX_REG_LR: // R31
      return "LR";
    case HEX_REG_SA0: // C00
      return "SA0";
    case HEX_REG_LC0: // C01
      return "LC0";
    case HEX_REG_SA1: // C02
      return "SA1";
    case HEX_REG_LC1: // C03
      return "LC1";
    case HEX_REG_P3_0: // C04
      return "P3:0";
    case HEX_REG_C05:
      return "C5";
    case HEX_REG_M0: // C06
      return "M0";
    case HEX_REG_M1: // C07
      return "M1";
    case HEX_REG_USR: // C08
      return "USR";
    case HEX_REG_PC: // C09
      return "PC";
    case HEX_REG_UGP: // C10
      return "UGP";
    case HEX_REG_GP: // C11
      return "GP";
    case HEX_REG_CS0: // C12
      return "CS0";
    case HEX_REG_CS1: // C13
      return "CS1";
    case HEX_REG_C14 ... HEX_REG_C31:
      return absl::StrFormat("C%d", reg - HEX_REG_C00);
    case HEX_REG_P0: // Subreg of HEX_REG_P3_0
      return "P0";
    case HEX_REG_P1: // Subreg of HEX_REG_P3_0
      return "P1";
    case HEX_REG_P2: // Subreg of HEX_REG_P3_0
      return "P2";
    case HEX_REG_P3: // Subreg of HEX_REG_P3_0
      return "P3";
    case HEX_REG_USR_LPCFG: // Subreg of HEX_REG_USR
      return "LPCFG";
    default:
      LOG(ERROR) << "Unexpected GetRegisterName for reg " << reg;
    }
    return "??";
  }

  std::string GetFlagName(uint32_t flag) override {
    LOG(FATAL) << "Unexpected GetFlagName for flag " << flag;
    return "";
  }

  virtual BNRegisterInfo GetRegisterInfo(uint32_t reg) override {
    // Skip temp registers.
    if (LLIL_REG_IS_TEMP(reg)) {
      // TODO: map single 32b registers to 64b pairs in LLIL_TEMP register
      // space.
      switch (LLIL_GET_TEMP_REG_INDEX(reg)) {
      case HEX_REG_P0:
      case HEX_REG_P1:
      case HEX_REG_P2:
      case HEX_REG_P3:
        return BNRegisterInfo{reg, 0, 1, NoExtend};
      default:
        return BNRegisterInfo{reg, 0, 4, NoExtend};
      }
    }

    // All registers are 32bit long.
    // TODO: add support for ".L", ".H" sub registers.
    switch (reg) {
    case HEX_REG_P0:
      return BNRegisterInfo{HEX_REG_P3_0, 0, 1, NoExtend};
    case HEX_REG_P1:
      return BNRegisterInfo{HEX_REG_P3_0, 1, 1, NoExtend};
    case HEX_REG_P2:
      return BNRegisterInfo{HEX_REG_P3_0, 2, 1, NoExtend};
    case HEX_REG_P3:
      return BNRegisterInfo{HEX_REG_P3_0, 3, 1, NoExtend};
    case HEX_REG_USR_LPCFG:
      CHECK_EQ(reg_field_info[REG_FIELD_USR_LPCFG].offset, 8);
      return BNRegisterInfo{HEX_REG_USR, 1, 1, NoExtend};
    case HEX_REG_R00 ... HEX_REG_R31:
      return BNRegisterInfo{reg, 0, 4, NoExtend};
    case HEX_REG_C00 ... HEX_REG_C31:
      return BNRegisterInfo{reg, 0, 4, NoExtend};
    default:
      LOG(ERROR) << "Unexpected GetRegisterInfo for reg " << reg;
    }
    return BNRegisterInfo{reg, 0, 4, NoExtend};
  }

  uint32_t GetStackPointerRegister() override { return HEX_REG_SP; }

  uint32_t GetLinkRegister() override { return HEX_REG_LR; }

private:
  PacketDb packet_db_;
};

extern "C" {
BN_DECLARE_CORE_ABI_VERSION
BINARYNINJAPLUGIN bool CorePluginInit() {
  Architecture *hexagon = new HexagonArchitecture("hexagon");
  Architecture::Register(hexagon);

  // Register calling convention.
  Ref<CallingConvention> conv;
  conv = new HexagonCallingConvention(hexagon);
  hexagon->RegisterCallingConvention(conv);
  hexagon->SetDefaultCallingConvention(conv);
  hexagon->SetCdeclCallingConvention(conv);
  hexagon->SetFastcallCallingConvention(conv);
  hexagon->SetStdcallCallingConvention(conv);

  // Register binary format parsers.
  BinaryViewType::RegisterArchitecture("ELF", 164, LittleEndian, hexagon);
  return true;
}
}

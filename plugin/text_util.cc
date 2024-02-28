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
#include "plugin/text_util.h"

#include "absl/strings/str_cat.h"
#include "glog/logging.h"
#include "plugin/hex_regs.h"

namespace {

std::string GeneralRegisterName(uint32_t reg) {
  switch (reg) {
  case HEX_REG_R00 ... HEX_REG_R28:
    return absl::StrCat("R", reg - HEX_REG_R00);
  case HEX_REG_SP: // R29
    return "SP";
  case HEX_REG_FP: // R30
    return "FP";
  case HEX_REG_LR: // R31
    return "LR";
  default:
    LOG(FATAL) << "Unexpected general register reg " << reg;
  }
  return "";
}

std::string ControlRegisterName(uint32_t reg) {
  switch (reg) {
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
    return absl::StrCat("C", reg - HEX_REG_C00);
  default:
    LOG(FATAL) << "Unexpected control register reg " << reg;
  }
  return "";
}

std::string PredicateRegisterName(uint32_t reg) {
  switch (reg) {
  case HEX_REG_P0:
    return "P0";
  case HEX_REG_P1:
    return "P1";
  case HEX_REG_P2:
    return "P2";
  case HEX_REG_P3:
    return "P3";
  default:
    LOG(FATAL) << "Unexpected predicate register reg " << reg;
  }
  return "";
}

std::string SystemRegisterName(uint32_t reg) {
  switch (reg) {
  case HEX_SREG_SGP0:
    return "SGP0";
  case HEX_SREG_SGP1:
    return "SGP1";
  case HEX_SREG_STID:
    return "STID";
  case HEX_SREG_ELR:
    return "ELR";
  case HEX_SREG_BADVA0:
    return "BADVA0";
  case HEX_SREG_BADVA1:
    return "BADVA1";
  case HEX_SREG_SSR:
    return "SSR";
  case HEX_SREG_CCR:
    return "CCR";
  case HEX_SREG_HTID:
    return "HTID";
  case HEX_SREG_BADVA:
    return "BADVA";
  case HEX_SREG_IMASK:
    return "IMASK";
  case HEX_SREG_GEVB:
    return "GEVB";
  case HEX_SREG_EVB:
    return "EVB";
  case HEX_SREG_MODECTL:
    return "MODECTL";
  case HEX_SREG_SYSCFG:
    return "SYSCFG";
  case HEX_SREG_IPENDAD:
    return "IPENDAD";
  case HEX_SREG_VID:
    return "VID";
  case HEX_SREG_VID1:
    return "VID1";
  case HEX_SREG_BESTWAIT:
    return "BESTWAIT";
  case HEX_SREG_IEL:
    return "IEL";
  case HEX_SREG_SCHEDCFG:
    return "SCHEDCFG";
  case HEX_SREG_IAHL:
    return "IAHL";
  case HEX_SREG_CFGBASE:
    return "CFGBASE";
  case HEX_SREG_DIAG:
    return "DIAG";
  case HEX_SREG_REV:
    return "REV";
  case HEX_SREG_PCYCLELO:
    return "PCYCLELO";
  case HEX_SREG_PCYCLEHI:
    return "PCYCLEHI";
  case HEX_SREG_ISDBST:
    return "ISDBST";
  case HEX_SREG_ISDBCFG0:
    return "ISDBCFG0";
  case HEX_SREG_ISDBCFG1:
    return "ISDBCFG1";
  case HEX_SREG_LIVELOCK:
    return "LIVELOCK";
  case HEX_SREG_BRKPTPC0:
    return "BRKPTPC0";
  case HEX_SREG_BRKPTCFG0:
    return "BRKPTCFG0";
  case HEX_SREG_BRKPTPC1:
    return "BRKPTPC1";
  case HEX_SREG_BRKPTCFG1:
    return "BRKPTCFG1";
  case HEX_SREG_ISDBMBXIN:
    return "ISDBMBXIN";
  case HEX_SREG_ISDBMBXOUT:
    return "ISDBMBXOUT";
  case HEX_SREG_ISDBEN:
    return "ISDBEN";
  case HEX_SREG_ISDBGPR:
    return "ISDBGPR";
  case HEX_SREG_PMUCNT4:
    return "PMUCNT4";
  case HEX_SREG_PMUCNT5:
    return "PMUCNT5";
  case HEX_SREG_PMUCNT6:
    return "PMUCNT6";
  case HEX_SREG_PMUCNT7:
    return "PMUCNT7";
  case HEX_SREG_PMUCNT0:
    return "PMUCNT0";
  case HEX_SREG_PMUCNT1:
    return "PMUCNT1";
  case HEX_SREG_PMUCNT2:
    return "PMUCNT2";
  case HEX_SREG_PMUCNT3:
    return "PMUCNT3";
  case HEX_SREG_PMUEVTCFG:
    return "PMUEVTCFG";
  case HEX_SREG_PMUSTID0:
    return "PMUSTID0";
  case HEX_SREG_PMUEVTCFG1:
    return "PMUEVTCFG1";
  case HEX_SREG_PMUSTID1:
    return "PMUSTID1";
  case HEX_SREG_TIMERLO:
    return "TIMERLO";
  case HEX_SREG_TIMERHI:
    return "TIMERHI";
  case HEX_SREG_PMUCFG:
    return "PMUCFG";
  case HEX_SREG_S59:
    return "S59";
  case HEX_SREG_S60:
    return "S60";
  case HEX_SREG_S61:
    return "S61";
  case HEX_SREG_S62:
    return "S62";
  case HEX_SREG_S63:
    return "S63";
  case HEX_SREG_COMMIT1T:
    return "COMMIT1T";
  case HEX_SREG_COMMIT2T:
    return "COMMIT2T";
  case HEX_SREG_COMMIT3T:
    return "COMMIT3T";
  case HEX_SREG_COMMIT4T:
    return "COMMIT4T";
  case HEX_SREG_COMMIT5T:
    return "COMMIT5T";
  case HEX_SREG_COMMIT6T:
    return "COMMIT6T";
  case HEX_SREG_PCYCLE1T:
    return "PCYCLE1T";
  case HEX_SREG_PCYCLE2T:
    return "PCYCLE2T";
  case HEX_SREG_PCYCLE3T:
    return "PCYCLE3T";
  case HEX_SREG_PCYCLE4T:
    return "PCYCLE4T";
  case HEX_SREG_PCYCLE5T:
    return "PCYCLE5T";
  case HEX_SREG_PCYCLE6T:
    return "PCYCLE6T";
  case HEX_SREG_STFINST:
    return "STFINST";
  case HEX_SREG_ISDBCMD:
    return "ISDBCMD";
  case HEX_SREG_ISDBVER:
    return "ISDBVER";
  case HEX_SREG_BRKPTINFO:
    return "BRKPTINFO";
  case HEX_SREG_RGDR3:
    return "RGDR3";
  case HEX_SREG_COMMIT7T:
    return "COMMIT7T";
  case HEX_SREG_COMMIT8T:
    return "COMMIT8T";
  case HEX_SREG_PCYCLE7T:
    return "PCYCLE7T";
  case HEX_SREG_PCYCLE8T:
    return "PCYCLE8T";
  case HEX_SREG_S85:
    return "S85";
  default:
    LOG(FATAL) << "Unexpected system register reg " << reg;
  }
  return "";
}

} // namespace

std::string GetRegisterName(absl::string_view reg_type,
                            absl::string_view hi_low_modifier, int regno) {
  std::string out;
  if (reg_type == "R" || reg_type == "N") {
    out = GeneralRegisterName(HEX_REG_R00 + regno);
  } else if (reg_type == "C") {
    out = ControlRegisterName(HEX_REG_C00 + regno);
  } else if (reg_type == "P") {
    out = PredicateRegisterName(HEX_REG_P0 + regno);
  } else if (reg_type == "S") {
    out = SystemRegisterName(HEX_SREG_SGP0 + regno);
  } else {
    out = absl::StrCat(reg_type, regno);
  }
  if (!hi_low_modifier.empty()) {
    absl::StrAppend(&out, ".", hi_low_modifier);
  }
  return out;
}

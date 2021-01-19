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
  } else {
    out = absl::StrCat(reg_type, regno);
  }
  if (!hi_low_modifier.empty()) {
    absl::StrAppend(&out, ".", hi_low_modifier);
  }
  return out;
}

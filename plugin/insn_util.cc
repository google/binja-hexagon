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
#include "glog/logging.h"
#include "plugin/status_macros.h"

// Defined in insn_text_funcs_generated.cc.
typedef void (*InsnTextFunc)(
    uint64_t pc, const Packet &pkt, const Insn &insn,
    std::vector<BinaryNinja::InstructionTextToken> &result);

extern const InsnTextFunc opcode_textptr[XX_LAST_OPCODE];

namespace {

using namespace BinaryNinja;
using absl::Hex;
using absl::StrCat;

int GetLastInsn(const Packet &pkt) {
  int last_insn = pkt.num_insns - 1;
  if (pkt.insn[last_insn].is_endloop) {
    last_insn--;
  }
  return last_insn;
}

absl::Status
FillBnInstructionTextTokensImpl(uint64_t pc, const Packet &pkt,
                                const Insn &insn,
                                std::vector<InstructionTextToken> &result) {
  if (opcode_textptr[insn.opcode] == nullptr) {
    return absl::InvalidArgumentError(
        StrCat("Unsupported opcode ", insn.opcode));
  }
  opcode_textptr[insn.opcode](pc, pkt, insn, result);
  return absl::OkStatus();
}

} // namespace

bool IsSubInsn(const Insn &insn) { return GET_ATTRIB(insn.opcode, A_SUBINSN); }
bool IsJump(const Insn &insn) {
  return GET_ATTRIB(insn.opcode, A_JUMP) && insn.opcode != J4_hintjumpr;
}
bool IsCall(const Insn &insn) { return GET_ATTRIB(insn.opcode, A_CALL); }
bool IsIndirect(const Insn &insn) {
  return GET_ATTRIB(insn.opcode, A_INDIRECT) && insn.opcode != J4_hintjumpr;
}
bool IsCondJump(const Insn &insn) {
  return GET_ATTRIB(insn.opcode, A_BN_COND_J);
}
bool IsReturn(const Insn &insn) { return GET_ATTRIB(insn.opcode, A_BN_RETURN); }
bool IsSystem(const Insn &insn) { return GET_ATTRIB(insn.opcode, A_BN_SYSTEM); }

absl::Status FillBnInstructionInfo(const PacketDb::InsnInfo &input,
                                   BinaryNinja::InstructionInfo &result) {
  if (input.insn_addr & 3) {
    return absl::InvalidArgumentError(
        StrCat("Got unaligned insn address ", Hex(input.insn_addr)));
  }
  result.length = 4;
  const Packet &pkt = input.pkt;
  int last_insn = GetLastInsn(pkt);
  if (!((input.insn_num == last_insn) || (IsSubInsn(pkt.insn[input.insn_num]) &&
                                          input.insn_num + 1 == last_insn))) {
    // Populate Packet's branch information only at the last instruction.
    return absl::OkStatus();
  }
  bool has_cj = false;
  bool has_ucj = false;
  for (int i = 0; i < pkt.num_insns; i++) {
    const Insn &insn = pkt.insn[i];
    has_cj |= IsJump(insn) && !IsIndirect(insn) && IsCondJump(insn);
    has_ucj |= IsJump(insn) && !IsIndirect(insn) && !IsCondJump(insn);
  }

  for (int i = 0; i < pkt.num_insns; i++) {
    const Insn &insn = pkt.insn[i];
    if (IsReturn(insn)) {
      if (IsCondJump(insn)) {
        // Skip, and do not annotate conditional returns.
      } else {
        result.AddBranch(FunctionReturn);
      }
    } else if (IsSystem(insn)) {
      if (IsCondJump(insn)) {
        // Skip, and do not annotate conditional, indirect jumps.
      } else {
        result.AddBranch(SystemCall);
      }
    } else if (IsJump(insn)) {
      if (IsIndirect(insn)) {
        if (IsCondJump(insn)) {
          // Skip, and do not annotate conditional, indirect jumps.
        } else {
          result.AddBranch(IndirectBranch);
        }
      } else if (IsCondJump(insn)) {
        result.AddBranch(TrueBranch, input.pc + insn.immed[0]);
        if (!has_ucj) {
          // Add implicit 'else' case.
          result.AddBranch(FalseBranch, input.pc + pkt.encod_pkt_size_in_bytes);
        }
      } else {
        auto type = UnconditionalBranch;
        if (has_cj) {
          // Add explicity 'else' case.
          type = FalseBranch;
        }
        result.AddBranch(type, input.pc + insn.immed[0]);
      }
    } else if (IsCall(insn)) {
      if (IsIndirect(insn)) {
        // Skip, and do not annotate indirect calls.
      } else {
        result.AddBranch(CallDestination, input.pc + insn.immed[0]);
      }
    }
  }
  return absl::OkStatus();
}

absl::Status FillBnInstructionTextTokens(
    const PacketDb::InsnInfo &input, size_t &len,
    std::vector<BinaryNinja::InstructionTextToken> &result) {
  if (input.insn_addr & 3) {
    return absl::InvalidArgumentError(
        StrCat("Got unaligned insn address ", Hex(input.insn_addr)));
  }
  const Packet &pkt = input.pkt;
  uint32_t insn_num = input.insn_num;
  const Insn &insn = pkt.insn[insn_num];
  // Sub instructions (2B) are printed as a single instruction.
  len = 4;
  result.emplace_back(TextToken, (input.insn_num == 0 ? "{ " : "  "));
  RETURN_IF_ERROR(FillBnInstructionTextTokensImpl(input.pc, pkt, insn, result));
  if (IsSubInsn(insn)) {
    CHECK_LT(++insn_num, pkt.num_insns);
    const Insn &next = pkt.insn[insn_num];
    result.emplace_back(TextToken, "; ");
    RETURN_IF_ERROR(
        FillBnInstructionTextTokensImpl(input.pc, pkt, next, result));
  }
  int last_insn = GetLastInsn(pkt);
  if (insn_num == last_insn) {
    result.emplace_back(TextToken, " }");
    if (pkt.pkt_has_endloop) {
      switch (pkt.insn[last_insn + 1].opcode) {
      case J2_endloop0:
        result.emplace_back(TextToken, "  :endloop0");
        break;
      case J2_endloop1:
        result.emplace_back(TextToken, "  :endloop1");
        break;
      case J2_endloop01:
        result.emplace_back(TextToken, "  :endloop01");
        break;
      }
    }
  } else {
    result.emplace_back(TextToken, "  ");
  }
  return absl::OkStatus();
}

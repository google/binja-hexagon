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

#include "absl/memory/memory.h"
#include "absl/strings/str_cat.h"
#include "binaryninjaapi.h"
#include "glog/logging.h"
#include "plugin/hex_regs.h"
#include "plugin/insn_util.h"
#include "plugin/packet_context.h"
#include "plugin/status_macros.h"
#include "third_party/qemu-hexagon/decode.h"

// Defined in il_funcs_generated.cc.
typedef void (*IlLiftFunc)(BinaryNinja::Architecture *arch, uint64_t pc,
                           const Packet &pkt, const Insn &insn, int insn_num,
                           PacketContext &ctx);

extern const IlLiftFunc opcode_liftptr[XX_LAST_OPCODE];

namespace {

using namespace BinaryNinja;
using absl::Hex;
using absl::StrCat;

absl::Status FillBnInstructionLowLevelImpl(Architecture *arch, uint64_t pc,
                                           const Packet &pkt, const Insn &insn,
                                           int insn_num, PacketContext &ctx) {
  LowLevelILFunction &il = ctx.IL();
  if (opcode_liftptr[insn.opcode] == nullptr) {
    il.AddInstruction(il.Undefined());
#ifndef NDEBUG
    LOG(INFO) << "Unsupported lifter for '" << opcode_names[insn.opcode]
              << "' at " << std::hex << "0x" << pc;
#endif
    return absl::OkStatus();
  }
  opcode_liftptr[insn.opcode](arch, pc, pkt, insn, insn_num, ctx);
  return absl::OkStatus();
}

} // namespace

Packet PreparePacketForLifting(const Packet &src) {
  Packet copy = src;
  decode_remove_extenders(&copy);
  decode_shuffle_for_execution(&copy);
  decode_split_cmpjump(&copy);
  return copy;
}

absl::Status FillBnInstructionLowLevelIL(Architecture *arch,
                                         const PacketDb::InsnInfo &input,
                                         size_t &len, LowLevelILFunction &il) {
  if (input.insn_addr & 3) {
    return absl::InvalidArgumentError(
        StrCat("Got unaligned insn address ", Hex(input.insn_addr)));
  }

  // Populate IL info only at the beginning of a packet.
  if (input.insn_num != 0) {
    return absl::OkStatus();
  }

  // Re-order instructions for easier processing.
  Packet pkt = PreparePacketForLifting(input.pkt);
  len = pkt.encod_pkt_size_in_bytes;

  // There are many types of branches:
  //   {conditional, non-conditional} x {direct, indirect} x {call, jump}
  // And a packet can have up to two distinct branch instructions.
  //
  // Branch semantics dictate:
  //   A. Post execution: A branch happens only after all packet instructions
  //   have been executed.
  //   B. Single execution: At exit, the CPU takes only a single branch, even if
  //   there are two branches in the packet.
  //   C. Ordering: Branches have a priority based on their encoding order in
  //   the packet. For example, if a packet has a conditional branch, followed
  //   by a non-conditional branch:
  //       { r1 = add(r1, r1)
  //         if (p0) jump:t 1f
  //         jump 2f }
  //   and the condition is met (p0) - then only the conditional branch is
  //   taken. This is also true for calls:
  //       { r1 = add(r1, r1)
  //         if (p0) call 1f
  //         jump 2f }
  //   If the condition is met (p0) - then the call is performed, and the return
  //   address (LR) is set to the next packet. The non-conditional branch (jump
  //   2f) is skipped.
  //
  // A naive implementation for branch semantics could use a LLIL_TEMP register
  // to track the branch destination and branch type:
  //
  //   lifter_jump():
  //     fWRITE_NPC:
  //      LLIL_TEMP(dest) <- branch dest expression, if LLIL_TEMP(dest) has not
  //      been set.
  //      LLIL_TEMP(type) <- branch type (jump, jumpr, call, callr).
  //   }
  //
  // Then here we would switch on the dest/type:
  //   il.AddInstruction(Il.If( .. ));
  //   il.MarkLabel(jump_case);
  //   il.AddInstruction(Il.Jump(LLIL_TEMP(dest));
  //   il.MarkLabel(call_case);
  //   il.AddInstruction(Il.Call(LLIL_TEMP(dest));
  //   ..
  //
  // However, this implementation gave poor decompilation results.
  //
  // Instead, we have this more involved implementation for branch semantics.
  // We track whether a conditional jump is taken in a symbolic, LLIL_TEMP
  // register, unique for that instruction number (BRANCH_TAKEN_ARRAY+insn_num).
  // In case of an indirect branch (jumpr, callr), we also track branch
  // destination: the branch destination expression result is stored in a unique
  // LLIL_TEMP register.
  // Later, after all packet instructions have been processed, and clobbered
  // registers have been written back, we add Il.If statements that test each
  // conditional result (in order), and perform the branch. In some cases, we
  // use decoder's information to compute the branch destination.
  //
  // For example, the following packet has a conditional call, and an
  // unconditional jump:
  //
  //   { if (P0) call 0x104
  //     jump 0x108
  //     R1 = add(R1,R1) }
  //
  // Its LLIL representation is the following:
  //
  //   0: temp210.b = 0
  //   1: if (P0.d) then 2 else 4
  //   2: temp210.b = 1
  //   3: goto 4
  //   4: temp1.d = R1 + R1
  //   5: R1 = temp1.d
  //   6: if (temp210.b == 1) then 7 else 9
  //   7: call(0x104)
  //   8: goto 10
  //   9: jump(0x108 => 11 @ 0x108)
  //   10: <return> tailcall(0x104)
  //
  // temp210 is the BRANCH_TAKEN flag for instruction number 0 (cond call).
  // When the branch condition passes (line 2), BRANCH_TAKEN is set to 1.
  // Lines 4,5 write back all clobbered registers after all packet instructions
  // have been processed.
  // Line 6 tests the BRANCH_TAKEN flag for instruction 0. If passes, the
  // call on line 7 (branch type + dest received from decoder) is performed.
  // Note the 'goto 10' at line 8: this skips the second, direct jump in the
  // packet (like 9).
  //
  if (pkt.pkt_has_cof) {
    for (int i = 0; i < pkt.num_insns; i++) {
      const Insn &insn = pkt.insn[i];
      if (!insn.part1 && IsCondJump(insn)) {
        il.AddInstruction(
            il.SetRegister(1, BRANCH_TAKEN_ARRAY + i, il.Const(1, 0)));
      }
    }
  }

  // Process packet instructions, in order.
  auto ctx = absl::make_unique<PacketContext>(il);
  for (int i = 0; i < pkt.num_insns; i++) {
    const Insn &insn = pkt.insn[i];
    RETURN_IF_ERROR(
        FillBnInstructionLowLevelImpl(arch, input.pc, pkt, insn, i, *ctx));
  }

  // Write back all clobbered registers, and clear context.
  ctx->WriteClobberedRegs();
  ctx.reset(nullptr);

  // Branch semantics. See comment above.
  if (pkt.pkt_has_cof) {
    LowLevelILLabel done;
    for (int i = 0; i < pkt.num_insns; i++) {
      const Insn &insn = pkt.insn[i];
      if (insn.part1) {
        continue;
      }
      if (IsJump(insn) || IsCall(insn)) {
        LowLevelILLabel branch_case, next_insn;
        if (IsCondJump(insn)) {
          il.AddInstruction(
              il.If(il.CompareEqual(1, il.Register(1, BRANCH_TAKEN_ARRAY + i),
                                    il.Const(1, 1)),
                    branch_case, next_insn));
          il.MarkLabel(branch_case);
        }
        if (IsIndirect(insn) && IsJump(insn)) {
          if (IsReturn(insn) ||
              (insn.opcode == J2_jumpr && insn.regno[0] == HEX_REG_LR)) {
            il.AddInstruction(il.Return(il.Register(4, HEX_REG_LR)));
          } else {
            il.AddInstruction(il.Jump(il.Register(4, BRANCHR_DEST_ARRAY + i)));
          }
        } else if (IsIndirect(insn) && IsCall(insn)) {
          il.AddInstruction(il.Call(il.Register(4, BRANCHR_DEST_ARRAY + i)));
          // Skip other branches in the packet, and go to the next neighboring
          // packet.
          il.AddInstruction(il.Goto(done));
        } else if (IsJump(insn)) {
          il.AddInstruction(
              il.Jump(il.ConstPointer(4, input.pc + insn.immed[0])));
        } else {
          CHECK(IsCall(insn));
          il.AddInstruction(
              il.Call(il.ConstPointer(4, input.pc + insn.immed[0])));
          // Skip other branches in the packet, and go to the next neighboring
          // packet.
          il.AddInstruction(il.Goto(done));
        }
        il.MarkLabel(next_insn);
      }
    }
    il.MarkLabel(done);
  }

  return absl::OkStatus();
}

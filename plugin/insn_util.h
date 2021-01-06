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

#include <vector>

#include "absl/status/status.h"
#include "binaryninjaapi.h"
#include "plugin/packet_db.h"

absl::Status FillBnInstructionInfo(const PacketDb::InsnInfo &input,
                                   BinaryNinja::InstructionInfo &result);

absl::Status FillBnInstructionTextTokens(
    const PacketDb::InsnInfo &input, size_t &len,
    std::vector<BinaryNinja::InstructionTextToken> &result);

bool IsSubInsn(const Insn &insn);
bool IsJump(const Insn &insn);
bool IsCall(const Insn &insn);
bool IsIndirect(const Insn &insn);
bool IsCondJump(const Insn &insn);
bool IsReturn(const Insn &insn);
bool IsSystem(const Insn &insn);

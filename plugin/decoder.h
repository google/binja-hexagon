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

#include "absl/status/statusor.h"
#include "absl/types/span.h"
#include "third_party/qemu-hexagon/attribs.h"
#include "third_party/qemu-hexagon/iclass.h"
#include "third_party/qemu-hexagon/insn.h"
#include "third_party/qemu-hexagon/opcodes.h"
#include "third_party/qemu-hexagon/reg_fields.h"

class Decoder {
public:
  ~Decoder();
  static Decoder &Get();

  absl::StatusOr<Packet> DecodePacket(absl::Span<const uint32_t> words);

private:
  Decoder();
};

bool operator==(const Insn &lhs, const Insn &rhs);
bool operator!=(const Insn &lhs, const Insn &rhs);
bool operator==(const Packet &lhs, const Packet &rhs);
bool operator!=(const Packet &lhs, const Packet &rhs);

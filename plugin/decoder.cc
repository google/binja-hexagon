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

#include "plugin/decoder.h"

#include "absl/status/status.h"
#include "absl/strings/str_cat.h"
#include "third_party/qemu-hexagon/decode.h"
#include "third_party/qemu-hexagon/opcodes.h"

Decoder::Decoder() {
  // Initialize decoding tables.
  decode_init();
  opcode_init();
}
Decoder::~Decoder() {}

Decoder &Decoder::Get() {
  // Return singleton object.
  static Decoder *global_decoder = new Decoder();
  return *global_decoder;
}

absl::StatusOr<Packet> Decoder::DecodePacket(absl::Span<const uint32_t> words) {
  Packet pkt;
  int res = decode_packet_safe(words.size(), words.data(), &pkt, true);
  if (res < 0) {
    return absl::InternalError(absl::StrCat("Failed to decode, res = ", res));
  }
  if (res == 0) {
    return absl::FailedPreconditionError("Insufficient words in packet");
  }
  return pkt;
}

bool operator==(const Insn &lhs, const Insn &rhs) {
  bool ok = (memcmp(lhs.regno, rhs.regno, sizeof(lhs.regno)) == 0);
  ok &= (lhs.opcode == rhs.opcode && lhs.iclass == rhs.iclass &&
         lhs.slot == rhs.slot && lhs.part1 == rhs.part1 &&
         lhs.extension_valid == rhs.extension_valid &&
         lhs.which_extended == rhs.which_extended &&
         lhs.is_endloop == rhs.is_endloop &&
         lhs.new_value_producer_slot == rhs.new_value_producer_slot &&
         lhs.hvx_resource == rhs.hvx_resource);
  ok &= (memcmp(lhs.immed, rhs.immed, sizeof(lhs.immed)) == 0);
  return ok;
}

bool operator!=(const Insn &lhs, const Insn &rhs) { return !(lhs == rhs); }

bool operator==(const Packet &lhs, const Packet &rhs) {
  bool ok = (lhs.num_insns == rhs.num_insns &&
             lhs.encod_pkt_size_in_bytes == rhs.encod_pkt_size_in_bytes &&
             lhs.pkt_has_cof == rhs.pkt_has_cof &&
             lhs.pkt_has_endloop == rhs.pkt_has_endloop &&
             lhs.pkt_has_dczeroa == rhs.pkt_has_dczeroa &&
             lhs.pkt_has_store_s0 == rhs.pkt_has_store_s0 &&
             lhs.pkt_has_store_s1 == rhs.pkt_has_store_s1 &&
             lhs.pkt_has_hvx == rhs.pkt_has_hvx &&
             lhs.pkt_has_extension == rhs.pkt_has_extension);
  if (ok) {
    for (int i = 0; i < lhs.num_insns; i++) {
      ok &= (lhs.insn[i] == rhs.insn[i]);
    }
  }
  return ok;
}

bool operator!=(const Packet &lhs, const Packet &rhs) { return !(lhs == rhs); }

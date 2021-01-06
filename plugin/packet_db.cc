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

#include "plugin/packet_db.h"

#include "absl/types/span.h"
#include "glog/logging.h"
#include "plugin/status_macros.h"
#include "third_party/abseil-cpp/absl/status/status.h"

bool operator==(const PacketDb::AddressInfo &lhs,
                const PacketDb::AddressInfo &rhs) {
  return (lhs.start_addr == rhs.start_addr && lhs.pkt == rhs.pkt);
}

bool operator!=(const PacketDb::AddressInfo &lhs,
                const PacketDb::AddressInfo &rhs) {
  return !(lhs == rhs);
}

absl::Status PacketDb::AddBytes(absl::Span<const uint8_t> data, uint64_t addr) {
  if (data.size() < 4 || data.size() % 4 != 0) {
    return absl::FailedPreconditionError("Insufficient bytes in data");
  }
  auto words = absl::MakeConstSpan(
      reinterpret_cast<const uint32_t *>(data.data()), data.size() / 4);
  int packets_added = 0;
  while (words.size() > 0) {
    auto result = Decoder::Get().DecodePacket(words);
    if (!result.ok()) {
      break;
    }
    auto pkt = result.value();
    absl::MutexLock lock(&mu_);
    map_.SetInterval(addr, addr + pkt.encod_pkt_size_in_bytes,
                     AddressInfo{addr, pkt});
    addr += pkt.encod_pkt_size_in_bytes;
    words = words.subspan(pkt.encod_pkt_size_in_bytes / 4);
    packets_added++;
  }
  if (packets_added == 0) {
    return absl::FailedPreconditionError("Insufficient bytes in data");
  }
  return absl::OkStatus();
}

absl::StatusOr<PacketDb::InsnInfo> PacketDb::Lookup(uint64_t addr) {
  absl::MutexLock lock(&mu_);
  const auto &addr_info = map_.find(addr).value();
  if (addr_info.pkt.encod_pkt_size_in_bytes == 0) {
    return absl::NotFoundError("Packet not found in interval map");
  }
  return FindInstructionInPacket(addr_info, addr);
}

PacketDb::InsnInfo
PacketDb::FindInstructionInPacket(const PacketDb::AddressInfo &addr_info,
                                  uint64_t addr) {
  InsnInfo result = {
      .pc = addr_info.start_addr,
      .pkt = addr_info.pkt,
      .insn_num = 0,
      .insn_addr = addr_info.start_addr,
  };
  for (; result.insn_num < result.pkt.num_insns; result.insn_num++) {
    const Insn &insn = result.pkt.insn[result.insn_num];
    size_t insn_size = (GET_ATTRIB(insn.opcode, A_SUBINSN) ? 2 : 4);
    if (result.insn_addr <= addr && addr < result.insn_addr + insn_size) {
      break;
    }
    result.insn_addr += insn_size;
  }
  return result;
}

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
#include "absl/synchronization/mutex.h"
#include "absl/types/span.h"
#include "plugin/decoder.h"
#include "third_party/chromium/blink/interval_map.h"

// Manages an address -> Packet database.
// Access is thread safe.
class PacketDb {
public:
  struct AddressInfo {
    uint64_t start_addr;
    Packet pkt;
  };

  struct InsnInfo {
    uint64_t pc;
    Packet pkt;
    uint32_t insn_num;
    uint64_t insn_addr;
  };

  PacketDb() = default;
  ~PacketDb() = default;

  // Decodes new input bytes and updates the map.
  // Returns Ok if at least one new packet was added.
  absl::Status AddBytes(absl::Span<const uint8_t> data, uint64_t addr)
      ABSL_EXCLUSIVE_LOCKS_REQUIRED(mu_);

  // Looks up a previously decoded instruction at |addr|.
  absl::StatusOr<InsnInfo> Lookup(uint64_t addr)
      ABSL_EXCLUSIVE_LOCKS_REQUIRED(mu_);

private:
  static InsnInfo FindInstructionInPacket(const AddressInfo &addr_info,
                                          uint64_t addr);

  absl::Mutex mu_;
  media::IntervalMap<uint64_t, AddressInfo> map_ ABSL_GUARDED_BY(mu_);
};

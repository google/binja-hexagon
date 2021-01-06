#pragma once

#include "third_party/qemu-hexagon/iclass.h"
#include "third_party/qemu-hexagon/insn.h"

#ifdef __cplusplus
extern "C" {
#endif

extern void mmvec_ext_decode_checks(Packet *pkt);
extern SlotMask mmvec_ext_decode_find_iclass_slots(int opcode);

#ifdef __cplusplus
}
#endif

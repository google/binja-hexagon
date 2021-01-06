/*
 *  Copyright(c) 2019-2020 Qualcomm Innovation Center, Inc. All Rights Reserved.
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, see <http://www.gnu.org/licenses/>.
 */

#define DECODE_NEW_TABLE(TAG, SIZE, WHATNOT) /* NOTHING */
#define TABLE_LINK(TABLE)                    /* NOTHING */
#define TERMINAL(TAG, ENC)                   /* NOTHING */
#define SUBINSNS(TAG, CLASSA, CLASSB, ENC)   /* NOTHING */
#define EXTSPACE(TAG, ENC)                   /* NOTHING */
#define INVALID()                            /* NOTHING */
#define DECODE_END_TABLE(...)                /* NOTHING */
#define DECODE_MATCH_INFO(...)               /* NOTHING */
#define DECODE_LEGACY_MATCH_INFO(...)        /* NOTHING */

#define DECODE_REG(REGNO, WIDTH, STARTBIT)                                     \
  insn->regno[REGNO] = ((encoding >> STARTBIT) & ((1 << WIDTH) - 1));

#define DECODE_IMPL_REG(REGNO, VAL) insn->regno[REGNO] = VAL;

#define DECODE_IMM(IMMNO, WIDTH, STARTBIT, VALSTART)                           \
  insn->immed[IMMNO] |= (((encoding >> STARTBIT) & ((1 << WIDTH) - 1)))        \
                        << (VALSTART);

#define DECODE_IMM_SXT(IMMNO, WIDTH)                                           \
  insn->immed[IMMNO] =                                                         \
      ((((int32_t)insn->immed[IMMNO]) << (32 - WIDTH)) >> (32 - WIDTH));

#define DECODE_IMM_NEG(IMMNO, WIDTH) insn->immed[IMMNO] = -insn->immed[IMMNO];

#define DECODE_IMM_SHIFT(IMMNO, SHAMT)                                         \
  if ((!insn->extension_valid) || (insn->which_extended != IMMNO)) {           \
    insn->immed[IMMNO] <<= SHAMT;                                              \
  }

#define DECODE_OPINFO(TAG, BEH)                                                \
  case TAG: {                                                                  \
    BEH                                                                        \
  } break;

/*
 * Fill in the operands of the instruction
 * dectree_generated.h had a DECODE_OPINFO entry for each opcode
 * For example,
 *     DECODE_OPINFO(A2_addi,
 *          DECODE_REG(0,5,0)
 *          DECODE_REG(1,5,16)
 *          DECODE_IMM(0,7,21,9)
 *          DECODE_IMM(0,9,5,0)
 *          DECODE_IMM_SXT(0,16)
 * with the macros defined above, we'll fill in a switch statement
 * where each case is an opcode tag.
 */
static void decode_op(Insn *insn, Opcode tag, uint32_t encoding) {
  insn->immed[0] = 0;
  insn->immed[1] = 0;
  insn->opcode = tag;
  if (insn->extension_valid) {
    insn->which_extended = opcode_which_immediate_is_extended(tag);
  }

  switch (tag) {
#include "dectree_generated.h"
  default:
    break;
  }

  insn->iclass = iclass_bits(encoding);
}

#undef DECODE_REG
#undef DECODE_IMPL_REG
#undef DECODE_IMM
#undef DECODE_IMM_SHIFT
#undef DECODE_OPINFO
#undef DECODE_MATCH_INFO
#undef DECODE_LEGACY_MATCH_INFO
#undef DECODE_END_TABLE
#undef INVALID
#undef TERMINAL
#undef SUBINSNS
#undef EXTSPACE
#undef TABLE_LINK
#undef DECODE_NEW_TABLE
#undef DECODE_SEPARATOR_BITS

static unsigned int decode_subinsn_tablewalk(Insn *insn,
                                             const DectreeTable *table,
                                             uint32_t encoding) {
  unsigned int i;
  Opcode opc;
  if (table->lookup_function) {
    i = table->lookup_function(table->startbit, table->width, encoding);
  } else {
    i = extract32(encoding, table->startbit, table->width);
  }
  if (table->table[i].type == DECTREE_TABLE_LINK) {
    return decode_subinsn_tablewalk(insn, table->table[i].table_link, encoding);
  } else if (table->table[i].type == DECTREE_TERMINAL) {
    opc = table->table[i].opcode;
    if ((encoding & decode_itable[opc].mask) != decode_itable[opc].match) {
      return 0;
    }
    decode_op(insn, opc, encoding);
    return 1;
  } else {
    return 0;
  }
}

static unsigned int get_insn_a(uint32_t encoding) {
  return extract32(encoding, 0, 13);
}

static unsigned int get_insn_b(uint32_t encoding) {
  return extract32(encoding, 16, 13);
}

static unsigned int decode_insns_tablewalk(Insn *insn,
                                           const DectreeTable *table,
                                           uint32_t encoding) {
  unsigned int i;
  unsigned int a, b;
  Opcode opc;
  if (table->lookup_function) {
    i = table->lookup_function(table->startbit, table->width, encoding);
  } else {
    i = extract32(encoding, table->startbit, table->width);
  }
  if (table->table[i].type == DECTREE_TABLE_LINK) {
    return decode_insns_tablewalk(insn, table->table[i].table_link, encoding);
  } else if (table->table[i].type == DECTREE_SUBINSNS) {
    a = get_insn_a(encoding);
    b = get_insn_b(encoding);
    b = decode_subinsn_tablewalk(insn, table->table[i].table_link_b, b);
    a = decode_subinsn_tablewalk(insn + 1, table->table[i].table_link, a);
    if ((a == 0) || (b == 0)) {
      return 0;
    }
    return 2;
  } else if (table->table[i].type == DECTREE_TERMINAL) {
    opc = table->table[i].opcode;
    if ((encoding & decode_itable[opc].mask) != decode_itable[opc].match) {
      if ((encoding & decode_legacy_itable[opc].mask) !=
          decode_legacy_itable[opc].match) {
        return 0;
      }
    }
    decode_op(insn, opc, encoding);
    return 1;
  } else if (table->table[i].type == DECTREE_EXTSPACE) {
    /*
     * For now, HVX will be the only coproc
     */
    return decode_insns_tablewalk(insn, ext_trees[EXT_IDX_mmvec], encoding);
  } else {
    return 0;
  }
}

static unsigned int decode_insns(Insn *insn, uint32_t encoding) {
  const DectreeTable *table;
  if (parse_bits(encoding) != 0) {
    /* Start with PP table - 32 bit instructions */
    table = &dectree_table_DECODE_ROOT_32;
  } else {
    /* start with EE table - duplex instructions */
    table = &dectree_table_DECODE_ROOT_EE;
  }
  return decode_insns_tablewalk(insn, table, encoding);
}

static void decode_add_endloop_insn(Insn *insn, int loopnum) {
  if (loopnum == 10) {
    insn->opcode = J2_endloop01;
  } else if (loopnum == 1) {
    insn->opcode = J2_endloop1;
  } else if (loopnum == 0) {
    insn->opcode = J2_endloop0;
  } else {
    ASSERT_AND_ABORT(0);
  }
}

static inline int decode_parsebits_is_loopend(uint32_t encoding32) {
  uint32_t bits = parse_bits(encoding32);
  return bits == 0x2;
}

static void decode_set_slot_number(Packet *pkt) {
  int slot;
  int i;
  int hit_mem_insn = 0;
  int hit_duplex = 0;

  /*
   * The slots are encoded in reverse order
   * For each instruction, count down until you find a suitable slot
   */
  for (i = 0, slot = 3; i < pkt->num_insns; i++) {
    SlotMask valid_slots = get_valid_slots(pkt, i);

    while (!(valid_slots & (1 << slot))) {
      slot--;
    }
    pkt->insn[i].slot = slot;
    if (slot) {
      /* I've assigned the slot, now decrement it for the next insn */
      slot--;
    }
  }

  /* Fix the exceptions - mem insns to slot 0,1 */
  for (i = pkt->num_insns - 1; i >= 0; i--) {
    /* First memory instruction always goes to slot 0 */
    if ((GET_ATTRIB(pkt->insn[i].opcode, A_MEMLIKE) ||
         GET_ATTRIB(pkt->insn[i].opcode, A_MEMLIKE_PACKET_RULES)) &&
        !hit_mem_insn) {
      hit_mem_insn = 1;
      pkt->insn[i].slot = 0;
      continue;
    }

    /* Next memory instruction always goes to slot 1 */
    if ((GET_ATTRIB(pkt->insn[i].opcode, A_MEMLIKE) ||
         GET_ATTRIB(pkt->insn[i].opcode, A_MEMLIKE_PACKET_RULES)) &&
        hit_mem_insn) {
      pkt->insn[i].slot = 1;
    }
  }

  /* Fix the exceptions - duplex always slot 0,1 */
  for (i = pkt->num_insns - 1; i >= 0; i--) {
    /* First subinsn always goes to slot 0 */
    if (GET_ATTRIB(pkt->insn[i].opcode, A_SUBINSN) && !hit_duplex) {
      hit_duplex = 1;
      pkt->insn[i].slot = 0;
      continue;
    }

    /* Next subinsn always goes to slot 1 */
    if (GET_ATTRIB(pkt->insn[i].opcode, A_SUBINSN) && hit_duplex) {
      pkt->insn[i].slot = 1;
    }
  }

  /* Fix the exceptions - slot 1 is never empty, always aligns to slot 0 */
  int slot0_found = 0;
  int slot1_found = 0;
  int slot1_iidx = 0;
  for (i = pkt->num_insns - 1; i >= 0; i--) {
    /* Is slot0 used? */
    if (pkt->insn[i].slot == 0) {
      int is_endloop = (pkt->insn[i].opcode == J2_endloop01);
      is_endloop |= (pkt->insn[i].opcode == J2_endloop0);
      is_endloop |= (pkt->insn[i].opcode == J2_endloop1);

      /*
       * Make sure it's not endloop since, we're overloading
       * slot0 for endloop
       */
      if (!is_endloop) {
        slot0_found = 1;
      }
    }
    /* Is slot1 used? */
    if (pkt->insn[i].slot == 1) {
      slot1_found = 1;
      slot1_iidx = i;
    }
  }
  /* Is slot0 empty and slot1 used? */
  if ((slot0_found == 0) && (slot1_found == 1)) {
    /* Then push it to slot0 */
    pkt->insn[slot1_iidx].slot = 0;
  }
}

/*
 * decode_packet
 * Decodes packet with given words
 * Returns 0 on insufficient words,
 * or number of words used on success
 */

int decode_packet(int max_words, const uint32_t *words, Packet *pkt,
                  bool disas_only) {
  int num_insns = 0;
  int words_read = 0;
  int end_of_packet = 0;
  int new_insns = 0;
  int i;
  uint32_t encoding32;

  /* Initialize */
  memset(pkt, 0, sizeof(*pkt));
  /* Try to build packet */
  while (!end_of_packet && (words_read < max_words)) {
    encoding32 = words[words_read];
    end_of_packet = is_packet_end(encoding32);
    new_insns = decode_insns(&pkt->insn[num_insns], encoding32);
    ASSERT_AND_ABORT(new_insns > 0);
    /*
     * If we saw an extender, mark next word extended so immediate
     * decode works
     */
    if (pkt->insn[num_insns].opcode == A4_ext) {
      pkt->insn[num_insns + 1].extension_valid = 1;
    }
    num_insns += new_insns;
    words_read++;
  }

  pkt->num_insns = num_insns;
  if (!end_of_packet) {
    /* Ran out of words! */
    return 0;
  }
  pkt->encod_pkt_size_in_bytes = words_read * 4;
  pkt->pkt_has_extension = 0;
  for (i = 0; i < num_insns; i++) {
    pkt->pkt_has_extension |= GET_ATTRIB(pkt->insn[i].opcode, A_EXTENSION);
  }

  /*
   * Check for :endloop in the parse bits
   * Section 10.6 of the Programmer's Reference describes the encoding
   *     The end of hardware loop 0 can be encoded with 2 words
   *     The end of hardware loop 1 needs 3 words
   */
  if ((words_read == 2) && (decode_parsebits_is_loopend(words[0]))) {
    decode_add_endloop_insn(&pkt->insn[pkt->num_insns++], 0);
  }
  if (words_read >= 3) {
    uint32_t has_loop0, has_loop1;
    has_loop0 = decode_parsebits_is_loopend(words[0]);
    has_loop1 = decode_parsebits_is_loopend(words[1]);
    if (has_loop0 && has_loop1) {
      decode_add_endloop_insn(&pkt->insn[pkt->num_insns++], 10);
    } else if (has_loop1) {
      decode_add_endloop_insn(&pkt->insn[pkt->num_insns++], 1);
    } else if (has_loop0) {
      decode_add_endloop_insn(&pkt->insn[pkt->num_insns++], 0);
    }
  }

  decode_apply_extenders(pkt);
  if (!disas_only) {
    decode_remove_extenders(pkt);
  }
  decode_set_slot_number(pkt);
  decode_fill_newvalue_regno(pkt);

  if (pkt->pkt_has_extension) {
    mmvec_ext_decode_checks(pkt);
  }

  if (!disas_only) {
    decode_shuffle_for_execution(pkt);
    decode_split_cmpjump(pkt);
  }

  decode_set_insn_attr_fields(pkt);

  return words_read;
}

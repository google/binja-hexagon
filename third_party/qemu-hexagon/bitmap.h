#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#define DIV_ROUND_UP(n, d) (((n) + (d)-1) / (d))

#define BITS_PER_BYTE 8
#define BITS_PER_LONG (sizeof(unsigned long) * BITS_PER_BYTE)

#define BIT(nr) (1UL << (nr))
#define BIT_ULL(nr) (1ULL << (nr))
#define BIT_MASK(nr) (1UL << ((nr) % BITS_PER_LONG))
#define BIT_WORD(nr) ((nr) / BITS_PER_LONG)

#define BITS_TO_LONGS(nr) DIV_ROUND_UP(nr, BITS_PER_BYTE * sizeof(long))

#define DECLARE_BITMAP(name, bits) unsigned long name[BITS_TO_LONGS(bits)]

/**
 * set_bit - Set a bit in memory
 * @nr: the bit to set
 * @addr: the address to start counting from
 */
static inline void set_bit(long nr, unsigned long *addr) {
  unsigned long mask = BIT_MASK(nr);
  unsigned long *p = addr + BIT_WORD(nr);

  *p |= mask;
}

/**
 *  test_bit - Determine whether a bit is set
 *  @nr: bit number to test
 *  @addr: Address to start counting from
 */
static inline int test_bit(long nr, const unsigned long *addr) {
  return 1UL & (addr[BIT_WORD(nr)] >> (nr & (BITS_PER_LONG - 1)));
}

#ifdef __cplusplus
}
#endif

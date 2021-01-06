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

#include <stdint.h>
#include <stdio.h>

#define MIN(a, b) (((a) < (b)) ? (a) : (b))
#define MAX(a, b) (((a) > (b)) ? (a) : (b))

static int g_res = 0;

__attribute__((noinline)) void test_add_int(int a, int b) { g_res = a + b; }

__attribute__((noinline)) void test_cmp_signed_int(int a, int b) {
  g_res = (a >= b ? 0x1234 : 0x8765);
}

__attribute__((noinline)) void test_cmp_unsigned_int(unsigned int a,
                                                     unsigned int b) {
  g_res = (a >= b ? 0x1234 : 0x8765);
}

__attribute__((noinline)) void test_mul_int(int a, int b) { g_res = a * b; }

__attribute__((noinline)) void test_func_call(int a, int b) {
  typedef int (*FUNC)(int);
  FUNC p = (FUNC)a;
  g_res = p(b);
}

__attribute__((noinline)) void test_struct(int a, int b) {
  typedef struct {
    int x[2];
    int y;
  } STRUCT;
  STRUCT *p = (STRUCT *)a;
  g_res = p->y + b;
}

__attribute__((noinline)) __attribute__((optnone)) int test_fact(int a) {
  if (a == 0)
    return 1;
  return test_fact(a - 1) * a;
}

__attribute__((noinline)) void test_and_int(int a, int b) { g_res = a & b; }
__attribute__((noinline)) void test_or_int(int a, int b) { g_res = a | b; }
__attribute__((noinline)) void test_xor_int(int a, int b) { g_res = a ^ b; }
__attribute__((noinline)) void test_not_int(int a) { g_res = ~a; }
__attribute__((noinline)) __attribute__((optnone)) void test_collatz(int a) {
  while (a != 1) {
    if ((a & 1) == 0) {
      a = a >> 1;
    } else {
      a = 3 * a + 1;
    }
  }
}

__attribute__((noinline)) void test_max_signed_int(int a, int b) {
  g_res = MAX(a, b);
}

__attribute__((noinline)) void test_max_unsigned_int(unsigned int a,
                                                     unsigned int b) {
  g_res = MAX(a, b);
}

__attribute__((noinline)) void test_min_signed_int(int a, int b) {
  g_res = MIN(a, b);
}

__attribute__((noinline)) void test_min_unsigned_int(unsigned int a,
                                                     unsigned int b) {
  g_res = MIN(a, b);
}

int main(int argc, char *argv[]) {
  test_add_int(argc, argc + 1);
  test_cmp_signed_int(argc, argc + 1);
  test_cmp_unsigned_int(argc, argc + 1);
  test_mul_int(argc, argc + 1);
  test_func_call(argc, argc + 1);
  test_struct(argc, argc + 1);
  test_fact(argc);
  test_and_int(argc, argc + 1);
  test_or_int(argc, argc + 1);
  test_xor_int(argc, argc + 1);
  test_not_int(argc);
  test_collatz(argc);
  test_max_signed_int(argc, argc + 1);
  test_max_unsigned_int(argc, argc + 1);
  test_min_signed_int(argc, argc + 1);
  test_min_unsigned_int(argc, argc + 1);
  return g_res;
}

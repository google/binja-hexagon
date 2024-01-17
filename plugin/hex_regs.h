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

enum {
  //
  // General registers.
  //
  HEX_REG_R00 = 0,
  HEX_REG_R01 = 1,
  HEX_REG_R02 = 2,
  HEX_REG_R03 = 3,
  HEX_REG_R04 = 4,
  HEX_REG_R05 = 5,
  HEX_REG_R06 = 6,
  HEX_REG_R07 = 7,
  HEX_REG_R08 = 8,
  HEX_REG_R09 = 9,
  HEX_REG_R10 = 10,
  HEX_REG_R11 = 11,
  HEX_REG_R12 = 12,
  HEX_REG_R13 = 13,
  HEX_REG_R14 = 14,
  HEX_REG_R15 = 15,
  HEX_REG_R16 = 16,
  HEX_REG_R17 = 17,
  HEX_REG_R18 = 18,
  HEX_REG_R19 = 19,
  HEX_REG_R20 = 20,
  HEX_REG_R21 = 21,
  HEX_REG_R22 = 22,
  HEX_REG_R23 = 23,
  HEX_REG_R24 = 24,
  HEX_REG_R25 = 25,
  HEX_REG_R26 = 26,
  HEX_REG_R27 = 27,
  HEX_REG_R28 = 28,
  HEX_REG_R29 = 29,
  HEX_REG_R30 = 30,
  HEX_REG_R31 = 31,

  //
  // General register aliases.
  //
  // Stack pointer.
  HEX_REG_SP = HEX_REG_R29,
  // Frame pointer.
  HEX_REG_FP = HEX_REG_R30,
  // Link register.
  HEX_REG_LR = HEX_REG_R31,

  //
  // Control registers.
  //
  HEX_REG_C00 = 32,
  HEX_REG_C01 = 33,
  HEX_REG_C02 = 34,
  HEX_REG_C03 = 35,
  HEX_REG_C04 = 36,
  HEX_REG_C05 = 37,
  HEX_REG_C06 = 38,
  HEX_REG_C07 = 39,
  HEX_REG_C08 = 40,
  HEX_REG_C09 = 41,
  HEX_REG_C10 = 42,
  HEX_REG_C11 = 43,
  HEX_REG_C12 = 44,
  HEX_REG_C13 = 45,
  HEX_REG_C14 = 46,
  HEX_REG_C15 = 47,
  HEX_REG_C16 = 48,
  HEX_REG_C17 = 49,
  HEX_REG_C18 = 50,
  HEX_REG_C19 = 51,
  HEX_REG_C20 = 52,
  HEX_REG_C21 = 53,
  HEX_REG_C22 = 54,
  HEX_REG_C23 = 55,
  HEX_REG_C24 = 56,
  HEX_REG_C25 = 57,
  HEX_REG_C26 = 58,
  HEX_REG_C27 = 59,
  HEX_REG_C28 = 60,
  HEX_REG_C29 = 61,
  HEX_REG_C30 = 62,
  HEX_REG_C31 = 63,

  //
  // Aliased control registers
  //
  // Loop registers.
  HEX_REG_SA0 = HEX_REG_C00,
  HEX_REG_LC0 = HEX_REG_C01,
  HEX_REG_SA1 = HEX_REG_C02,
  HEX_REG_LC1 = HEX_REG_C03,
  // Predicate registers 3:0
  HEX_REG_P3_0 = HEX_REG_C04,
  // Modifier registers.
  HEX_REG_M0 = HEX_REG_C06,
  HEX_REG_M1 = HEX_REG_C07,
  // User status register.
  HEX_REG_USR = HEX_REG_C08,
  // Program counter.
  HEX_REG_PC = HEX_REG_C09,
  // User general pointer.
  HEX_REG_UGP = HEX_REG_C10,
  // Global pointer.
  HEX_REG_GP = HEX_REG_C11,
  // Circular start registers.
  HEX_REG_CS0 = HEX_REG_C12,
  HEX_REG_CS1 = HEX_REG_C13,

  //
  // Sub registers.
  //
  // Predicate registers modeled as sub registers of HEX_REG_P3_0.
  HEX_REG_P0 = 90,
  HEX_REG_P1 = 91,
  HEX_REG_P2 = 92,
  HEX_REG_P3 = 93,
  // HW loop configuration modeled as sub register of HEX_REG_USR.
  HEX_REG_USR_LPCFG = 94,

  NUM_HEX_REGS = 100,
};

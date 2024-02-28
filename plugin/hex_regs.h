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

//
// System registers
//
enum {
    HEX_SREG_SGP0 = 0,
    HEX_SREG_SGP1 = 1,
    HEX_SREG_STID = 2,
    HEX_SREG_ELR = 3,
    HEX_SREG_BADVA0 = 4,
    HEX_SREG_BADVA1 = 5,
    HEX_SREG_SSR = 6,
    HEX_SREG_CCR = 7,
    HEX_SREG_HTID = 8,
    HEX_SREG_BADVA = 9,
    HEX_SREG_IMASK = 10,
    HEX_SREG_GEVB  = 11,
    HEX_SREG_EVB = 16,
    HEX_SREG_MODECTL = 17,
    HEX_SREG_SYSCFG = 18,
    HEX_SREG_IPENDAD = 20,
    HEX_SREG_VID = 21,
    HEX_SREG_VID1 = 22,
    HEX_SREG_BESTWAIT = 23,
    HEX_SREG_IEL = 24,
    HEX_SREG_SCHEDCFG = 25,
    HEX_SREG_IAHL = 26,
    HEX_SREG_CFGBASE = 27,
    HEX_SREG_DIAG = 28,
    HEX_SREG_REV = 29,
    HEX_SREG_PCYCLELO = 30,
    HEX_SREG_PCYCLEHI = 31,
    HEX_SREG_ISDBST = 32,
    HEX_SREG_ISDBCFG0 = 33,
    HEX_SREG_ISDBCFG1 = 34,
    HEX_SREG_LIVELOCK = 35,
    HEX_SREG_BRKPTPC0 = 36,
    HEX_SREG_BRKPTCFG0 = 37,
    HEX_SREG_BRKPTPC1 = 38,
    HEX_SREG_BRKPTCFG1 = 39,
    HEX_SREG_ISDBMBXIN = 40,
    HEX_SREG_ISDBMBXOUT = 41,
    HEX_SREG_ISDBEN = 42,
    HEX_SREG_ISDBGPR = 43,
    HEX_SREG_PMUCNT4 = 44,
    HEX_SREG_PMUCNT5 = 45,
    HEX_SREG_PMUCNT6 = 46,
    HEX_SREG_PMUCNT7 = 47,
    HEX_SREG_PMUCNT0 = 48,
    HEX_SREG_PMUCNT1 = 49,
    HEX_SREG_PMUCNT2 = 50,
    HEX_SREG_PMUCNT3 = 51,
    HEX_SREG_PMUEVTCFG = 52,
    HEX_SREG_PMUSTID0 = 53,
    HEX_SREG_PMUEVTCFG1 = 54,
    HEX_SREG_PMUSTID1 = 55,
    HEX_SREG_TIMERLO = 56,
    HEX_SREG_TIMERHI = 57,
    HEX_SREG_PMUCFG = 58,
    HEX_SREG_S59 = 59,
    HEX_SREG_S60 = 60,
    HEX_SREG_S61 = 61,
    HEX_SREG_S62 = 62,
    HEX_SREG_S63 = 63,
    HEX_SREG_COMMIT1T = 64,
    HEX_SREG_COMMIT2T = 65,
    HEX_SREG_COMMIT3T = 66,
    HEX_SREG_COMMIT4T = 67,
    HEX_SREG_COMMIT5T = 68,
    HEX_SREG_COMMIT6T = 69,
    HEX_SREG_PCYCLE1T = 70,
    HEX_SREG_PCYCLE2T = 71,
    HEX_SREG_PCYCLE3T = 72,
    HEX_SREG_PCYCLE4T = 73,
    HEX_SREG_PCYCLE5T = 74,
    HEX_SREG_PCYCLE6T = 75,
    HEX_SREG_STFINST = 76,
    HEX_SREG_ISDBCMD = 77,
    HEX_SREG_ISDBVER = 78,
    HEX_SREG_BRKPTINFO = 79,
    HEX_SREG_RGDR3 = 80,
    HEX_SREG_COMMIT7T = 81,
    HEX_SREG_COMMIT8T = 82,
    HEX_SREG_PCYCLE7T = 83,
    HEX_SREG_PCYCLE8T = 84,
    HEX_SREG_S85 = 85,

    // Alias system registers

    HEX_SREG_GLB_START = HEX_SREG_EVB
};

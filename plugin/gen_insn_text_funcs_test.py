#!/usr/bin/env python3
#
# Copyright (C) 2020 Google LLC
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import unittest
import io
from hex_common import *
from gen_insn_text_funcs import *
from lark import Tree, Token

SEMANTICS = """SEMANTICS( \
    "J2_jump", \
    "jump #r22:2", \
    \"\"\"{fIMMEXT(riV); fPCALIGN(riV); fBRANCH(fREAD_PC()+riV,COF_TYPE_JUMP);}\"\"\" \
)
ATTRIBUTES( \
    "J2_jump", \
    "ATTRIBS(A_JUMP)" \
)
SEMANTICS( \
    "J2_jumpr", \
    "jumpr Rs32", \
    \"\"\"{fJUMPR(RsN,RsV,COF_TYPE_JUMPR);}\"\"\" \
)
ATTRIBUTES( \
    "J2_jumpr", \
    "ATTRIBS(A_JUMP,A_INDIRECT)" \
)
SEMANTICS( \
    "A2_add", \
    "Rd32=add(Rs32,Rt32)", \
    \"\"\"{ RdV=RsV+RtV;}\"\"\" \
)
ATTRIBUTES( \
    "A2_add", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "A2_sub", \
    "Rd32=sub(Rt32,Rs32)", \
    \"\"\"{ RdV=RtV-RsV;}\"\"\" \
)
ATTRIBUTES( \
    "A2_sub", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "A2_addh_l16_ll", \
    "Rd32=add""(Rt.L32,Rs.L32)""\", \
    \"\"\"{RdV=fSXTN(16,32,(fGETHALF(0,RtV)+fGETHALF(0,RsV)));}\"\"\" \
)
ATTRIBUTES( \
    "A2_addh_l16_ll", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "A2_addp", \
    "Rdd32=add(Rss32,Rtt32)", \
    \"\"\"{ RddV=RssV+RttV;}\"\"\" \
)
ATTRIBUTES( \
    "A2_addp", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "A2_addpsat", \
    "Rdd32=add(Rss32,Rtt32):sat", \
    \"\"\"{ fADDSAT64(RddV,RssV,RttV);}\"\"\" \
)
ATTRIBUTES( \
    "A2_addpsat", \
    "ATTRIBS(A_ARCHV3)" \
)
SEMANTICS( \
    "A4_ext", \
    "immext(#u26:6)", \
    \"\"\"{ fHIDE(); }\"\"\" \
)
ATTRIBUTES( \
    "A4_ext", \
    "ATTRIBS(A_IT_EXTENDER)" \
)
SEMANTICS( \
    "A4_combineii", \
    "Rdd32=combine(#s8,#U6)", \
    \"\"\"{ fIMMEXT(UiV); fSETWORD(0,RddV,UiV); fSETWORD(1,RddV,siV); }\"\"\" \
)
ATTRIBUTES( \
    "A4_combineii", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "SS2_stored_sp", \
    "memd(r29+#s6:3)=Rtt8", \
    \"\"\"{fEA_RI(fREAD_SP(),siV); fSTORE(1,8,EA,RttV);}\"\"\" \
)
ATTRIBUTES( \
    "SS2_stored_sp", \
    "ATTRIBS(A_STORE,A_SUBINSN)" \
)
SEMANTICS( \
    "J4_cmpeqi_tp0_jump_nt", \
    "p0=""cmp.eq(Rs16,#U5)""; if (p0.new) jump:nt #r9:2", \
    \"\"\"{fPART1(fWRITE_P0(f8BITSOF((RsV==UiV)))) fBRANCH_SPECULATE_STALL(fLSBNEW0,,SPECULATE_NOT_TAKEN,13,0) if (fLSBNEW0) {fIMMEXT(riV); fPCALIGN(riV); fBRANCH(fREAD_PC()+riV,COF_TYPE_JUMP);}}\"\"\" \
)
ATTRIBUTES( \
    "J4_cmpeqi_tp0_jump_nt", \
    "ATTRIBS(A_JUMP,A_NEWCMPJUMP,A_BN_COND_J)" \
)
SEMANTICS( \
    "J2_jumprnz", \
    "if (Rs32==#0) jump:nt #r13:2", \
    \"\"\"{fBRANCH_SPECULATE_STALL((RsV==0), , SPECULATE_NOT_TAKEN,12,0) if (RsV == 0) {fBRANCH(fREAD_PC()+riV,COF_TYPE_JUMP);}}\"\"\" \
)
ATTRIBUTES( \
    "J2_jumprnz", \
    "ATTRIBS(A_JUMP,A_ARCHV3,A_BN_COND_J)" \
)
SEMANTICS( \
    "L4_loadrub_ur", \
    "Rd32=memub""(Rt32<<#u2+#U6)", \
    \"\"\"{fMUST_IMMEXT(UiV); fEA_IRs(UiV,RtV,uiV); fLOAD(1,1,u,EA,RdV);}\"\"\" \
)
ATTRIBUTES( \
    "L4_loadrub_ur", \
    "ATTRIBS(A_LOAD)" \
)
SEMANTICS( \
    "L2_loadrub_pci", \
    "Rd32=memub""(Rx32++#s4:""0"":circ(Mu2))", \
    \"\"\"{fEA_REG(RxV); fPM_CIRI(RxV,siV,MuV); fLOAD(1,1,u,EA,RdV);}\"\"\" \
)
ATTRIBUTES( \
    "L2_loadrub_pci", \
    "ATTRIBS(A_LOAD)" \
)
SEMANTICS( \
    "L2_loadrub_pcr", \
    "Rd32=memub""(Rx32++I:circ(Mu2))", \
    \"\"\"{fEA_REG(RxV); fPM_CIRR(RxV,fREAD_IREG(MuV)<<0,MuV); fLOAD(1,1,u,EA,RdV);}\"\"\" \
)
ATTRIBUTES( \
    "L2_loadrub_pcr", \
    "ATTRIBS(A_LOAD)" \
)
SEMANTICS( \
    "S2_allocframe", \
    "allocframe(Rx32,#u11:3):raw", \
    \"\"\"{ fEA_RI(RxV,-8); fSTORE(1,8,EA,fFRAME_SCRAMBLE((fCAST8_8u(fREAD_LR()) << 32) | fCAST4_4u(fREAD_FP()))); fWRITE_FP(EA); fFRAMECHECK(EA-uiV,EA); RxV = EA-uiV; }\"\"\" \
)
ATTRIBUTES( \
    "S2_allocframe", \
    "ATTRIBS(A_STORE,A_RESTRICT_SLOT0ONLY)" \
)
SEMANTICS( \
    "L4_return_tnew_pt", \
    "if (Pv4"".new"") Rdd32=dealloc_return(Rs32)"":t"":raw", \
    \"\"\"{ fHIDE(size8u_t tmp;) fBRANCH_SPECULATE_STALL(fLSBNEW(PvN),,SPECULATE_TAKEN,12,0); fEA_REG(RsV); if (fLSBNEW(PvN)) { fLOAD(1,8,u,EA,tmp); RddV = fFRAME_UNSCRAMBLE(tmp); fWRITE_SP(EA+8); fJUMPR(REG_LR,fGETWORD(1,RddV),COF_TYPE_JUMPR); } else { LOAD_CANCEL(EA); } }\"\"\" \
)
ATTRIBUTES( \
    "L4_return_tnew_pt", \
    "ATTRIBS(A_LOAD,A_RESTRICT_SLOT0ONLY,A_JUMP,A_INDIRECT)" \
)
SEMANTICS( \
    "A5_ACS", \
    "Rxx32,Pe4=vacsh(Rss32,Rtt32)", \
    \"\"\"{ fHIDE(int i;) fHIDE(int xv;) fHIDE(int sv;) fHIDE(int tv;) for (i = 0; i < 4; i++) { xv = (int) fGETHALF(i,RxxV); sv = (int) fGETHALF(i,RssV); tv = (int) fGETHALF(i,RttV); xv = xv + tv; sv = sv - tv; fSETBIT(i*2, PeV, (xv > sv)); fSETBIT(i*2+1,PeV, (xv > sv)); fSETHALF(i, RxxV, fSATH(fMAX(xv,sv))); } }\"\"\" \
)
ATTRIBUTES( \
    "A5_ACS", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "F2_sffma_sc", \
    "Rx32+=sfmpy(Rs32,Rt32,Pu4):scale", \
    \"\"\"{ fHIDE(size4s_t tmp;) fCHECKSFNAN3(RxV,RxV,RsV,RtV); tmp=fUNFLOAT(fFMAFX(fFLOAT(RsV),fFLOAT(RtV),fFLOAT(RxV),PuV)); if (!((fFLOAT(RxV) == 0.0) && fISZEROPROD(fFLOAT(RsV),fFLOAT(RtV)))) RxV = tmp; }\"\"\" \
)
ATTRIBUTES( \
    "F2_sffma_sc", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "S2_storerf_io", \
    "memh""(Rs32+#s11:""1"")=""Rt.H32", \
    \"\"\"{fIMMEXT(siV); fEA_RI(RsV,siV); fSTORE(1,2,EA,fGETHALF(1,RtV)); }\"\"\" \
)
ATTRIBUTES( \
    "S2_storerf_io", \
    "ATTRIBS(A_STORE)" \
)
SEMANTICS( \
    "J4_cmpeqn1_tp0_jump_nt", \
    "p0=""cmp.eq(Rs16,#-1)""; if (p0.new) jump:nt #r9:2", \
    \"\"\"{fPART1(fWRITE_P0(f8BITSOF((RsV==-1)))) fBRANCH_SPECULATE_STALL(fLSBNEW0,,SPECULATE_NOT_TAKEN,13,0) if (fLSBNEW0) {fIMMEXT(riV); fPCALIGN(riV); fBRANCH(fREAD_PC()+riV,COF_TYPE_JUMP);}}\"\"\" \
)
ATTRIBUTES( \
    "J4_cmpeqn1_tp0_jump_nt", \
    "ATTRIBS(A_JUMP,A_NEWCMPJUMP,A_BN_COND_J)" \
)
SEMANTICS( \
    "J4_jumpseti", \
    "Rd16=#U6 ; jump #r9:2", \
    \"\"\"{fIMMEXT(riV); fPCALIGN(riV); RdV=UiV; fBRANCH(fREAD_PC()+riV,COF_TYPE_JUMP);}\"\"\" \
)
ATTRIBUTES( \
    "J4_jumpseti", \
    "ATTRIBS(A_JUMP)" \
)
SEMANTICS( \
    "J4_cmpeqi_t_jumpnv_t", \
    "if (""cmp.eq(Ns8.new,#U5)"") jump:t #r9:2", \
    \"\"\"{fBRANCH_SPECULATE_STALL((fNEWREG(NsN)==(UiV)),,SPECULATE_TAKEN,13,0);if ((fNEWREG(NsN)==(UiV))) {fIMMEXT(riV); fPCALIGN(riV); fBRANCH(fREAD_PC()+riV,COF_TYPE_JUMP);}}\"\"\" \
)
ATTRIBUTES( \
    "J4_cmpeqi_t_jumpnv_t", \
    "ATTRIBS(A_JUMP,A_DOTNEWVALUE,A_MEMLIKE_PACKET_RULES,A_BN_COND_J)" \
)
SEMANTICS( \
    "J2_loop0r", \
    "loop0(#r7:2,Rs32)", \
    \"\"\"{ fIMMEXT(riV); fPCALIGN(riV); fWRITE_LOOP_REGS0( fREAD_PC()+riV, RsV); fSET_LPCFG(0); }\"\"\" \
)
ATTRIBUTES( \
    "J2_loop0r", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "J2_loop0i", \
    "loop0(#r7:2,#U10)", \
    \"\"\"{ fIMMEXT(riV); fPCALIGN(riV); fWRITE_LOOP_REGS0( fREAD_PC()+riV, UiV); fSET_LPCFG(0); }\"\"\" \
)
ATTRIBUTES( \
    "J2_loop0i", \
    "ATTRIBS()" \
)
MACROATTRIB( \
    "fWRITE_LOOP_REGS0", \
    \"\"\"{WRITE_RREG(REG_LC0,COUNT); WRITE_RREG(REG_SA0,START);}\"\"\", \
    "(A_IMPLICIT_WRITES_LC0,A_IMPLICIT_WRITES_SA0)" \
)
MACROATTRIB( \
    "fWRITE_LOOP_REGS1", \
    \"\"\"{WRITE_RREG(REG_LC1,COUNT); WRITE_RREG(REG_SA1,START);}\"\"\", \
    "(A_IMPLICIT_WRITES_LC1,A_IMPLICIT_WRITES_SA1)" \
)
"""

ATTRIBS_DEF = """
DEF_ATTRIB(AA_DUMMY, "Dummy Zeroth Attribute", "", "")
DEF_ATTRIB(LOAD, "Loads from memory", "", "")
DEF_ATTRIB(STORE, "Stores to memory", "", "")
DEF_ATTRIB(IMPLICIT_WRITES_SA0, "Writes start addr for loop 0", "", "UREG.SA0")
DEF_ATTRIB(IMPLICIT_WRITES_SA1, "Writes start addr for loop 1", "", "UREG.SA1")
DEF_ATTRIB(ZZ_LASTATTRIB, "Last attribute in the file", "", "")
"""


class TestGenInsnTextFuncs(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    read_semantics_file_obj(io.StringIO(SEMANTICS))
    read_attribs_file_obj(io.StringIO(ATTRIBS_DEF))
    calculate_attribs()
    cls.tagregs = get_tagregs()
    cls.tagimms = get_tagimms()

  def test_cmp_jump_has_address_token_in_jump(self):
    for tag in [
        "J4_cmpeqn1_tp0_jump_nt", "J4_cmpeqi_tp0_jump_nt",
        "J4_cmpeqi_t_jumpnv_t"
    ]:
      tokens = process_insn_tokens(tag, TestGenInsnTextFuncs.tagregs[tag],
                                   TestGenInsnTextFuncs.tagimms[tag])
      instructions = list(
          filter(lambda x: isinstance(x[1], InstructionToken),
                 enumerate(tokens)))
      self.assertEqual(len(instructions), 2)
      self.assertGreater(instructions[0][1].arg1.find("cmp"), 0)
      self.assertGreater(instructions[1][1].arg1.find("jump"), 0)
      jump_idx = instructions[1][0]
      addresses = list(
          filter(lambda x: isinstance(x[1], CodeRelativeAddressToken),
                 enumerate(tokens)))
      self.assertEqual(len(addresses), 1)
      addr_idx = addresses[0][0]
      self.assertGreater(addr_idx, jump_idx)

  def test_setijump_has_address_token_in_jump(self):
    for tag in ["J4_jumpseti"]:
      tokens = process_insn_tokens(tag, TestGenInsnTextFuncs.tagregs[tag],
                                   TestGenInsnTextFuncs.tagimms[tag])
      instructions = list(
          filter(lambda x: isinstance(x[1], InstructionToken),
                 enumerate(tokens)))
      self.assertEqual(len(instructions), 1)
      self.assertGreater(instructions[0][1].arg1.find("jump"), 0)
      jump_idx = instructions[0][0]
      addresses = list(
          filter(lambda x: isinstance(x[1], CodeRelativeAddressToken),
                 enumerate(tokens)))
      self.assertEqual(len(addresses), 1)
      addr_idx = addresses[0][0]
      self.assertGreater(addr_idx, jump_idx)

  def test_loop_has_address_token(self):
    for tag in ["J2_loop0r", "J2_loop0i"]:
      tokens = process_insn_tokens(tag, TestGenInsnTextFuncs.tagregs[tag],
                                   TestGenInsnTextFuncs.tagimms[tag])
      addresses = list(
          filter(lambda x: isinstance(x[1], CodeRelativeAddressToken),
                 enumerate(tokens)))
      self.assertEqual(len(addresses), 1)

  def test_process_tags(self):
    for tag in [
        "J2_jump",
        "J2_jumpr",
        "A2_add",
        "A2_sub",
        "A2_addh_l16_ll",
        "A2_addp",
        "A2_addpsat",
        "A4_ext",
        "A4_combineii",
        "SS2_stored_sp",
        "J4_cmpeqi_tp0_jump_nt",
        "J2_jumprnz",
        "L4_loadrub_ur",
        "L2_loadrub_pci",
        "L2_loadrub_pcr",
        "S2_allocframe",
        "L4_return_tnew_pt",
        "A5_ACS",
        "F2_sffma_sc",
        "S2_storerf_io",
    ]:
      # print(tag, behdict[tag])
      out = gen_insn_text_func(tag, TestGenInsnTextFuncs.tagregs[tag],
                               TestGenInsnTextFuncs.tagimms[tag])
      # print(out)


if __name__ == '__main__':
  unittest.main()

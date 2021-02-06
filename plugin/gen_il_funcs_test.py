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
from gen_il_funcs import *
from lark import Token

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
    "J2_jumpt", \
    "if (Pu4) ""jump"":nt ""#r15:2", \
    \"\"\"{fBRANCH_SPECULATE_STALL(fLSBOLD(PuV),,SPECULATE_NOT_TAKEN,12,0); if (fLSBOLD(PuV)) { fIMMEXT(riV);fPCALIGN(riV); fBRANCH(fREAD_PC()+riV,COF_TYPE_JUMP);; }}\"\"\" \
)
ATTRIBUTES( \
    "J2_jumpt", \
    "ATTRIBS(A_JUMP,A_BN_COND_J)" \
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
    "SA1_tfr", \
    "Rd16=Rs16", \
    \"\"\"{ RdV=RsV;}\"\"\" \
)
ATTRIBUTES( \
    "SA1_tfr", \
    "ATTRIBS(A_SUBINSN)" \
)
SEMANTICS( \
    "SA1_seti", \
    "Rd16=#u6", \
    \"\"\"{ fIMMEXT(uiV); RdV=uiV;}\"\"\" \
)
ATTRIBUTES( \
    "SA1_seti", \
    "ATTRIBS(A_SUBINSN)" \
)
SEMANTICS( \
    "A2_tfrsi", \
    "Rd32=#s16", \
    \"\"\"{ fIMMEXT(siV); RdV=siV;}\"\"\" \
)
ATTRIBUTES( \
    "A2_tfrsi", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "S2_storeri_io", \
    "memw""(Rs32+#s11:""2"")=""Rt32", \
    \"\"\"{fIMMEXT(siV); fEA_RI(RsV,siV); fSTORE(1,4,EA,RtV); }\"\"\" \
)
ATTRIBUTES( \
    "S2_storeri_io", \
    "ATTRIBS(A_STORE)" \
)
SEMANTICS( \
    "S4_storeiri_io", \
    "memw""(Rs32+#u6:""2"")=""#S8", \
    \"\"\"{fEA_RI(RsV,uiV); fIMMEXT(SiV); fSTORE(1,4,EA,SiV); }\"\"\" \
)
ATTRIBUTES( \
    "S4_storeiri_io", \
    "ATTRIBS(A_ARCHV2,A_STORE)" \
)
SEMANTICS( \
    "L2_loadrb_io", \
    "Rd32=memb""(Rs32+#s11:""0"")", \
    \"\"\"{fIMMEXT(siV); fEA_RI(RsV,siV); fLOAD(1,1,s,EA,RdV); }\"\"\" \
)
ATTRIBUTES( \
    "L2_loadrb_io", \
    "ATTRIBS(A_LOAD)" \
)
SEMANTICS( \
    "J2_call", \
    "call #r22:2", \
    \"\"\"{fIMMEXT(riV); fPCALIGN(riV); fCALL(fREAD_PC()+riV); }\"\"\" \
)
ATTRIBUTES( \
    "J2_call", \
    "ATTRIBS(A_CALL)" \
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
    "A2_addp", \
    "Rdd32=add(Rss32,Rtt32)", \
    \"\"\"{ RddV=RssV+RttV;}\"\"\" \
)
ATTRIBUTES( \
    "A2_addp", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "L4_return", \
    "Rdd32=dealloc_return(Rs32):raw", \
    \"\"\"{ fHIDE(size8u_t tmp;) fEA_REG(RsV); fLOAD(1,8,u,EA,tmp); RddV = fFRAME_UNSCRAMBLE(tmp); fWRITE_SP(EA+8); fJUMPR(REG_LR,fGETWORD(1,RddV),COF_TYPE_JUMPR);}\"\"\" \
)
ATTRIBUTES( \
    "L4_return", \
    "ATTRIBS(A_JUMP,A_INDIRECT,A_LOAD,A_RESTRICT_SLOT0ONLY,A_BN_RETURN)" \
)
SEMANTICS( \
    "L2_deallocframe", \
    "Rdd32=deallocframe(Rs32):raw", \
    \"\"\"{ fHIDE(size8u_t tmp;) fEA_REG(RsV); fLOAD(1,8,u,EA,tmp); RddV = fFRAME_UNSCRAMBLE(tmp); fWRITE_SP(EA+8); }\"\"\" \
)
ATTRIBUTES( \
    "L2_deallocframe", \
    "ATTRIBS(A_LOAD)" \
)
SEMANTICS( \
    "L2_loadri_io", \
    "Rd32=memw""(Rs32+#s11:""2"")", \
    \"\"\"{fIMMEXT(siV); fEA_RI(RsV,siV); fLOAD(1,4,u,EA,RdV); }\"\"\" \
)
ATTRIBUTES( \
    "L2_loadri_io", \
    "ATTRIBS(A_LOAD)" \
)
SEMANTICS( \
    "C2_cmpgti", \
    "Pd4=cmp.gt(Rs32,#s10)", \
    \"\"\"{fIMMEXT(siV); PdV=f8BITSOF(RsV>siV);}\"\"\" \
)
ATTRIBUTES( \
    "C2_cmpgti", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "J2_trap0", \
    "trap0(#u8)", \
    \"\"\"fTRAP(0,uiV);\"\"\" \
)
ATTRIBUTES( \
    "J2_trap0", \
    "ATTRIBS(A_COF, A_BN_SYSTEM)" \
)
SEMANTICS( \
    "SA1_seti", \
    "Rd16=#u6", \
    \"\"\"{ fIMMEXT(uiV); RdV=uiV;}\"\"\" \
)
ATTRIBUTES( \
    "SA1_seti", \
    "ATTRIBS(A_SUBINSN)" \
)
SEMANTICS( \
    "C2_cmpeqi", \
    "Pd4=cmp.eq(Rs32,#s10)", \
    \"\"\"{fIMMEXT(siV); PdV=f8BITSOF(RsV==siV);}\"\"\" \
)
ATTRIBUTES( \
    "C2_cmpeqi", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "C2_muxii", \
    "Rd32=mux(Pu4,#s8,#S8)", \
    \"\"\"{ fIMMEXT(siV); (fLSBOLD(PuV)) ? (RdV=siV):(RdV=SiV); }\"\"\" \
)
ATTRIBUTES( \
    "C2_muxii", \
    "ATTRIBS(A_ARCHV2)" \
)
SEMANTICS( \
    "S2_tstbit_i", \
    "Pd4=tstbit(Rs32,#u5)", \
    \"\"\"{ PdV = f8BITSOF((RsV & (1<<uiV)) != 0); }\"\"\" \
)
ATTRIBUTES( \
    "S2_tstbit_i", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "M2_mpyi", \
    "Rd32=mpyi(Rs32,Rt32)", \
    \"\"\"{ RdV=RsV*RtV;}\"\"\" \
)
ATTRIBUTES( \
    "M2_mpyi", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "S2_storerinew_io", \
    "memw""(Rs32+#s11:""2"")=""Nt8.new", \
    \"\"\"{fIMMEXT(siV); fEA_RI(RsV,siV); fSTORE(1,4,EA,fNEWREG_ST(NtN)); }\"\"\" \
)
ATTRIBUTES( \
    "S2_storerinew_io", \
    "ATTRIBS(A_STORE)" \
)
SEMANTICS( \
    "J4_cmpeqi_tp0_jump_t", \
    "p0=""cmp.eq(Rs16,#U5)""; if (p0.new) jump:t #r9:2", \
    \"\"\"{fPART1(fWRITE_P0(f8BITSOF((RsV==UiV)))) fBRANCH_SPECULATE_STALL(fLSBNEW0,,SPECULATE_TAKEN,13,0) if (fLSBNEW0) {fIMMEXT(riV); fPCALIGN(riV); fBRANCH(fREAD_PC()+riV,COF_TYPE_JUMP);}}\"\"\" \
)
ATTRIBUTES( \
    "J4_cmpeqi_tp0_jump_t", \
    "ATTRIBS(A_JUMP,A_NEWCMPJUMP,A_BN_COND_J)" \
)
SEMANTICS( \
    "J4_cmpeqi_fp0_jump_nt", \
    "p0=""cmp.eq(Rs16,#U5)""; if (!p0.new) jump:nt #r9:2", \
    \"\"\"{fPART1(fWRITE_P0(f8BITSOF((RsV==UiV)))) fBRANCH_SPECULATE_STALL(fLSBNEW0NOT,,SPECULATE_NOT_TAKEN,13,0) if (fLSBNEW0NOT) {fIMMEXT(riV); fPCALIGN(riV); fBRANCH(fREAD_PC()+riV,COF_TYPE_JUMP);}}\"\"\" \
)
ATTRIBUTES( \
    "J4_cmpeqi_fp0_jump_nt", \
    "ATTRIBS(A_JUMP,A_NEWCMPJUMP,A_BN_COND_J)" \
)
SEMANTICS( \
    "C4_addipc", \
    "Rd32=add(pc,#u6)", \
    \"\"\"{ RdV=fREAD_PC()+fIMMEXT(uiV);}\"\"\" \
)
ATTRIBUTES( \
    "C4_addipc", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "L2_ploadritnew_io", \
    "if (Pt4.new) ""Rd32=memw""(Rs32+#u6:""2"")", \
    \"\"\"{fIMMEXT(uiV); fEA_RI(RsV,uiV); if (fLSBNEW(PtN)) { fLOAD(1,4,u,EA,RdV); } else {LOAD_CANCEL(EA);}}\"\"\" \
)
ATTRIBUTES( \
    "L2_ploadritnew_io", \
    "ATTRIBS(A_ARCHV2,A_LOAD)" \
)
SEMANTICS( \
    "C2_andn", \
    "Pd4=and(Pt4,!Ps4)", \
    \"\"\"{PdV=PtV & (~PsV);}\"\"\" \
)
ATTRIBUTES( \
    "C2_andn", \
    "ATTRIBS(A_CRSLOT23)" \
)
SEMANTICS( \
    "SA1_combine0i", \
    "Rdd8=combine(#0,#u2)", \
    \"\"\"{ fSETWORD(0,RddV,uiV); fSETWORD(1,RddV,0); }\"\"\" \
)
ATTRIBUTES( \
    "SA1_combine0i", \
    "ATTRIBS(A_SUBINSN)" \
)
SEMANTICS( \
    "A2_paddit", \
    "if (Pu4) ""Rd32=add(Rs32,#s8)", \
    \"\"\"{if(fLSBOLD(PuV)){fIMMEXT(siV); RdV=RsV+siV;} else {CANCEL;}}\"\"\" \
)
ATTRIBUTES( \
    "A2_paddit", \
    "ATTRIBS(A_ARCHV2)" \
)
SEMANTICS( \
    "A2_paddif", \
    "if (!Pu4) ""Rd32=add(Rs32,#s8)", \
    \"\"\"{if(fLSBOLDNOT(PuV)){fIMMEXT(siV); RdV=RsV+siV;} else {CANCEL;}}\"\"\" \
)
ATTRIBUTES( \
    "A2_paddif", \
    "ATTRIBS(A_ARCHV2)" \
)
SEMANTICS( \
    "M2_acci", \
    "Rx32+=add(Rs32,Rt32)", \
    \"\"\"{ RxV=RxV + RsV + RtV;}\"\"\" \
)
ATTRIBUTES( \
    "M2_acci", \
    "ATTRIBS(A_ARCHV2)" \
)
SEMANTICS( \
    "L2_loadrub_pi", \
    "Rd32=memub""(Rx32++#s4:""0"")", \
    \"\"\"{fEA_REG(RxV); fPM_I(RxV,siV); fLOAD(1,1,u,EA,RdV);}\"\"\" \
)
ATTRIBUTES( \
    "L2_loadrub_pi", \
    "ATTRIBS(A_LOAD)" \
)
SEMANTICS( \
    "C2_cmoveif", \
    "if (!Pu4) Rd32=#s12", \
    \"\"\"{ fIMMEXT(siV); if (fLSBOLDNOT(PuV)) RdV=siV; else CANCEL;}\"\"\" \
)
ATTRIBUTES( \
    "C2_cmoveif", \
    "ATTRIBS(A_ARCHV2)" \
)
SEMANTICS( \
    "J4_cmpeq_t_jumpnv_t", \
    "if (""cmp.eq(Ns8.new,Rt32)"") jump:t #r9:2", \
    \"\"\"{fBRANCH_SPECULATE_STALL((fNEWREG(NsN)==RtV),,SPECULATE_TAKEN,13,0);if ((fNEWREG(NsN)==RtV)) {fIMMEXT(riV); fPCALIGN(riV); fBRANCH(fREAD_PC()+riV,COF_TYPE_JUMP);}}\"\"\" \
)
ATTRIBUTES( \
    "J4_cmpeq_t_jumpnv_t", \
    "ATTRIBS(A_JUMP,A_DOTNEWVALUE,A_MEMLIKE_PACKET_RULES,A_BN_COND_J)" \
)
SEMANTICS( \
    "J2_callr", \
    "callr Rs32", \
    \"\"\"{ fCALLR(RsV); }\"\"\" \
)
ATTRIBUTES( \
    "J2_callr", \
    "ATTRIBS(A_CALL,A_INDIRECT)" \
)
SEMANTICS( \
    "S2_asl_i_r_or", \
    "Rx" "32" "|" "=asl(" "Rs" "32,#u" "5" ")" "", \
    \"\"\"{ RxV = fECHO(RxV | fASHIFTL(RsV,uiV,4_4)); }\"\"\" \
)
ATTRIBUTES( \
    "S2_asl_i_r_or", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "A2_zxth", \
    "Rd32=zxth(Rs32)", \
    \"\"\"{RdV = fZXTN(16,32,RsV);}\"\"\" \
)
ATTRIBUTES( \
    "A2_zxth", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "A2_sxth", \
    "Rd32=sxth(Rs32)", \
    \"\"\"{RdV = fSXTN(16,32,RsV);}\"\"\" \
)
ATTRIBUTES( \
    "A2_sxth", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "L2_loadrigp", \
    "Rd32=memw""(gp+#u16:""2"")", \
    \"\"\"{fIMMEXT(uiV); fEA_GPI(uiV); fLOAD(1,4,u,EA,RdV); }\"\"\" \
)
ATTRIBUTES( \
    "L2_loadrigp", \
    "ATTRIBS(A_LOAD,A_ARCHV2)" \
)
SEMANTICS( \
    "S2_storerbnew_io", \
    "memb""(Rs32+#s11:""0"")=""Nt8.new", \
    \"\"\"{fIMMEXT(siV); fEA_RI(RsV,siV); fSTORE(1,1,EA,fGETBYTE(0,fNEWREG_ST(NtN))); }\"\"\" \
)
ATTRIBUTES( \
    "S2_storerbnew_io", \
    "ATTRIBS(A_STORE)" \
)
SEMANTICS( \
    "SL2_return_t", \
    "if (p0) dealloc_return", \
    \"\"\"{ fHIDE(size8u_t tmp;); fBRANCH_SPECULATE_STALL(fLSBOLD(fREAD_P0()),, SPECULATE_NOT_TAKEN,4,0); fEA_REG(fREAD_FP()); if (fLSBOLD(fREAD_P0())) { fLOAD(1,8,u,EA,tmp); tmp = fFRAME_UNSCRAMBLE(tmp); fWRITE_LR(fGETWORD(1,tmp)); fWRITE_FP(fGETWORD(0,tmp)); fWRITE_SP(EA+8); fJUMPR(REG_LR,fGETWORD(1,tmp),COF_TYPE_JUMPR);} else {LOAD_CANCEL(EA);} }\"\"\" \
)
ATTRIBUTES( \
    "SL2_return_t", \
    "ATTRIBS(A_JUMP,A_INDIRECT,A_SUBINSN,A_LOAD,A_RESTRICT_SLOT0ONLY,A_RESTRICT_SLOT0ONLY,A_BN_RETURN)" \
)
SEMANTICS( \
    "L4_loadri_rr", \
    "Rd32=memw""(Rs32+Rt32<<#u2)", \
    \"\"\"{fEA_RRs(RsV,RtV,uiV); fLOAD(1,4,u,EA,RdV);}\"\"\" \
)
ATTRIBUTES( \
    "L4_loadri_rr", \
    "ATTRIBS(A_ARCHV2,A_LOAD)" \
)
SEMANTICS( \
    "S2_lsr_i_r_acc", \
    "Rx" "32" "+" "=lsr(" "Rs" "32,#u" "5" ")" "", \
    \"\"\"{ RxV = fECHO(RxV + fLSHIFTR(RsV,uiV,4_4)); }\"\"\" \
)
ATTRIBUTES( \
    "S2_lsr_i_r_acc", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "S2_asr_i_r", \
    "Rd" "32" "" "=asr(" "Rs" "32,#u" "5" ")" "", \
    \"\"\"{ RdV = fECHO( fASHIFTR(RsV,uiV,4_4)); }\"\"\" \
)
ATTRIBUTES( \
    "S2_asr_i_r", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "A2_max", \
    "Rd32=max(Rs32,Rt32)", \
    \"\"\"{ RdV = fMAX(RsV,RtV); }\"\"\" \
)
ATTRIBUTES( \
    "A2_max", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "A2_maxu", \
    "Rd32=maxu(Rs32,Rt32)", \
    \"\"\"{ RdV = fMAX(fCAST4u(RsV),fCAST4u(RtV)); }\"\"\" \
)
ATTRIBUTES( \
    "A2_maxu", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "A2_abs", \
    "Rd32=abs(Rs32)", \
    \"\"\"{ RdV = fABS(RsV); }\"\"\" \
)
ATTRIBUTES( \
    "A2_abs", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "M2_dpmpyuu_s0", \
    "Rdd32=mpyu(Rs32,Rt32)", \
    \"\"\"{RddV=fMPY32UU(fCAST4u(RsV),fCAST4u(RtV));}\"\"\" \
)
ATTRIBUTES( \
    "M2_dpmpyuu_s0", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "S2_storerh_io", \
    "memh""(Rs32+#s11:""1"")=""Rt32", \
    \"\"\"{fIMMEXT(siV); fEA_RI(RsV,siV); fSTORE(1,2,EA,fGETHALF(0,RtV)); }\"\"\" \
)
ATTRIBUTES( \
    "S2_storerh_io", \
    "ATTRIBS(A_STORE)" \
)
SEMANTICS( \
    "M7_dcmpyrw", \
    "Rdd32=" "cmpyrw" "(Rss32," "Rtt32" ")", \
    \"\"\"{ RddV = (fMPY32SS(fGETWORD(0, RssV), fGETWORD(0, RttV)) - fMPY32SS(fGETWORD(1, RssV), fGETWORD(1, RttV)));}\"\"\" \
)
ATTRIBUTES( \
    "M7_dcmpyrw", \
    "ATTRIBS(A_RESTRICT_SLOT3ONLY)" \
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
SEMANTICS( \
    "J2_endloop0", \
    "endloop0", \
    \"\"\"{ if (fGET_LPCFG) { fHIDE( if (fGET_LPCFG >= 2) { } else ) if (fGET_LPCFG==1) { fWRITE_P3(0xff); } fSET_LPCFG(fGET_LPCFG-1); } if (fREAD_LC0>1) { fBRANCH(fREAD_SA0,COF_TYPE_LOOPEND0); fWRITE_LC0(fREAD_LC0-1); } }\"\"\" \
)
ATTRIBUTES( \
    "J2_endloop0", \
    "ATTRIBS(A_HWLOOP0_END, A_JUMP, A_INDIRECT, A_BN_COND_J)" \
)
SEMANTICS( \
    "A2_tfrcrr", \
    "Rd32=Cs32", \
    \"\"\"{ RdV=CsV;}\"\"\" \
)
ATTRIBUTES( \
    "A2_tfrcrr", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "S2_storew_locked", \
    "memw_locked(Rs32,Pd4)=Rt32", \
    \"\"\"{ fEA_REG(RsV); fSTORE_LOCKED(1,4,EA,RtV,PdV) }\"\"\" \
)
ATTRIBUTES( \
    "S2_storew_locked", \
    "ATTRIBS(A_STORE,A_RESTRICT_SLOT0ONLY)" \
)
SEMANTICS( \
    "L4_loadd_locked", \
    "Rdd32=memd_locked(Rs32)", \
    \"\"\"{ fEA_REG(RsV); fLOAD_LOCKED(1,8,u,EA,RddV) }\"\"\" \
)
ATTRIBUTES( \
    "L4_loadd_locked", \
    "ATTRIBS(A_LOAD,A_RESTRICT_SLOT0ONLY)" \
)
SEMANTICS( \
    "M4_xor_and", \
    "Rx32^=and(Rs32,Rt32)", \
    \"\"\"{ RxV ^= (RsV & RtV); }\"\"\" \
)
ATTRIBUTES( \
    "M4_xor_and", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "A2_negp", \
    "Rdd32=neg(Rss32)", \
    \"\"\"{ RddV = -RssV; }\"\"\" \
)
ATTRIBUTES( \
    "A2_negp", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "A2_tfrih", \
    "Rx.H32=#u16", \
    \"\"\"{ fSETHALF(1,RxV,uiV);}\"\"\" \
)
ATTRIBUTES( \
    "A2_tfrih", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "S4_extract", \
    "Rd32=extract(Rs32,#u5,#U5)", \
    \"\"\"{ fHIDE(int) width=uiV; fHIDE(int) offset=UiV; RdV = fSXTN(width,32,(fCAST4_4u(RsV) >> offset)); }\"\"\" \
)
ATTRIBUTES( \
    "S4_extract", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "A2_swiz", \
    "Rd32=swiz(Rs32)", \
    \"\"\"{ fSETBYTE(0,RdV,fGETBYTE(3,RsV)); fSETBYTE(1,RdV,fGETBYTE(2,RsV)); fSETBYTE(2,RdV,fGETBYTE(1,RsV)); fSETBYTE(3,RdV,fGETBYTE(0,RsV)); }\"\"\" \
)
ATTRIBUTES( \
    "A2_swiz", \
    "ATTRIBS(A_ARCHV2)" \
)
SEMANTICS( \
    "A2_combineii", \
    "Rdd32=combine(#s8,#S8)", \
    \"\"\"{ fIMMEXT(siV); fSETWORD(0,RddV,SiV); fSETWORD(1,RddV,siV); }\"\"\" \
)
ATTRIBUTES( \
    "A2_combineii", \
    "ATTRIBS(A_ARCHV2)" \
)
SEMANTICS( \
    "S6_rol_i_r", \
    "Rd" "32" "" "=rol(" "Rs" "32,#u" "5" ")" "", \
    \"\"\"{ RdV = fECHO( fROTL(RsV,uiV,4_4)); }\"\"\" \
)
ATTRIBUTES( \
    "S6_rol_i_r", \
    "ATTRIBS()" \
)
SEMANTICS( \
    "S6_rol_i_p", \
    "Rdd" "32" "" "=rol(" "Rss" "32,#u" "6" ")" "", \
    \"\"\"{ RddV = fECHO( fROTL(RssV,uiV,8_8)); }\"\"\" \
)
ATTRIBUTES( \
    "S6_rol_i_p", \
    "ATTRIBS()" \
)
"""

ATTRIBS_DEF = """
DEF_ATTRIB(AA_DUMMY, "Dummy Zeroth Attribute", "", "")
DEF_ATTRIB(LOAD, "Loads from memory", "", "")
DEF_ATTRIB(STORE, "Stores to memory", "", "")
DEF_ATTRIB(ZZ_LASTATTRIB, "Last attribute in the file", "", "")
"""


class TestGenIlFunc(unittest.TestCase):
  # yapf: disable
  @classmethod
  def setUpClass(cls):
    read_semantics_file_obj(io.StringIO(SEMANTICS))
    read_attribs_file_obj(io.StringIO(ATTRIBS_DEF))
    set_overrides()
    calculate_attribs()
    cls.tagregs = get_tagregs()
    cls.tagimms = get_tagimms()
    cls.maxDiff = None

  def parse_semantics(self, tag):
    parts = preprocess_semantics(tag)
    if len(parts) > 1:
      return [
          process_semantics(tag, parts[0]),
          process_semantics(tag, parts[1])
      ]
    self.assertEqual(len(parts), 1)
    return process_semantics(tag, parts[0])

  def test_tfrsi(self):
    self.assertEqual(
        self.parse_semantics('A2_tfrsi'),
        [IlSetRegister(4, 'RdV', IlConst(4, 'siV'))])

  def test_add(self):
    self.assertEqual(
        self.parse_semantics('A2_add'), [
            IlSetRegister(4, 'RdV',
                          IlAdd(4, IlRegister(4, 'RsV'), IlRegister(4, 'RtV')))
        ])

  def test_storeri_io(self):
    self.assertEqual(
        self.parse_semantics('S2_storeri_io'), [
            IlSetRegister(4, 'EA_REG',
                          IlAdd(4, IlRegister(4, 'RsV'), IlConst(4, 'siV'))),
            IlStore(4, IlRegister(4, 'EA_REG'), IlRegister(4, 'RtV'))
        ])

  def test_storeiri_io(self):
    self.assertEqual(
        self.parse_semantics('S4_storeiri_io'), [
            IlSetRegister(4, 'EA_REG',
                          IlAdd(4, IlRegister(4, 'RsV'), IlConst(4, 'uiV'))),
            IlStore(4, IlRegister(4, 'EA_REG'), IlConst(4, 'SiV'))
        ])

  def test_loadrb_io(self):
    self.assertEqual(
        self.parse_semantics('L2_loadrb_io'), [
            IlSetRegister(4, 'EA_REG',
                          IlAdd(4, IlRegister(4, 'RsV'), IlConst(4, 'siV'))),
            IlSetRegister(4, 'RdV',
                          IlSignExtend(4, IlLoad(1, IlRegister(4, 'EA_REG'))))
        ])

  def test_jump(self):
    self.assertEqual(
        self.parse_semantics('J2_jump'), [
            RawC('riV = riV & ~PCALIGN_MASK;'),
            IlJump(IlAdd(4, IlConstPointer(4, 'pc'), IlConst(4, 'riV')))
        ])

  def test_call(self):
    self.assertEqual(
        self.parse_semantics('J2_call'), [
            RawC('riV = riV & ~PCALIGN_MASK;'),
            IlCall(IlAdd(4, IlConstPointer(4, 'pc'), IlConst(4, 'riV')))
        ])

  def test_allocframe(self):
    self.assertEqual(
        self.parse_semantics('S2_allocframe'), [
            IlSetRegister(
                4, 'EA_REG',
                IlAdd(4, IlRegister(4, 'RxV'), IlNeg(4, IlConst(4, 8)))),
            IlStore(8, IlRegister(4, 'EA_REG'),
                    IlRegisterSplit(4, 'HEX_REG_LR', 'HEX_REG_FP')),
            IlSetRegister(4, 'HEX_REG_FP', IlRegister(4, 'EA_REG')),
            IlSetRegister(4, 'RxV',
                          IlSub(4, IlRegister(4, 'EA_REG'), IlConst(4, 'uiV')))
        ])

  def test_addp(self):
    self.assertEqual(
        self.parse_semantics('A2_addp'), [
            IlSetRegister(
                8, 'RddV', IlAdd(8, IlRegister(8, 'RssV'), IlRegister(
                    8, 'RttV')))
        ])

  def test_return(self):
    self.assertEqual(
        self.parse_semantics('L4_return'), [
            IlSetRegister(4, 'EA_REG', IlRegister(4, 'RsV')),
            IlSetRegister(8, 'TMP_REG', IlLoad(8, IlRegister(4, 'EA_REG'))),
            IlSetRegister(8, 'RddV', IlRegister(8, 'TMP_REG')),
            IlSetRegister(4, 'HEX_REG_SP',
                          IlAdd(4, IlRegister(4, 'EA_REG'), IlConst(4, 8))),
            IlReturn(
                IlSignExtend(
                    8,
                    IlLowPart(
                        4,
                        IlArithShiftRight(8, IlRegister(8, 'RddV'),
                                          IlConst(1, 32)))))
        ])

  def test_deallocframe(self):
    self.assertEqual(
        self.parse_semantics('L2_deallocframe'), [
            IlSetRegister(4, 'EA_REG', IlRegister(4, 'RsV')),
            IlSetRegister(8, 'TMP_REG', IlLoad(8, IlRegister(4, 'EA_REG'))),
            IlSetRegister(8, 'RddV', IlRegister(8, 'TMP_REG')),
            IlSetRegister(4, 'HEX_REG_SP',
                          IlAdd(4, IlRegister(4, 'EA_REG'), IlConst(4, 8)))
        ])

  def test_loadri_io(self):
    self.assertEqual(
        self.parse_semantics('L2_loadri_io'), [
            IlSetRegister(4, 'EA_REG',
                          IlAdd(4, IlRegister(4, 'RsV'), IlConst(4, 'siV'))),
            IlSetRegister(4, 'RdV', IlLoad(4, IlRegister(4, 'EA_REG')))
        ])

  def test_jumpr(self):
    self.assertEqual(
        self.parse_semantics('J2_jumpr'), [
            IlSetRegister(4, 'BRANCHR_DEST_ARRAY + insn_num',
                          IlRegister(4, 'RsV')),
            IlJump(IlRegister(4, 'RsV')),
        ])

  def test_cmpgti(self):
    self.assertEqual(
        self.parse_semantics('C2_cmpgti'), [
            IlSetRegister(
                1, 'PdV',
                IlCompareSignedGreaterThan(4, IlRegister(4, 'RsV'),
                                           IlConst(4, 'siV')))
        ])

  def test_trap0(self):
    self.assertEqual(self.parse_semantics('J2_trap0'), [IlSystemCall()])

  def test_cmpeqi(self):
    self.assertEqual(
        self.parse_semantics('C2_cmpeqi'), [
            IlSetRegister(
                1, 'PdV',
                IlCompareEqual(4, IlRegister(4, 'RsV'), IlConst(4, 'siV')))
        ])

  def test_muxii(self):
    self.assertEqual(
        self.parse_semantics('C2_muxii'), [
            '{ LowLevelILLabel true_case, false_case, done;',
            IlIf(IlRegister(1, 'PuV'), 'true_case', 'false_case'), 'true_case',
            IlSetRegister(4, 'RdV', IlConst(4, 'siV')),
            IlGoto('done'), 'false_case',
            IlSetRegister(4, 'RdV', IlConst(4, 'SiV')), 'done', '}'
        ])

  def test_tstbit(self):
    self.assertEqual(
        self.parse_semantics('S2_tstbit_i'), [
            IlSetRegister(
                1, 'PdV',
                IlCompareNotEqual(
                    4,
                    IlAnd(4, IlRegister(4, 'RsV'),
                          IlShiftLeft(4, IlConst(4, 1), IlConst(4, 'uiV'))),
                    IlConst(4, 0)))
        ])

  def test_jumpt(self):
    self.assertEqual(
        self.parse_semantics('J2_jumpt'), [
            '{ LowLevelILLabel true_case, done;',
            IlIf(IlRegister(1, 'PuV'), 'true_case',
                 'done'), 'true_case', 'riV = riV & ~PCALIGN_MASK;',
            IlSetRegister(1, 'BRANCH_TAKEN_ARRAY + insn_num', IlConst(1, 1)),
            IlJump(IlAdd(4, IlConstPointer(4, 'pc'), IlConst(4, 'riV'))),
            'done', '}'
        ])

  def test_mpyi(self):
    self.assertEqual(
        self.parse_semantics('M2_mpyi'), [
            IlSetRegister(4, 'RdV',
                          IlMult(4, IlRegister(4, 'RsV'), IlRegister(4, 'RtV')))
        ])

  def test_storerinew(self):
    self.assertEqual(
        self.parse_semantics('S2_storerinew_io'), [
            IlSetRegister(4, 'EA_REG',
                          IlAdd(4, IlRegister(4, 'RsV'), IlConst(4, 'siV'))),
            IlStore(4, IlRegister(4, 'EA_REG'), IlRegister(4, 'NtN'))
        ])

  def test_cmpjump_t(self):
    self.assertEqual(
        self.parse_semantics('J4_cmpeqi_tp0_jump_t'),
        [[
            IlSetRegister(
                1, 'Pd0',
                IlCompareEqual(4, IlRegister(4, 'RsV'), IlConst(4, 'UiV')))
        ],
         [
             '{ LowLevelILLabel true_case, done;',
             IlIf(IlRegister(1, 'Pd0'), 'true_case',
                  'done'), 'true_case', 'riV = riV & ~PCALIGN_MASK;',
             IlSetRegister(1, 'BRANCH_TAKEN_ARRAY + insn_num', IlConst(1, 1)),
             IlJump(IlAdd(4, IlConstPointer(4, 'pc'), IlConst(4, 'riV'))),
             'done', '}'
         ]])

  def test_cmpjump_nt(self):
    self.assertEqual(
        self.parse_semantics('J4_cmpeqi_fp0_jump_nt'),
        [[
            IlSetRegister(
                1, 'Pd0',
                IlCompareEqual(4, IlRegister(4, 'RsV'), IlConst(4, 'UiV')))
        ],
         [
             '{ LowLevelILLabel true_case, done;',
             IlIf(IlNot(1, IlRegister(1, 'Pd0')), 'true_case',
                  'done'), 'true_case', 'riV = riV & ~PCALIGN_MASK;',
             IlSetRegister(1, 'BRANCH_TAKEN_ARRAY + insn_num', IlConst(1, 1)),
             IlJump(IlAdd(4, IlConstPointer(4, 'pc'), IlConst(4, 'riV'))),
             'done', '}'
         ]])

  def test_addipc(self):
    self.assertEqual(
        self.parse_semantics('C4_addipc'), [
            IlSetRegister(4, 'RdV',
                          IlAdd(4, IlConstPointer(4, 'pc'), IlConst(4, 'uiV')))
        ])

  def test_ploadritnew(self):
    self.assertEqual(
        self.parse_semantics('L2_ploadritnew_io'), [
            IlSetRegister(4, 'EA_REG',
                          IlAdd(4, IlRegister(4, 'RsV'), IlConst(
                              4, 'uiV'))), '{ LowLevelILLabel true_case, done;',
            IlIf(IlRegister(1, 'PtN'), 'true_case', 'done'), 'true_case',
            IlSetRegister(4, 'RdV', IlLoad(4, IlRegister(4, 'EA_REG'))), 'done',
            '}'
        ])

  def test_andn(self):
    self.assertEqual(
        self.parse_semantics('C2_andn'), [
            IlSetRegister(
                1, 'PdV',
                IlAnd(1, IlRegister(1, 'PtV'), IlNot(1, IlRegister(1, 'PsV'))))
        ])

  def test_combine0i(self):
    self.assertEqual(
        self.parse_semantics('SA1_combine0i'), [
            IlSetRegister(
                8, 'RddV',
                IlOr(
                    8,
                    IlAnd(
                        8, IlRegister(8, 'RddV'),
                        IlNot(
                            8,
                            IlShiftLeft(8, IlConst(4, 0xffffffff), IlConst(
                                1, 0)))),
                    IlShiftLeft(
                        8, IlAnd(8, IlConst(4, 'uiV'), IlConst(4, 0xffffffff)),
                        IlConst(1, 0)))),
            IlSetRegister(
                8, 'RddV',
                IlOr(
                    8,
                    IlAnd(
                        8, IlRegister(8, 'RddV'),
                        IlNot(
                            8,
                            IlShiftLeft(8, IlConst(4, 0xffffffff), IlConst(
                                1, 32)))),
                    IlShiftLeft(8,
                                IlAnd(8, IlConst(4, 0), IlConst(4, 0xffffffff)),
                                IlConst(1, 32))))
        ])

  def test_paddit(self):
    self.assertEqual(
        self.parse_semantics('A2_paddit'), [
            '{ LowLevelILLabel true_case, done;',
            IlIf(IlRegister(1, 'PuV'), 'true_case', 'done'), 'true_case',
            IlSetRegister(4, 'RdV',
                          IlAdd(4, IlRegister(4, 'RsV'), IlConst(4, 'siV'))),
            'done', '}'
        ])

  def test_paddif(self):
    self.assertEqual(
        self.parse_semantics('A2_paddif'), [
            '{ LowLevelILLabel true_case, done;',
            IlIf(IlNot(1, IlRegister(1, 'PuV')), 'true_case',
                 'done'), 'true_case',
            IlSetRegister(4, 'RdV',
                          IlAdd(4, IlRegister(4, 'RsV'), IlConst(4, 'siV'))),
            'done', '}'
        ])

  def test_acci(self):
    self.assertEqual(
        self.parse_semantics('M2_acci'), [
            IlSetRegister(
                4, 'RxV',
                IlAdd(4, IlRegister(4, 'RxV'),
                      IlAdd(4, IlRegister(4, 'RsV'), IlRegister(4, 'RtV'))))
        ])

  def test_loadrub_pi(self):
    self.assertEqual(
        self.parse_semantics('L2_loadrub_pi'), [
            IlSetRegister(4, 'EA_REG', IlRegister(4, 'RxV')),
            IlSetRegister(4, 'RxV',
                          IlAdd(4, IlRegister(4, 'RxV'), IlConst(4, 'siV'))),
            IlSetRegister(4, 'RdV',
                          IlZeroExtend(4, IlLoad(1, IlRegister(4, 'EA_REG'))))
        ])

  def test_cmoveif(self):
    self.assertEqual(
        self.parse_semantics('C2_cmoveif'), [
            '{ LowLevelILLabel true_case, done;',
            IlIf(IlNot(1, IlRegister(1, 'PuV')), 'true_case', 'done'),
            'true_case',
            IlSetRegister(4, 'RdV', IlConst(4, 'siV')), 'done', '}'
        ])

  def test_cmpeq_jumpnv(self):
    self.assertEqual(
        self.parse_semantics('J4_cmpeq_t_jumpnv_t'), [
            '{ LowLevelILLabel true_case, done;',
            IlIf(
                IlCompareEqual(4, IlRegister(4, 'NsN'), IlRegister(4, 'RtV')),
                'true_case', 'done'), 'true_case', 'riV = riV & ~PCALIGN_MASK;',
            IlSetRegister(1, 'BRANCH_TAKEN_ARRAY + insn_num', IlConst(1, 1)),
            IlJump(IlAdd(4, IlConstPointer(4, 'pc'), IlConst(4, 'riV'))),
            'done', '}'
        ])

  def test_callr(self):
    self.assertEqual(
        self.parse_semantics('J2_callr'), [
            IlSetRegister(4, 'BRANCHR_DEST_ARRAY + insn_num',
                          IlRegister(4, 'RsV')),
            IlCall(IlRegister(4, 'RsV'))
        ])

  def test_asl_or(self):
    self.assertEqual(
        self.parse_semantics('S2_asl_i_r_or'), [
            IlSetRegister(
                4, 'RxV',
                IlOr(4, IlRegister(4, 'RxV'),
                     IlShiftLeft(4, IlRegister(4, 'RsV'), IlConst(4, 'uiV'))))
        ])

  def test_zxth(self):
    self.assertEqual(
        self.parse_semantics('A2_zxth'), [
            IlSetRegister(
                4, 'RdV',
                IlAnd(
                    4, IlRegister(4, 'RsV'),
                    IlSub(4, IlShiftLeft(4, IlConst(4, 1), IlConst(4, 16)),
                          IlConst(4, 1))))
        ])

  def test_sxth(self):
    self.assertEqual(
        self.parse_semantics('A2_sxth'), [
            IlSetRegister(
                4, 'RdV',
                IlSub(
                    4,
                    IlXor(
                        4,
                        IlAnd(
                            4, IlRegister(4, 'RsV'),
                            IlSub(4,
                                  IlShiftLeft(4, IlConst(4, 1), IlConst(4, 16)),
                                  IlConst(4, 1))),
                        IlShiftLeft(4, IlConst(4, 1),
                                    IlSub(4, IlConst(4, 16), IlConst(4, 1)))),
                    IlShiftLeft(4, IlConst(4, 1),
                                IlSub(4, IlConst(4, 16), IlConst(4, 1)))))
        ])

  def test_loadrigp(self):
    self.assertEqual(
        self.parse_semantics('L2_loadrigp'), [
            IlSetRegister(4, 'EA_REG', IlAdd(4, IlReadGP(4), IlConst(4,
                                                                     'uiV'))),
            IlSetRegister(4, 'RdV', IlLoad(4, IlRegister(4, 'EA_REG')))
        ])

  def test_storerbnew_io(self):
    self.assertEqual(
        self.parse_semantics('S2_storerbnew_io'), [
            IlSetRegister(4, 'EA_REG',
                          IlAdd(4, IlRegister(4, 'RsV'), IlConst(4, 'siV'))),
            IlStore(1, IlRegister(4, 'EA_REG'),
                    IlLowPart(1, IlRegister(4, 'NtN')))
        ])

  def test_sl2_return_t(self):
    self.assertEqual(
        self.parse_semantics('SL2_return_t'), [
            IlSetRegister(4, 'EA_REG', IlRegister(4, 'HEX_REG_FP')),
            '{ LowLevelILLabel true_case, done;',
            IlIf(IlRegister(1, 'Pd0'), 'true_case', 'done'), 'true_case',
            IlSetRegister(8, 'TMP_REG', IlLoad(8, IlRegister(4, 'EA_REG'))),
            IlSetRegister(8, 'TMP_REG', IlRegister(8, 'TMP_REG')),
            IlSetRegister(
                4, 'HEX_REG_LR',
                IlSignExtend(
                    8,
                    IlLowPart(
                        4,
                        IlArithShiftRight(8, IlRegister(8, 'TMP_REG'),
                                          IlConst(1, 32))))),
            IlSetRegister(
                4, 'HEX_REG_FP',
                IlSignExtend(8, IlLowPart(4, IlRegister(8, 'TMP_REG')))),
            IlSetRegister(4, 'HEX_REG_SP',
                          IlAdd(4, IlRegister(4, 'EA_REG'), IlConst(4, 8))),
            IlReturn(
                IlSignExtend(
                    8,
                    IlLowPart(
                        4,
                        IlArithShiftRight(8, IlRegister(8, 'TMP_REG'),
                                          IlConst(1, 32))))), 'done', '}'
        ])

  def test_loadri_rr(self):
    self.assertEqual(
        self.parse_semantics('L4_loadri_rr'), [
            IlSetRegister(
                4, 'EA_REG',
                IlAdd(4, IlRegister(4, 'RsV'),
                      IlShiftLeft(4, IlRegister(4, 'RtV'), IlConst(4, 'uiV')))),
            IlSetRegister(4, 'RdV', IlLoad(4, IlRegister(4, 'EA_REG')))
        ])

  def test_lsr_i_r_acc(self):
    self.assertEqual(
        self.parse_semantics('S2_lsr_i_r_acc'), [
            IlSetRegister(
                4, 'RxV',
                IlAdd(
                    4, IlRegister(4, 'RxV'),
                    IlLogicalShiftRight(4, IlRegister(4, 'RsV'),
                                        IlConst(4, 'uiV'))))
        ])

  def test_asr_i_r(self):
    self.assertEqual(
        self.parse_semantics('S2_asr_i_r'), [
            IlSetRegister(
                4, 'RdV',
                IlArithShiftRight(4, IlRegister(4, 'RsV'), IlConst(4, 'uiV')))
        ])

  def test_max(self):
    self.assertEqual(
        self.parse_semantics('A2_max'), [
            IlSetRegister(
                4, 'RdV',
                IlAdd(
                    4,
                    IlMult(
                        4,
                        IlBoolToInt(
                            4,
                            IlCompareSignedGreaterEqual(4, IlRegister(4, 'RsV'),
                                                        IlRegister(4, 'RtV'))),
                        IlRegister(4, 'RsV')),
                    IlMult(
                        4,
                        IlBoolToInt(
                            4,
                            IlCompareSignedLessThan(4, IlRegister(4, 'RsV'),
                                                    IlRegister(4, 'RtV'))),
                        IlRegister(4, 'RtV'))))
        ])

  def test_maxu(self):
    self.assertEqual(
        self.parse_semantics('A2_maxu'), [
            IlSetRegister(
                4, 'RdV',
                IlAdd(
                    4,
                    IlMult(
                        4,
                        IlBoolToInt(
                            4,
                            IlCompareUnsignedGreaterEqual(
                                4, IlRegister(4, 'RsV'), IlRegister(4, 'RtV'))),
                        IlRegister(4, 'RsV')),
                    IlMult(
                        4,
                        IlBoolToInt(
                            4,
                            IlCompareUnsignedLessThan(4, IlRegister(4, 'RsV'),
                                                      IlRegister(4, 'RtV'))),
                        IlRegister(4, 'RtV'))))
        ])

  def test_abs(self):
    self.assertEqual(
        self.parse_semantics('A2_abs'), [
            IlSetRegister(
                4, 'RdV',
                IlMult(
                    4,
                    IlSub(
                        4, IlConst(4, 1),
                        IlMult(
                            4, IlConst(4, 2),
                            IlBoolToInt(
                                4,
                                IlCompareSignedLessThan(4, IlRegister(4, 'RsV'),
                                                        IlConst(4, 0))))),
                    IlRegister(4, 'RsV')))
        ])

  def test_dpmpyuu(self):
    self.assertEqual(
        self.parse_semantics('M2_dpmpyuu_s0'), [
            IlSetRegister(
                8, 'RddV',
                IlMult(8, IlZeroExtend(8, IlRegister(4, 'RsV')),
                       IlZeroExtend(8, IlRegister(4, 'RtV'))))
        ])

  def test_storerh_io(self):
    self.assertEqual(
        self.parse_semantics('S2_storerh_io'), [
            IlSetRegister(4, 'EA_REG',
                          IlAdd(4, IlRegister(4, 'RsV'), IlConst(4, 'siV'))),
            IlStore(2, IlRegister(4, 'EA_REG'),
                    IlSignExtend(4, IlLowPart(2, IlRegister(4, 'RtV'))))
        ])

  def test_dcmpyrw(self):
    self.assertEqual(
        self.parse_semantics('M7_dcmpyrw'), [
            IlSetRegister(
                8, 'RddV',
                IlSub(
                    8,
                    IlMult(
                        8,
                        IlSignExtend(
                            8,
                            IlLowPart(
                                4,
                                IlSignExtend(
                                    8, IlLowPart(4, IlRegister(8, 'RssV'))))),
                        IlSignExtend(
                            8,
                            IlLowPart(
                                4,
                                IlSignExtend(
                                    8, IlLowPart(4, IlRegister(8, 'RttV')))))),
                    IlMult(
                        8,
                        IlSignExtend(
                            8,
                            IlLowPart(
                                4,
                                IlSignExtend(
                                    8,
                                    IlLowPart(
                                        4,
                                        IlArithShiftRight(
                                            8, IlRegister(8, 'RssV'),
                                            IlConst(1, 32)))))),
                        IlSignExtend(
                            8,
                            IlLowPart(
                                4,
                                IlSignExtend(
                                    8,
                                    IlLowPart(
                                        4,
                                        IlArithShiftRight(
                                            8, IlRegister(8, 'RttV'),
                                            IlConst(1, 32)))))))))
        ])

  def test_loop0i(self):
    self.assertEqual(
        self.parse_semantics('J2_loop0i'), [
            'riV = riV & ~PCALIGN_MASK;',
            IlSetRegister(4, 'HEX_REG_LC0', IlConst(4, 'UiV')),
            IlSetRegister(4, 'HEX_REG_SA0',
                          IlAdd(4, IlConstPointer(4, 'pc'), IlConst(4, 'riV'))),
            IlSetRegister(1, 'HEX_REG_USR_LPCFG', IlConst(4, 0))
        ])

  def test_endloop0(self):
    self.assertEqual(
        self.parse_semantics('J2_endloop0'), [
            '{ LowLevelILLabel true_case, done;',
            IlIf(IlRegister(1, 'HEX_REG_USR_LPCFG'), 'true_case',
                 'done'), 'true_case', '{ LowLevelILLabel true_case, done;',
            IlIf(
                IlCompareEqual(1, IlRegister(1, 'HEX_REG_USR_LPCFG'),
                               IlConst(4, 1)), 'true_case',
                'done'), 'true_case',
            IlSetRegister(1, 'Pd3', IlConst(4, '0xff')), 'done', '}',
            IlSetRegister(
                1, 'HEX_REG_USR_LPCFG',
                IlSub(1, IlRegister(1, 'HEX_REG_USR_LPCFG'), IlConst(4, 1))),
            'done', '}', '{ LowLevelILLabel true_case, done;',
            IlIf(
                IlCompareSignedGreaterThan(4, IlRegister(4, 'HEX_REG_LC0'),
                                           IlConst(4, 1)), 'true_case',
                'done'), 'true_case',
            IlSetRegister(1, 'BRANCH_TAKEN_ARRAY + insn_num', IlConst(1, 1)),
            IlSetRegister(4, 'BRANCHR_DEST_ARRAY + insn_num',
                          IlRegister(4, 'HEX_REG_SA0')),
            IlJump(IlRegister(4, 'HEX_REG_SA0')),
            IlSetRegister(4, 'HEX_REG_LC0',
                          IlSub(4, IlRegister(4, 'HEX_REG_LC0'), IlConst(
                              4, 1))), 'done', '}'
        ])

  def test_tfrcrr(self):
    self.assertEqual(
        self.parse_semantics('A2_tfrcrr'),
        [IlSetRegister(4, 'RdV', IlRegister(4, 'CsV'))])

  def test_storew_locked(self):
    self.assertEqual(
        self.parse_semantics('S2_storew_locked'), [
            IlSetRegister(4, 'EA_REG', IlRegister(4, 'RsV')),
            IlStore(4, IlRegister(4, 'EA_REG'), IlRegister(4, 'RtV')),
            IlSetRegister(1, 'PdV', IlConst(1, 1))
        ])

  def test_loadd_locked(self):
    self.assertEqual(
        self.parse_semantics('L4_loadd_locked'), [
            IlSetRegister(4, 'EA_REG', IlRegister(4, 'RsV')),
            IlSetRegister(8, 'RddV', IlLoad(8, IlRegister(4, 'EA_REG')))
        ])

  def test_xor_and(self):
    self.assertEqual(
        self.parse_semantics('M4_xor_and'), [
            IlSetRegister(
                4, 'RxV',
                IlXor(4, IlRegister(4, 'RxV'),
                      IlAnd(4, IlRegister(4, 'RsV'), IlRegister(4, 'RtV'))))
        ])

  def test_negp(self):
    self.assertEqual(
        self.parse_semantics('A2_negp'),
        [IlSetRegister(8, 'RddV', IlNeg(8, IlRegister(8, 'RssV')))])

  def test_tfrih(self):
    self.assertEqual(
        self.parse_semantics('A2_tfrih'), [
            IlSetRegister(
                4, 'RxV',
                IlOr(
                    4,
                    IlAnd(
                        4, IlRegister(4, 'RxV'),
                        IlNot(
                            4, IlShiftLeft(4, IlConst(4, 0xffff), IlConst(
                                1, 16)))),
                    IlShiftLeft(4,
                                IlAnd(4, IlConst(4, 'uiV'), IlConst(4, 0xffff)),
                                IlConst(1, 16))))
        ])

  def test_extract(self):
    self.assertEqual(
        self.parse_semantics('S4_extract'), [
            IlSetRegister(8, 'WIDTH_REG', IlConst(4, 'uiV')),
            IlSetRegister(8, 'OFFSET_REG', IlConst(4, 'UiV')),
            IlSetRegister(
                4, 'RdV',
                IlSub(
                    4,
                    IlXor(
                        4,
                        IlAnd(
                            4,
                            IlLogicalShiftRight(4, IlRegister(4, 'RsV'),
                                                IlRegister(8, 'OFFSET_REG')),
                            IlSub(
                                4,
                                IlShiftLeft(4, IlConst(4, 1),
                                            IlRegister(8, 'WIDTH_REG')),
                                IlConst(4, 1))),
                        IlShiftLeft(
                            4, IlConst(4, 1),
                            IlSub(8, IlRegister(8, 'WIDTH_REG'), IlConst(4,
                                                                         1)))),
                    IlShiftLeft(
                        4, IlConst(4, 1),
                        IlSub(8, IlRegister(8, 'WIDTH_REG'), IlConst(4, 1)))))
        ])

  def test_swiz(self):
    self.assertEqual(
        self.parse_semantics('A2_swiz'), [
            IlSetRegister(
                4, 'RdV',
                IlOr(
                    4,
                    IlShiftLeft(
                        4, IlAnd(4, IlRegister(4, 'RsV'), IlConst(4, 0xff)),
                        IlConst(1, 24)),
                    IlOr(
                        4,
                        IlShiftLeft(
                            4, IlAnd(4, IlRegister(4, 'RsV'), IlConst(
                                4, 0xff00)), IlConst(1, 8)),
                        IlOr(
                            4,
                            IlLogicalShiftRight(
                                4,
                                IlAnd(4, IlRegister(4, 'RsV'),
                                      IlConst(4, 0xff0000)), IlConst(1, 8)),
                            IlLogicalShiftRight(
                                4,
                                IlAnd(4, IlRegister(4, 'RsV'),
                                      IlConst(4, 0xff000000)), IlConst(1,
                                                                       24))))))
        ])

  def test_combineii(self):
    self.assertEqual(
        self.parse_semantics('A2_combineii'), [
            IlSetRegister(
                8, 'RddV',
                IlOr(
                    8,
                    IlAnd(
                        8, IlRegister(8, 'RddV'),
                        IlNot(
                            8,
                            IlShiftLeft(8, IlConst(4, 0xffffffff), IlConst(
                                1, 0)))),
                    IlShiftLeft(
                        8, IlAnd(8, IlConst(4, 'SiV'), IlConst(4, 0xffffffff)),
                        IlConst(1, 0)))),
            IlSetRegister(
                8, 'RddV',
                IlOr(
                    8,
                    IlAnd(
                        8, IlRegister(8, 'RddV'),
                        IlNot(
                            8,
                            IlShiftLeft(8, IlConst(4, 0xffffffff), IlConst(
                                1, 32)))),
                    IlShiftLeft(
                        8, IlAnd(8, IlConst(4, 'siV'), IlConst(4, 0xffffffff)),
                        IlConst(1, 32))))
        ])

  # yapf: enable
  def test_rol_i_r(self):
    self.assertEqual(
        self.parse_semantics('S6_rol_i_r'), [
            IlSetRegister(
                4, 'RdV',
                IlRotateLeft(4, IlRegister(4, 'RsV'), IlConst(4, 'uiV')))
        ])

  # yapf: enable
  def test_rol_i_p(self):
    self.assertEqual(
        self.parse_semantics('S6_rol_i_p'), [
            IlSetRegister(
                8, 'RddV',
                IlRotateLeft(8, IlRegister(8, 'RssV'), IlConst(4, 'uiV')))
        ])

  # def test_gen(self):
  #   print(gen_il_func(tag, TestGenIlFunc.tagregs[tag],
  #                    TestGenIlFunc.tagimms[tag]))
  #   for tag in SUPPORTED_TAGS:
  #     print(tag)
  #     out = self.parse_semantics(tag)
  #     print(out)


if __name__ == '__main__':
  unittest.main()

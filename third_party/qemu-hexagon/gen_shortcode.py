#!/usr/bin/env python3

##
##  Copyright(c) 2019-2020 Qualcomm Innovation Center, Inc. All Rights Reserved.
##
##  This program is free software; you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation; either version 2 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with this program; if not, see <http://www.gnu.org/licenses/>.
##

import sys
import re
import string
from io import StringIO

from hex_common import *


def gen_shortcode(f, tag):
  f.write('DEF_SHORTCODE(%s, %s)\n' % (tag, semdict[tag]))


def main():
  read_semantics_file(sys.argv[1])
  read_attribs_file(sys.argv[2])
  calculate_attribs()
  tagregs = get_tagregs()
  tagimms = get_tagimms()

  ##
  ## Generate the shortcode_generated.h file
  ##
  f = StringIO()

  f.write("#ifndef DEF_SHORTCODE\n")
  f.write("#define DEF_SHORTCODE(TAG,SHORTCODE)    /* Nothing */\n")
  f.write("#endif\n")

  for tag in tags:
    ## Skip the priv instructions
    if ("A_PRIV" in attribdict[tag]):
      continue
    ## Skip the guest instructions
    if ("A_GUEST" in attribdict[tag]):
      continue
    ## Skip the diag instructions
    if (tag == "Y6_diag"):
      continue
    if (tag == "Y6_diag0"):
      continue
    if (tag == "Y6_diag1"):
      continue

    gen_shortcode(f, tag)

  f.write("#undef DEF_SHORTCODE\n")

  realf = open(sys.argv[3], 'w')
  realf.write(f.getvalue())
  realf.close()
  f.close()


if __name__ == "__main__":
  main()

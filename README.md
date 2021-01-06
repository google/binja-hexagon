# Binary Ninja Hexagon Processor Plugin

## Overview

This is a new architecture plugin for [Binary Ninja](https://binary.ninja/)
reverse engineering platform. It adds support for Qualcomm's
[Hexagon CPUs](https://en.wikipedia.org/wiki/Qualcomm_Hexagon).

Main features:

1.  **Complete disassembler support**. Plugin decodes individual instructions,
    parses and tokenizes instruction operands, and populates branch information
    for all packets:

![Screenshot1](/docs/images/screenshot1.png)

1.  **Partial decompiler support**. Plugin lifts (a subset of) Hexagon
    instructions to Binary Ninja's
    [Low-Level Intermediate Language](https://docs.binary.ninja/dev/bnil-llil.html)
    (LLIL). Lifter manages clobbered registers, implements ".new" semantics and
    packet level branch semantics. Thanks to BN's IL modules, the LLIL
    representation is lifted to pseudo-C, High-Level IL (HLIL), producing
    readable, decompiled code:

![Screenshot2](/docs/images/screenshot2.png)

## Additional Information

*   [Setup and build](/docs/setup.md) instructions.

*   [High level design](/docs/design.md) document.

## Status

The plugin is very much in Alpha stage. Only around 40% of Hexagon's > 2000
instructions are currently lifted to LLIL. Feedback, bug reports and PRs are
welcome.

## Acknowledgments

This plugin was built using
[QEMU's Hexagon target](https://github.com/quic/qemu) by Taylor Simpson from
Qualcomm Innovation Center.

Instruction lifters are [auto generated](/plugin/gen_il_funcs.py) by parsing
semantics descriptions. These descriptions are preprocessed using
[PCPP](https://github.com/ned14/pcpp) by Niall Douglas and David Beazley, and
parsed using [Lark-parser](https://github.com/lark-parser/lark) by Erez Shinan.

## License

This project is a derivative work of QEMU's Hexagon target, therefore, it is
licensed under GPLv2, as the original work.


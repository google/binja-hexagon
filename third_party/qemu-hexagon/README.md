# QEMU Hexagon Target

This folder is a modified version of [quic/qemu](https://github.com/quic/qemu) Hexagon target.

Local changes include:

*  Added new attribute annotations: `A_BN_COND_J`, `A_BN_RETURN`, `A_BN_SYSTEM`.

*  Replaces `assert`s with `longjmp`s, so decoder fails gracefully for invalid, non-code input.

*  Removed QEMU specific code (`gen_tcg_funcs.py`).

*  Removed QEMU library dependencies.

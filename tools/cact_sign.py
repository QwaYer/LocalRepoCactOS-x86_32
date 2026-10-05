#!/usr/bin/env python3
"""cact_sign.py — Sign a .cctk module with an ECDSA P-256 signature.

Appends the module trailer (see CactKernel-x86_32/tools/modsign.py):

    [ ELF ][ magic:4 = "CMOD" ][ vermagic:4 LE ][ signature:64 ]

The build host signs with the private key (Cact/crypto/modsign/
module_sign_priv.pem); the kernel verifies with the matching public key and
refuses a module whose vermagic does not match its own ABI.  Idempotent: a
module that already carries the trailer is left unchanged.
"""

import os
import sys
from pathlib import Path


def _kernel_root() -> str:
    """Resolve the sibling kernel repo (where the signing tools live)."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(script_dir, "..", "..", "CactKernel-x86_32"))


sys.path.insert(0, os.path.join(_kernel_root(), "tools"))
import modsign  # noqa: E402


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <module.cctk>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "rb") as f:
        data = f.read()

    if modsign.already_signed(data):
        print(f"cact_sign: {Path(path).name} — already signed")
        sys.exit(0)

    if not os.path.isfile(modsign.PRIV_PEM):
        modsign.generate_keys()

    signed = modsign.sign_module(modsign.PRIV_PEM, data)
    with open(path, "wb") as f:
        f.write(signed)

    print(f"cact_sign: {Path(path).name} — signed "
          f"(ECDSA P-256, vermagic 0x{modsign.vermagic():08x})")
    sys.exit(0)


if __name__ == "__main__":
    main()

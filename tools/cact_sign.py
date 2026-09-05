#!/usr/bin/env python3
"""cact_sign.py — Sign .cctk ELF module with HMAC-SHA256.

Appends a 32-byte HMAC-SHA256 tag to the module file.
The tag is computed as HMAC-SHA256(key, ELF data).

The key is read from the kernel's hmac_key.bin
(CactKernel-x86_32/Cact/crypto/hmac_ffi/hmac_key.bin) so it matches the
kernel's Rust cact_hmac_verify(). Generate it with:
  python3 CactKernel-x86_32/tools/gen_hmac_key.py
"""

import os
import sys
import hmac
import hashlib

TAG_SIZE = 32


def _key_path() -> str:
    """Resolve the kernel hmac_key.bin relative to this script (a sibling repo)."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(
        script_dir, "..", "..", "CactKernel-x86_32", "Cact", "crypto", "hmac_ffi", "hmac_key.bin"))


def _load_key() -> bytes:
    path = _key_path()
    try:
        with open(path, "rb") as f:
            key = f.read()
    except FileNotFoundError:
        print(f"HMAC key not found at {path}", file=sys.stderr)
        print("Generate one with: python3 CactKernel-x86_32/tools/gen_hmac_key.py", file=sys.stderr)
        sys.exit(1)
    if len(key) != 32:
        print(f"HMAC key must be exactly 32 bytes, got {len(key)}", file=sys.stderr)
        sys.exit(1)
    return key


def sign(data: bytes) -> bytes:
    return hmac.new(_load_key(), data, hashlib.sha256).digest()


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <module.cctk>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "rb") as f:
        data = f.read()

    # Skip if already signed with the same key
    if len(data) >= TAG_SIZE:
        elf_body = data[:-TAG_SIZE]
        stored_tag = data[-TAG_SIZE:]
        if sign(elf_body) == stored_tag:
            print(f"  [{path}]: already signed, OK")
            sys.exit(0)

    tag = sign(data)

    with open(path, "ab") as f:
        f.write(tag)

    print(f"signed: {path}  tag={tag.hex()}")
    sys.exit(0)


if __name__ == "__main__":
    main()

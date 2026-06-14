#!/usr/bin/env python3
"""Pack LocalRepoCactOS/lib into a flat cctkfs image consumed by the Cact
kernel.

Directory layout (lib_dir):
  lib/*.cctk        → /lib/<name>.cctk    (PCI driver modules)
  lib/*.so          → /lib/<name>.so      (shared libraries)
  lib/*.o           → /lib/<name>.o       (object files, e.g. start.o)
  lib/*.a           → /lib/<name>.a       (static archives)
  lib/bin/*         → /bin/<name>         (user ELF)
  lib/sbin/*        → /sbin/<name>        (priv/net tools)
  lib/<rest>        → /<rest>             (anything else, e.g. include/, usr/)

Layout matches tools/cctkfs.h (little-endian, contiguous):
  cctkfs_hdr (32 B)
  cctkfs_entry[count] (24 B each)
  name blob (NUL-separated, 8-byte aligned)
  data blobs (each 16-byte aligned)
"""
import os
import struct
import sys
from pathlib import Path

MAGIC   = 0x53464B43          # 'CKFS' little endian
VERSION = 1
HDR_FMT = "<IIIIIIII"         # 32 bytes
ENT_FMT = "<IIIIII"           # 24 bytes
ALIGN_NAMES = 8
ALIGN_DATA  = 16


def align_up(n, a):
    return (n + a - 1) & ~(a - 1)


def archive_path(lib_dir: Path, path: Path) -> str:
    """Map a file under lib_dir to its archive path in cctkfs."""
    rel = path.relative_to(lib_dir)
    parts = rel.parts

    # lib/bin/<name>  →  /bin/<name>
    if len(parts) >= 2 and parts[0] == "bin":
        return f"/bin/{'/'.join(parts[1:])}"

    # lib/sbin/<name>  →  /sbin/<name>
    if len(parts) >= 2 and parts[0] == "sbin":
        return f"/sbin/{'/'.join(parts[1:])}"

    # lib/<name>.cctk, lib/<name>.so, lib/<name>.o, lib/<name>.a  →  /lib/<name>
    if len(parts) == 1:
        return f"/lib/{path.name}"

    # lib/<rest>  →  /lib/<rest>
    return f"/lib/{'/'.join(parts)}"


def main(argv):
    if len(argv) != 3:
        print("usage: pack_cctkfs.py <lib_dir> <out_image>", file=sys.stderr)
        return 2

    lib_dir = Path(argv[1])
    out_path = Path(argv[2])

    staged = []

    # Walk the entire lib_dir tree
    for path in sorted(lib_dir.rglob("*")):
        if not path.is_file():
            continue
        arcpath = archive_path(lib_dir, path)
        staged.append((arcpath.encode("utf-8"), path))

    staged.sort(key=lambda t: t[0])

    if not staged:
        print(f"error: no files found in {lib_dir}", file=sys.stderr)
        return 1

    entries = []
    name_blob = bytearray()
    for archive_name_bytes, path in staged:
        name_off = len(name_blob)
        name_blob += archive_name_bytes
        name_blob += b"\x00"
        entries.append({
            "path": path,
            "arcname": archive_name_bytes.decode("utf-8"),
            "name_off": name_off,
            "name_len": len(archive_name_bytes),
            "data": path.read_bytes(),
        })

    while len(name_blob) % ALIGN_NAMES:
        name_blob.append(0)

    hdr_size      = struct.calcsize(HDR_FMT)
    ent_size      = struct.calcsize(ENT_FMT)
    entries_off   = hdr_size
    names_off     = entries_off + ent_size * len(entries)
    cur           = names_off + len(name_blob)
    cur           = align_up(cur, ALIGN_DATA)

    for e in entries:
        cur          = align_up(cur, ALIGN_DATA)
        e["data_off"] = cur
        cur += len(e["data"])

    total_size = cur

    blob = bytearray(total_size)
    struct.pack_into(HDR_FMT, blob, 0,
                     MAGIC, VERSION, total_size, len(entries),
                     entries_off, names_off, len(name_blob), 0)

    for i, e in enumerate(entries):
        struct.pack_into(ENT_FMT, blob, entries_off + i * ent_size,
                         e["name_off"], e["name_len"],
                         e["data_off"], len(e["data"]),
                         0, 0)

    blob[names_off:names_off + len(name_blob)] = name_blob

    for e in entries:
        blob[e["data_off"]:e["data_off"] + len(e["data"])] = e["data"]

    out_path.write_bytes(blob)

    print(f"cctkfs: wrote {out_path} ({total_size} bytes, {len(entries)} entries)")
    for e in entries:
        print(f"  {e['arcname']:48s} @ {e['data_off']:#08x}  {len(e['data'])} B")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

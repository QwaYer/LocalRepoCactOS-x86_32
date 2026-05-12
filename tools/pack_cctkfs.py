#!/usr/bin/env python3
"""Pack LocalRepoCactOS/lib into a flat cctkfs image consumed by the Cact
kernel.  Includes:
  - lib/*.cctk  → archive path /lib/<name>.cctk  (PCI driver modules)
  - lib/*.so    → archive path /lib/<name>.so    (shared libraries; served
                  by libfs as cctkfs-overlay)
  - lib/bin/*   → /bin/<name>   (user ELF — binfs + pci_modblob)
  - lib/sbin/*  → /sbin/<name> (priv/net tools — sbinfs + pci_modblob)

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


def main(argv):
    if len(argv) != 3:
        print("usage: pack_cctkfs.py <lib_dir> <out_image>", file=sys.stderr)
        return 2

    lib_dir = Path(argv[1])
    out_path = Path(argv[2])

    staged = []
    for pattern in ("*.cctk", "*.so"):
        for path in sorted(lib_dir.glob(pattern)):
            archive_name = f"/lib/{path.name}".encode("utf-8")
            staged.append((archive_name, path))
    bin_dir = lib_dir / "bin"
    if bin_dir.is_dir():
        for path in sorted(bin_dir.iterdir()):
            if path.is_file():
                archive_name = f"/bin/{path.name}".encode("utf-8")
                staged.append((archive_name, path))
    sbin_dir = lib_dir / "sbin"
    if sbin_dir.is_dir():
        for path in sorted(sbin_dir.iterdir()):
            if path.is_file():
                archive_name = f"/sbin/{path.name}".encode("utf-8")
                staged.append((archive_name, path))
    staged.sort(key=lambda t: t[0])

    if not staged:
        print(f"error: no .cctk/.so in {lib_dir} and no lib/bin/ or lib/sbin/ files",
              file=sys.stderr)
        return 1

    # Archive paths match pci_modblob_get() lookups, e.g. "/lib/foo.cctk",
    # "/bin/cactsole".
    entries = []
    name_blob = bytearray()
    for archive_name, path in staged:
        name_off = len(name_blob)
        name_blob += archive_name
        name_blob += b"\x00"
        entries.append({
            "path": path,
            "arcname": archive_name.decode("utf-8"),
            "name_off": name_off,
            "name_len": len(archive_name),
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
        print(f"  {e['arcname']:32s} @ {e['data_off']:#08x}  {len(e['data'])} B")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

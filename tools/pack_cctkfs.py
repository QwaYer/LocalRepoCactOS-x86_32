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

Output is meant to be watched: a progress bar on a terminal, a line every 10%
when stdout is redirected (meson captures it), and the full file table with -v.
"""
import os
import struct
import sys
import time
from pathlib import Path

MAGIC   = 0x53464B43          # 'CKFS' little endian
VERSION = 1
HDR_FMT = "<IIIIIIII"         # 32 bytes
ENT_FMT = "<IIIIII"           # 24 bytes
ALIGN_NAMES = 8
ALIGN_DATA  = 16

BAR_WIDTH = 26


def align_up(n, a):
    return (n + a - 1) & ~(a - 1)


def fmt_size(n):
    for unit, div in (("GiB", 1 << 30), ("MiB", 1 << 20), ("KiB", 1 << 10)):
        if n >= div:
            return f"{n / div:.2f} {unit}"
    return f"{n} B"


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


def group_of(arcname: str) -> str:
    top = arcname.strip("/").split("/")[0]
    if top == "lib" and arcname.endswith(".cctk"):
        return "modules"
    return top


class Progress:
    """Counts files into the image, quietly or live.

    A terminal gets one rewritten bar line; anything else (meson's log, a file)
    gets a line per 10% so the output stays readable when it is captured.  Both
    forms carry the same information: percentage, count and the file in hand."""

    def __init__(self, total, label):
        self.total = max(total, 1)
        self.label = label
        self.n = 0
        self.live = sys.stdout.isatty()
        self.next_pct = 10
        self.start = time.monotonic()

    def _bar(self, pct):
        filled = int(BAR_WIDTH * pct / 100)
        if filled >= BAR_WIDTH:
            return "=" * BAR_WIDTH
        return "=" * filled + ">" + "." * (BAR_WIDTH - filled - 1)

    def _render(self, name):
        pct = self.n * 100 // self.total
        if len(name) > 34:
            name = "..." + name[-33:]
        return f"  [{self._bar(pct)}] {pct:3d}%  {self.n}/{self.total}  {name}"

    def step(self, name):
        self.n += 1
        pct = self.n * 100 // self.total
        if self.live:
            sys.stdout.write("\r" + self._render(name))
            if self.n == self.total:
                sys.stdout.write("\n")
            sys.stdout.flush()
        elif pct >= self.next_pct or self.n == self.total:
            while pct >= self.next_pct:
                self.next_pct += 10
            print(self._render(name), flush=True)

    def elapsed(self):
        return time.monotonic() - self.start


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("-")]
    verbose = any(a in ("-v", "--verbose") for a in argv[1:])

    if len(args) != 2:
        print("usage: pack_cctkfs.py [-v] <lib_dir> <out_image>", file=sys.stderr)
        return 2

    lib_dir = Path(args[0])
    out_path = Path(args[1])

    staged = []
    for path in sorted(lib_dir.rglob("*")):
        if path.is_file():
            staged.append((archive_path(lib_dir, path).encode("utf-8"), path))
    staged.sort(key=lambda t: t[0])

    if not staged:
        print(f"cctkfs: error: no files found in {lib_dir}", file=sys.stderr)
        return 1

    print(f"cctkfs: packing {len(staged)} files from {lib_dir}")

    # Sizes first: the entry table needs every offset before any data is placed.
    entries = []
    name_blob = bytearray()
    for arc_bytes, path in staged:
        entries.append({
            "path": path,
            "arcname": arc_bytes.decode("utf-8"),
            "name_off": len(name_blob),
            "name_len": len(arc_bytes),
            "size": path.stat().st_size,
        })
        name_blob += arc_bytes + b"\x00"

    while len(name_blob) % ALIGN_NAMES:
        name_blob.append(0)

    hdr_size    = struct.calcsize(HDR_FMT)
    ent_size    = struct.calcsize(ENT_FMT)
    entries_off = hdr_size
    names_off   = entries_off + ent_size * len(entries)
    cur         = align_up(names_off + len(name_blob), ALIGN_DATA)

    for e in entries:
        cur           = align_up(cur, ALIGN_DATA)
        e["data_off"] = cur
        cur          += e["size"]

    blob = bytearray(cur)
    struct.pack_into(HDR_FMT, blob, 0,
                     MAGIC, VERSION, cur, len(entries),
                     entries_off, names_off, len(name_blob), 0)

    for i, e in enumerate(entries):
        struct.pack_into(ENT_FMT, blob, entries_off + i * ent_size,
                         e["name_off"], e["name_len"],
                         e["data_off"], e["size"], 0, 0)

    blob[names_off:names_off + len(name_blob)] = name_blob

    # Hand the files to the image one at a time — this is the part worth watching.
    prog = Progress(len(entries), out_path.name)
    for e in entries:
        data = e["path"].read_bytes()
        blob[e["data_off"]:e["data_off"] + len(data)] = data
        prog.step(e["arcname"])

    out_path.write_bytes(blob)

    groups = {}
    for e in entries:
        groups[group_of(e["arcname"])] = groups.get(group_of(e["arcname"]), 0) + 1
    breakdown = " · ".join(f"{k} {v}" for k, v in sorted(groups.items()))

    print(f"cctkfs: wrote {out_path.name} — {fmt_size(cur)} · "
          f"{len(entries)} entries ({breakdown}) · {prog.elapsed():.2f}s")

    if verbose:
        print(f"cctkfs: image layout ({out_path})")
        for e in entries:
            print(f"  {e['arcname']:48s} @ {e['data_off']:#08x}  {e['size']} B")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

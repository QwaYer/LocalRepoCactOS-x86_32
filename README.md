# 🗂️ LocalRepoCactOS

<p align="center">
  <img src="https://img.shields.io/badge/license-GPLv3-blue.svg?style=for-the-badge" alt="License: GPLv3">
  <img src="https://img.shields.io/badge/output-cctkfs.img-green.svg?style=for-the-badge" alt="cctkfs.img">
  <img src="https://img.shields.io/badge/packer-Python%203-yellow.svg?style=for-the-badge" alt="Python 3">
  <img src="https://img.shields.io/badge/boot-Multiboot2%20module-purple.svg?style=for-the-badge" alt="Multiboot2 module">
  <img src="https://img.shields.io/badge/format-cctkfs%20v1-orange.svg?style=for-the-badge" alt="cctkfs v1">
  <img src="https://img.shields.io/badge/signature-ECDSA%20P--256-red.svg?style=for-the-badge" alt="ECDSA P-256">
</p>

<p align="center">
  Staging tree for <strong>out-of-tree PCI drivers</strong> (<strong><code>*.cctk</code></strong>) and <strong>early userspace</strong> ELFs, packed into one <strong><code>cctkfs.img</code></strong> archive.<br>
  GRUB loads it as a <strong>Multiboot2</strong> <strong><code>module2</code></strong>; the <strong>Cact</strong> kernel copies it into RAM <strong>before paging</strong> and overlays <strong><code>/lib</code></strong>, <strong><code>/bin</code></strong>, and <strong><code>/sbin</code></strong> on top of disk-backed VFS.<br>
  <strong>2.0.0:</strong> all `.cctk` modules are signed with an <strong>ECDSA P-256</strong> key pair. Each module carries a fixed trailer — magic `CMOD`, a 4-byte LE vermagic, then a 64-byte r‖s signature over `ELF || magic || vermagic`; the kernel verifies it with the embedded public key before loading (`mod_tag_verify()` in `Cact/kernel/elf/mod_tag.c`, Rust crate `cact_crypto`). The build host signs with `tools/modsign.py` via `tools/cact_sign.py`.
</p>

---

## 📊 Stats

| | |
|---|---|
| **Output image** | **`cctkfs.img`** — flat archive, magic **`CKFS`** / version **1** ([`tools/cctkfs.h`](tools/cctkfs.h)) |
| **Packer** | **`tools/pack_cctkfs.py`** — `python3 tools/pack_cctkfs.py [-v] lib/ cctkfs.img`; a live progress bar on a terminal, a line per 10% when the output is captured, and the full file table with **`-v`** ([`meson.build`](meson.build)) |
| **Driver slot** | **`lib/*.cctk`** — at least **one** required or the **`stage`** target fails with an explicit error; packed as **`/usr/lib/modules/<name>.cctk`** |
| **Userspace staging** | **`lib/bin/*`** → archive **`/usr/bin/*`** · **`lib/sbin/*`** → **`/usr/sbin/*`** (from **CactUserBins** **`stage`**) |
| **Dynamic libc** | **`lib/clibc.so`** — copied from **`<cactlib_dir>/build-meson/clibc.so`** (the **`cactlib_dir`** option, set by the integrator) |
| **Bootstrap ELFs** | **`init`** (copy of **cgoct**), **`cactsole`**, **`cgoct`**, **`cactsole-rescue`** (copy of **cactsole**) |
| **Merged layout** | userland is **usrmerge**: the kernel serves **`/usr/{bin,sbin,lib}`** and makes **`/bin`, `/sbin`, `/lib`** symlinks into them |

---

## 🔗 Ecosystem

| Piece | Role |
|-------|------|
| **[CactKernel-x86_32](https://github.com/QwaYer/CactKernel-x86_32)** | Parses the **`cctkfs`** module, stages **`cctkfs_stage[]`**, serves **GDD** / **pci_load_module**, **binfs** / **sbinfs** / **libfs** / **usrfs** overlays |
| **`*-for-Cact` driver repos** | Each **`ninja -C build-meson stage`** drops **`*.cctk`** into **`lib/`** here |
| **[CactLib-x86_32](https://github.com/QwaYer/CactLibc-x86_32)** | Builds **`clibc.so`** consumed by staged ELFs |
| **[Cgoct-x86_32](https://github.com/QwaYer/Cgoct-x86_32)** | **`/usr/bin/init`** — userspace supervisor |
| **[Cactsole-x86_32](https://github.com/QwaYer/Cactsole-x86_32)** | **`/usr/bin/cactsole`** and **`/usr/bin/cactsole-rescue`** (same binary, two names) |
| **[CactUserBins-x86_32](https://github.com/QwaYer/CactUserBins-x86_32)** | **`ninja -C build-meson stage`** fills **`lib/bin/`** and **`lib/sbin/`** |
| **[CactOS-x86_32](https://github.com/QwaYer/CactOS-x86_32)** | **Workspace integrator** — drives **`ninja`** across libc, shells, userbins, drivers, this packer, kernel, **CactBridge** |

---

## 📦 What goes into `cctkfs.img`

| Source under `lib/` | Path inside the archive | Purpose |
|---------------------|-------------------------|---------|
| **`*.cctk`** | **`/usr/lib/modules/<name>.cctk`** | Relocatable **PCI** driver blobs (**ET_REL**), loaded via **GDD** |
| **`*.so`** | **`/usr/lib/<name>.so`** | Shared libs (**libfs** overlay), e.g. **`clibc.so`** |
| **`ca-certificates.crt`** | **`/usr/share/ca-certificates.crt`** | Default **CA bundle** for the libc TLS client (libc looks in **`/etc/ssl/certs/ca-certificates.crt`** first and falls back to this copy) |
| **`consolefont.psf`** | **`/usr/share/consolefont.psf`** | PSF2 console font read by the kernel at boot |
| **`firmware/*`** | **`/usr/lib/firmware/*`** | **request_firmware()** blobs (e.g. **`rt2870.bin`**) |
| **`include/*`** | **`/usr/include/*`** | libc/cactsole headers |
| **`bin/*`** | **`/usr/bin/<name>`** | **init**, **cactsole**, **cgoct**, **cactsole-rescue**, plus all **CactUserBins** tools |
| **`sbin/*`** | **`/usr/sbin/<name>`** | Privileged / net helpers (**kill**, **su**, **modload**, **ping**, …) |
| **`cactpkg/*`**, **`cact-install/*`** | **`/usr/lib/<area>/*`** | Offline package repo and installer payload |

The packer sorts entries by **archive path**, then writes header + entry table + **NUL-separated** names (**8-byte** aligned) + payloads (**16-byte** aligned). See docstring in [`tools/pack_cctkfs.py`](tools/pack_cctkfs.py).

---

## 🔨 Building

**Recommended — full workspace**

From the **parent** of all sibling trees, run **`ninja -C CactOS-x86_32/build-meson stage`** (or **`… iso`**) — **[CactOS-x86_32](https://github.com/QwaYer/CactOS-x86_32)** configures this project with **`-Dcactlib_dir`**, **`-Dcactsole_bin`**, **`-Dcgoct_bin`**, **`-Duserbins_mk`**, **`-Dcactsoleinc`** and runs its **`stage`** target, which repacks **`cctkfs.img`**.

**Standalone — this repository only**

Sibling directories are auto-detected from their default relative paths:

```sh
meson setup build-meson
ninja -C build-meson stage   # gather siblings + pack cctkfs.img
ninja -C build-meson ca      # re-stage just the CA bundle
ninja -C build-meson purge   # clean
```

Override any path with a Meson option (see table below).

| Option | Meaning |
|----------|---------|
| **`-Dcactlib_dir`** | Root of **CactLib-x86_32** (must already contain **`build-meson/clibc.so`**) |
| **`-Dcactsole_bin`** | Path to built **`cactsole`** |
| **`-Dcgoct_bin`** | Path to built **`cgoct`** |
| **`-Duserbins_mk`** | Directory of **CactUserBins-x86_32** (its **`stage`** target is invoked) |
| **`-Dcactsoleinc`** | **`include/`** from **Cactsole-x86_32** |

**Prerequisites**

| Requirement | Notes |
|-------------|-------|
| **`python3`** | Runs **`pack_cctkfs.py`** |
| **`lib/*.cctk`** | **Mandatory** — install drivers first (see below) |

**Driver install** (each driver's own **`stage`** target copies into **`lib/`**):

```sh
ninja -C ../AHCI-for-Cact-x86_32/build-meson stage
ninja -C ../NVMe-for-Cact-x86_32/build-meson stage
ninja -C ../Virtio-net-for-Cact-x86_32/build-meson stage
ninja -C ../Yukon-for-Cact-x86_32/build-meson stage
```

**Pack the image**

```sh
ninja -C build-meson stage
ninja -C build-meson purge
```

---

## 📂 Repository layout

```
LocalRepoCactOS/
├── meson.build           # sibling paths arrive as -D options; stage/ca/purge targets
├── LICENSE
├── tools/
│   ├── cctkfs.h          # on-disk layout (shared idea with kernel reader)
│   ├── pack_cctkfs.py    # packs lib/ → cctkfs.img (progress bar / -v)
│   └── cact_sign.py      # appends the ECDSA P-256 trailer to a .cctk
├── lib/                  # populated by the drivers' stage targets + -D options
│   ├── *.cctk
│   ├── clibc.so
│   ├── ca-certificates.crt
│   ├── bin/
│   └── sbin/
├── src/                  # optional mirrors of driver sources
└── cctkfs.img            # generated (gitignored in practice)
```

---

## 🚀 Boot flow (runtime)

1. **GRUB** reads **`grub.cfg`**:
   ```
   multiboot2 /boot/kernel.bin
   module2   /boot/cctkfs.img cctkfs
   ```
2. Early **`init()`** (paging still off): **Multiboot2** parsing records the first module whose cmdline begins with **`cctkfs`**.
3. **`pci_modblob_load(phys, size)`** copies the module into a static **`cctkfs_stage[]`** **`.bss`** buffer **before** **`pmm_init_from_mmap()`** / **`init_heap()`** so the heap cannot overwrite bootloader pages.
4. **`pci_enumerate()`** drives **GDD** prompts for recognised devices.
5. On confirm, **`pci_load_module("/usr/lib/modules/<name>.cctk", drv)`** resolves the path inside **`cctkfs_stage`**, copies the **ET_REL** image, applies relocations, calls **`pci_driver_probe(dev)`**.
6. Userspace **`/usr/bin/init`** (**cgoct**) expects **`/usr/bin/cactsole`** (and optionally **`cactsole-rescue`**) on the overlay **`PATH`** (**`/usr/bin:/usr/sbin`**).

---

## ➕ Adding a new PCI driver

1. Create a sibling repo **`<Name>-for-Cact-x86_32`** whose **`meson.build`**:
   - compiles **`<name>_mod.c`** with **`-ffreestanding -fno-pie -m32 -mno-mmx -mno-sse -mno-sse2`** (ring-0 code must not use SSE),
   - emits **`<name>.cctk`** (relocatable object),
   - exposes a **`stage`** run_target copying it into **`-Dlocal_repo=<…>/lib/`**.
2. (Optional) mirror sources under **`src/<Name>-for-Cact/`**.
3. Teach **GDD** in **`CactKernel-x86_32/.../pci_gdd.c`** to recognise the PCI class tuple.
4. **`ninja -C <Name>-for-Cact-x86_32/build-meson stage`**, then **`ninja -C LocalRepoCactOS-x86_32/build-meson stage`** with the integrator options — or just run **`ninja -C CactOS-x86_32/build-meson drivers`**.

---

## ℹ️ Invariants

| Rule | Why |
|------|-----|
| **ABI** must match **libc** and the kernel | **`syscall.h`** (15 traps) and **`ioctl_abi.h`** are the contract — bump **CactLib**, then relink **cgoct**, **cactsole**, **CactUserBins** |
| **`/usr/bin/init` is cgoct** | The kernel’s first ELF task is **`usr/bin/init`**; keep this staging rule when swapping supervisors |

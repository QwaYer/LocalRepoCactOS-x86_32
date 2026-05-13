# 🗂️ LocalRepoCactOS

<p align="center">
  <img src="https://img.shields.io/badge/license-GPLv3-blue.svg?style=for-the-badge" alt="License: GPLv3">
  <img src="https://img.shields.io/badge/output-cctkfs.img-green.svg?style=for-the-badge" alt="cctkfs.img">
  <img src="https://img.shields.io/badge/packer-Python%203-yellow.svg?style=for-the-badge" alt="Python 3">
  <img src="https://img.shields.io/badge/boot-Multiboot2%20module-purple.svg?style=for-the-badge" alt="Multiboot2 module">
  <img src="https://img.shields.io/badge/format-cctkfs%20v1-orange.svg?style=for-the-badge" alt="cctkfs v1">
</p>

<p align="center">
  Staging tree for <strong>out-of-tree PCI drivers</strong> (<strong><code>*.cctk</code></strong>) and <strong>early userspace</strong> ELFs, packed into one <strong><code>cctkfs.img</code></strong> archive.<br>
  GRUB loads it as a <strong>Multiboot2</strong> <strong><code>module2</code></strong>; the <strong>Cact</strong> kernel copies it into RAM <strong>before paging</strong> and overlays <strong><code>/lib</code></strong>, <strong><code>/bin</code></strong>, and <strong><code>/sbin</code></strong> on top of disk-backed VFS.
</p>

---

## 📊 Stats

| | |
|---|---|
| **Output image** | **`cctkfs.img`** — flat archive, magic **`CKFS`** / version **1** ([`tools/cctkfs.h`](tools/cctkfs.h)) |
| **Packer** | **`tools/pack_cctkfs.py`** — invoked as **`python3 $(PACKER) lib/ cctkfs.img`** ([`Makefile`](Makefile)) |
| **Driver slot** | **`lib/*.cctk`** — at least **one** required or **`make`** fails with an explicit error |
| **Userspace staging** | **`lib/bin/*`** → archive **`/bin/*`** · **`lib/sbin/*`** → **`/sbin/*`** (from **CactUserBins** **`make install`**) |
| **Dynamic libc** | **`lib/libc.so`** — copied from a built **`libc.so`** when **`CACTLIB_DIR`** is passed by the integrator (see **`Makefile`**) |
| **Bootstrap ELFs** | **`init`** (copy of **cgoct**), **`cactsole`**, **`cgoct`**, **`cactsole-rescue`** (copy of **cactsole**) |

---

## 🔗 Ecosystem

| Piece | Role |
|-------|------|
| **[CactKernel-x86_32](https://github.com/QwaYer/CactKernel-x86_32)** | Parses the **`cctkfs`** module, stages **`cctkfs_stage[]`**, serves **GDD** / **pci_load_module**, **binfs** / **sbinfs** / **libfs** overlays |
| **`*-for-Cact` driver repos** | Each **`make install`** drops **`*.cctk`** into **`lib/`** here |
| **[CactLib-x86_32](https://github.com/QwaYer/CactLib-x86_32)** | Builds **`libc.so`** consumed by staged ELFs |
| **[Cgoct-x86_32](https://github.com/QwaYer/Cgoct-x86_32)** | **`/bin/init`** — userspace supervisor |
| **[Cactsole-x86_32](https://github.com/QwaYer/Cactsole-x86_32)** | **`/bin/cactsole`** and **`/bin/cactsole-rescue`** (same binary, two names) |
| **[CactUserBins-x86_32](https://github.com/QwaYer/CactUserBins-x86_32)** | **`make install`** fills **`lib/bin/`** and **`lib/sbin/`** |
| **[CactOS-x86_32](https://github.com/QwaYer/CactOS-x86_32)** | **Workspace integrator** — runs **`make`** across libc, shells, userbins, drivers, this packer, kernel, **CactBridge** |

---

## 📦 What goes into `cctkfs.img`

| Source under `lib/` | Path inside the archive | Purpose |
|---------------------|-------------------------|---------|
| **`*.cctk`** | **`/lib/<name>.cctk`** | Relocatable **PCI** driver blobs (**ET_REL**), loaded via **GDD** |
| **`*.so`** | **`/lib/<name>.so`** | Shared libs (**libfs** overlay), e.g. **`libc.so`** |
| **`bin/*`** | **`/bin/<name>`** | **init**, **cactsole**, **cgoct**, **cactsole-rescue**, plus all **CactUserBins** tools |
| **`sbin/*`** | **`/sbin/<name>`** | Privileged / net helpers (**kill**, **su**, **modload**, **ping**, …) |

The packer sorts entries by **archive path**, then writes header + entry table + **NUL-separated** names (**8-byte** aligned) + payloads (**16-byte** aligned). See docstring in [`tools/pack_cctkfs.py`](tools/pack_cctkfs.py).

---

## 🔨 Building

**Recommended — full workspace**

From the **parent** of all sibling trees, run **`make`** or **`make -C CactOS-x86_32 iso`** — **[CactOS-x86_32](https://github.com/QwaYer/CactOS-x86_32)** passes **`CACTLIB_DIR`**, **`CACTSOLE_BIN`**, **`CGOCT_BIN`**, **`USERBINS_MK`**, **`CACTSOLEINC`**, **`LR_BIN`**, **`LR_SBIN`** into this **`Makefile`** and repacks **`cctkfs.img`**.

**Standalone — this repository only**

Sibling directories are auto-detected. Just run:

```sh
make      # auto-detects all siblings + packs cctkfs.img
```

Override any path if needed (see table below).

| Variable | Meaning |
|----------|---------|
| **`CACTLIB_DIR`** | Root of **CactLib-x86_32** (must already contain **`libc.so`**) |
| **`CACTSOLE_BIN`** | Path to built **`cactsole`** |
| **`CGOCT_BIN`** | Path to built **`cgoct`** |
| **`USERBINS_MK`** | Directory of **CactUserBins-x86_32** (for **`make install`**) |
| **`CACTSOLEINC`** | **`include/`** from **Cactsole-x86_32** |
| **`LR_BIN`** / **`LR_SBIN`** | Staging dirs (e.g. **`lib/bin`** / **`lib/sbin`** under this repo) |

**Prerequisites**

| Requirement | Notes |
|-------------|-------|
| **`python3`** | Runs **`pack_cctkfs.py`** |
| **`lib/*.cctk`** | **Mandatory** — install drivers first (see table below) |

**Driver install** (auto-detects siblings by default):

```sh
make -C ../AHCI-for-Cact install
make -C ../NVMe-for-Cact install
make -C ../Virtio-net-for-Cact install
make -C ../Yukon-for-Cact install
```

**Pack the image**

```sh
make      # auto-detects all paths
make clean

---

## 📂 Repository layout

```
LocalRepoCactOS/
├── Makefile              # requires CACTLIB_DIR, paths from integrator (CactOS)
├── LICENSE
├── tools/
│   ├── cctkfs.h          # on-disk layout (shared idea with kernel reader)
│   └── pack_cctkfs.py    # packs lib/ → cctkfs.img
├── lib/                  # populated by driver installs + make targets
│   ├── *.cctk
│   ├── libc.so
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
5. On confirm, **`pci_load_module("/lib/<name>.cctk", drv)`** resolves the path inside **`cctkfs_stage`**, copies the **ET_REL** image, applies relocations, calls **`pci_driver_probe(dev)`**.
6. Userspace **`/bin/init`** (**cgoct**) expects **`/bin/cactsole`** (and optionally **`cactsole-rescue`**) on the overlay **`PATH`**.

---

## ➕ Adding a new PCI driver

1. Create a sibling repo **`<Name>-for-Cact`** whose **`Makefile`**:
   - compiles **`<name>_mod.c`** with **`-ffreestanding -fno-pie -m32`**,
   - emits **`<name>.cctk`** (relocatable object renamed),
   - implements **`make install`** copying into **`$(LOCAL_REPO)/lib/`**.
2. (Optional) mirror sources under **`src/<Name>-for-Cact/`**.
3. Teach **GDD** in **`CactKernel-x86_32/.../pci_gdd.c`** to recognise the PCI class tuple.
4. **`make -C <Name>-for-Cact KERN_ROOT=… LOCAL_REPO=… install`**, then **`make`** in **LocalRepoCactOS** with integrator variables — or run **`make`** from **CactOS-x86_32**.

---

## ℹ️ Invariants

| Rule | Why |
|------|-----|
| **Syscall numbers** must match **libc** and the kernel | **`syscall.h`** is the contract — bump **CactLib**, then relink **cgoct**, **cactsole**, **CactUserBins** |
| **`/bin/init` is cgoct** | The kernel’s first ELF task is **`bin/init`**; keep this staging rule when swapping supervisors |

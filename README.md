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
| **Dynamic libc** | **`lib/libc.so`** copied from **`../CactLib-x86_32/libc.so`** (target **`libs`**) |
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

**Prerequisites**

| Requirement | Notes |
|-------------|-------|
| **`python3`** | Runs **`pack_cctkfs.py`** |
| **`lib/*.cctk`** | **Mandatory** — install drivers first (see table below) |
| **Sibling trees** | **`../CactLib-x86_32`**, **`../Cgoct-x86_32`**, **`../Cactsole-x86_32`**, **`../CactUserBins-x86_32`** for default **`make all`** |

**Typical driver install names** (examples from this workspace layout):

| Driver | Example install |
|--------|-----------------|
| AHCI | `make -C ../AHCI-for-Cact install` |
| NVMe | `make -C ../NVMe-for-Cact install` |
| virtio-net | `make -C ../Virtio-net-for-Cact install` |
| Yukon | `make -C ../Yukon-for-Cact install` |

**Pack the image**

```sh
make            # userbins + libs + pack → cctkfs.img
make userbins   # only rebuild/install ELFs into lib/bin and lib/sbin
make libs       # refresh lib/libc.so from CactLib
make clean      # remove cctkfs.img, lib/bin/, lib/sbin/, lib/libc.so
```

**End-to-end with the kernel ISO**

```sh
make -C ../LocalRepoCactOS
make -C ../CactKernel-x86_32
```

The kernel build copies **`cctkfs.img`** into **`build/isodir/boot/`** when present; **`grub.cfg`** loads it with **`module2 /boot/cctkfs.img cctkfs`**.

---

## 📂 Repository layout

```
LocalRepoCactOS/
├── Makefile              # wires CactLib / cgoct / cactsole / CactUserBins
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
4. **`make -C <Name>-for-Cact install && make`** here, then rebuild the kernel.

---

## ℹ️ Invariants

| Rule | Why |
|------|-----|
| **Syscall numbers** must match **libc** and the kernel | **`syscall.h`** is the contract — bump **CactLib**, then relink **cgoct**, **cactsole**, **CactUserBins** |
| **`/bin/init` is cgoct** | The kernel’s first ELF task is **`bin/init`**; keep this staging rule when swapping supervisors |

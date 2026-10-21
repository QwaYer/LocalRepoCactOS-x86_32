# ==============================================================================
# LocalRepoCactOS — Meson build system (image staging + packing)
# ==============================================================================
#
#   meson setup build-meson
#   ninja -C build-meson stage       # == old `make all` (always re-runs)
#   ninja -C build-meson userbins    # only the sibling binaries
#   ninja -C build-meson daemons     # only the system daemons/network helpers
#   ninja -C build-meson libs        # only clibc.so / ld.so
#   ninja -C build-meson bin         # only /bin/{init,cgoct,cactsole,cactsole-rescue}
#   ninja -C build-meson font        # only /usr/share/consolefont.psf
#   ninja -C build-meson purge       # the Makefile's `clean`
#
# This repo owns no sources of its own: it drives the sibling repositories
# (Meson "stage" targets), stages their output into lib/, signs the kernel
# modules and packs cctkfs.img.  The project declares no languages, so no cross
# file is needed here.
#
# The pipeline is deliberately a run_target: the integrators wipe lib/bin and
# lib/sbin before calling it, so it must stage and pack on every invocation
# rather than being skipped by ninja as "up to date".  Meson reserves the target
# names install/test/clean, hence "stage" and "purge".
#
# Every shell fragment below is self-terminating (ends with "; ") so the
# run_targets can concatenate them without gluing statements together.
# ==============================================================================

project('localrepo-cactos',
  version: '1.0.0',
  meson_version: '>=1.0.0')

fs = import('fs')
bash = find_program('bash')
python3 = find_program('python3')
ninja = find_program('ninja')

src_root = meson.project_source_root()
siblings = fs.parent(src_root)

# ------------------------------------------------------------------------------
# Paths (the Makefile's CACTLIB_DIR / CACTSOLE_BIN / CGOCT_BIN / USERBINS_MK …)
# ------------------------------------------------------------------------------

lib_dir = src_root / 'lib'
bin_dir = lib_dir / 'bin'
sbin_dir = lib_dir / 'sbin'

_cactlib = get_option('cactlib_dir')
cactlib_dir = _cactlib.startswith('/') ? _cactlib : src_root / _cactlib
_sole = get_option('cactsole_bin')
cactsole_bin = _sole.startswith('/') ? _sole : src_root / _sole
_cgoct = get_option('cgoct_bin')
cgoct_bin = _cgoct.startswith('/') ? _cgoct : src_root / _cgoct
# /usr/bin/init defaults to cgoct; a check image overrides it with the runner.
_init = get_option('init_bin')
init_bin = cgoct_bin
if _init != ''
  init_bin = _init.startswith('/') ? _init : src_root / _init
endif
_userbins = get_option('userbins_mk')
userbins_mk = _userbins.startswith('/') ? _userbins : src_root / _userbins
_soleinc = get_option('cactsoleinc')
cactsoleinc = _soleinc.startswith('/') ? _soleinc : src_root / _soleinc

cactpkg_mk = siblings / 'CactPkg-x86_32'
cactinst_mk = siblings / 'Cact-install-x86_32'
xfbdev_bin = siblings / 'CactXfbdev-x86_32' / 'build-meson' / 'xfbdev'
# The console font is generated, not vendored: CactKernel owns the generator
# (and the 8x8 glyph table it draws from).
font_gen = siblings / 'CactKernel-x86_32' / 'tools' / 'gen_consolefont.py'

libc_so_src = cactlib_dir / 'build-meson' / 'clibc.so'
ld_so_src = cactlib_dir / 'build-meson' / 'ld.so'

out_img = src_root / 'cctkfs.img'
packer = src_root / 'tools' / 'pack_cctkfs.py'
signer = src_root / 'tools' / 'cact_sign.py'

# The "store" is what too big and too rare to sit in the initfs image: the
# firmware mirror, packed into localrepo.tar.zst.  The boot flow copies the
# archive to /tmp and firmextr streams members out of it on demand.  Everything
# else the image needs (userland, drivers, the cactpkg repository and the
# installer media) is packed straight into cctkfs.img.
store_dir = src_root / 'store'
store_lib = store_dir / 'usr' / 'lib'
out_tar = src_root / 'localrepo.tar.zst'
zstd = find_program('zstd')

# ------------------------------------------------------------------------------
# Sibling staging: configure on first use, then run their "stage" target
# ------------------------------------------------------------------------------

_stage_tpl = ('d="@0@"; ' +
              'if [ ! -f "$d/build-meson/build.ninja" ]; then ' +
              'meson setup "$d/build-meson" "$d" --cross-file "$d/cross/i686-cact-clang.ini" @1@; ' +
              'else meson configure "$d/build-meson" @1@ > /dev/null; fi; ' +
              ninja.full_path() + ' -C "$d/build-meson" @2@; ')

_cactlib_opt = '-Dcactlib="' + cactlib_dir + '"'
_sbin_opt = '-Dlr_sbin="' + sbin_dir + '"'
_lib_opt = '-Dlr_lib="' + lib_dir + '"'
_bin_opt = '-Dlr_bin="' + bin_dir + '"'
_soleinc_opt = '-Dcactsoleinc="' + cactsoleinc + '"'

# Daemons and network helpers: they all take cactlib + lr_sbin.
_daemon_names = ['logd', 'devd', 'netd', 'powerd', 'quirkd', 'resolved', 'seatd',
                 'audiod', 'wifid', 'dhcpd']

_script_daemons = ''
foreach d : _daemon_names
  _dir = siblings / ('Cact-' + d + '-x86_32')
  _script_daemons += (
    'if [ -f "' + _dir + '/meson.build" ]; then ' +
    _stage_tpl.format(_dir, _cactlib_opt + ' ' + _sbin_opt, 'stage') +
    'fi; '
  )
endforeach

_script_userbins = _stage_tpl.format(
  userbins_mk,
  _cactlib_opt + ' ' + _soleinc_opt + ' ' + _bin_opt + ' ' + _sbin_opt,
  'stage')

# Optional siblings (present in the image only when the directory exists).
_script_cactpkg = ''
if fs.exists(cactpkg_mk / 'meson.build')
  _script_cactpkg = _stage_tpl.format(
    cactpkg_mk, _cactlib_opt + ' ' + _sbin_opt + ' ' + _lib_opt, 'stage')
endif

# cact-install stages twice over: `stage` drops the installer binary into
# lib/sbin, and `stage-media` (which needs `grub-bundle` first, and the kernel
# already built) drops the media the installer deploys into lib/cact-install —
# boot/kernel.bin plus the GRUB stage files.  Both land in cctkfs.img, so the
# media has to be staged before the pack step below.  The whole-workspace build
# (CactOS-x86_32) runs the same three targets; running them again from here is
# what makes this repository build a complete image on its own.
_script_cactinst = ''
if fs.exists(cactinst_mk / 'meson.build')
  _script_cactinst = _stage_tpl.format(
    cactinst_mk, _cactlib_opt + ' ' + _sbin_opt + ' ' + _lib_opt,
    'stage grub-bundle stage-media')
endif

# ------------------------------------------------------------------------------
# Staging helpers
# ------------------------------------------------------------------------------

# libs: the shared CactLibc objects the image serves as /usr/lib/*.so
_script_libs = (
  'mkdir -p "' + lib_dir + '"; ' +
  'cp -f "' + libc_so_src + '" "' + lib_dir + '/clibc.so"; ' +
  'cp -f "' + ld_so_src + '" "' + lib_dir + '/ld.so"; '
)

# font: the PSF2 console font the kernel loads from /usr/share/consolefont.psf
# at boot (pack_cctkfs.py maps lib/consolefont.psf there).  It is generated
# rather than vendored so that no binary has to live in this repository; the
# generator is deterministic and emits a byte-identical file to the copy
# CactKernel carries.
_script_font = (
  'mkdir -p "' + lib_dir + '"; ' +
  'if [ -f "' + font_gen + '" ]; then ' +
  python3.full_path() + ' "' + font_gen + '" "' + lib_dir + '/consolefont.psf"; ' +
  'else echo "WARN: ' + font_gen + ' not found — the image carries no console font" >&2; fi; '
)

# bin: init and the supervisor both come from cgoct; the shell doubles as the
# rescue shell.  A check image stages cactcheck as init instead.
_script_bin = (
  'mkdir -p "' + bin_dir + '"; ' +
  'cp -f "' + init_bin + '" "' + bin_dir + '/init"; ' +
  'cp -f "' + cgoct_bin + '" "' + bin_dir + '/cgoct"; ' +
  'cp -f "' + cactsole_bin + '" "' + bin_dir + '/cactsole"; ' +
  'cp -f "' + cactsole_bin + '" "' + bin_dir + '/cactsole-rescue"; '
)

# Optional framebuffer compositor, mirrored into lib/sbin when built.
_script_xfbdev = (
  'if [ -f "' + xfbdev_bin + '" ]; then mkdir -p "' + sbin_dir + '"; ' +
  'cp -f "' + xfbdev_bin + '" "' + sbin_dir + '/xfbdev"; fi; '
)

# Trust anchors for the TLS client.  /etc lives on the (ext4-backed) boot disk,
# so the image carries the default under /usr/share: libc looks in
# /etc/ssl/certs/ca-certificates.crt first and falls back to the image copy at
# /usr/share/ca-certificates/ca-certificates.crt.  That way the anchors update
# with a package on a booted system instead of needing a kernel or image rebuild.
_script_ca = (
  'for src in /etc/ssl/certs/ca-certificates.crt ' +
             '/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem ' +
             '/etc/ssl/cert.pem; do ' +
  'if [ -f "$src" ]; then cp -fL "$src" "' + lib_dir + '/ca-certificates.crt"; ' +
  'echo "staged CA bundle: $src"; break; fi; done; '
)

# Firmware.  The whole mirror goes into the store — that is what the localrepo
# archive carries — copied as-is: the mirror's blobs are already compressed
# (*.zst), so re-compressing the set buys nothing, and request_firmware() tries
# "<name>.zst" before "<name>" anyway.  `cp -al` hard-links the tree instead of
# duplicating 500+ MiB on the same filesystem; firmextr streams a single member
# out on demand and the kernel then sees it under /usr/lib/firmware via the VFS.
_fw_dir = siblings / 'Firmware-for-Cact-x86' / 'lib' / 'firmware'

_script_fw = (
  'rm -rf "' + store_dir + '/usr"; mkdir -p "' + store_lib + '"; ' +
  'if [ -d "' + _fw_dir + '" ]; then ' +
  'cp -al "' + _fw_dir + '" "' + store_lib + '/firmware"; ' +
  'else echo "WARN: firmware mirror ' + _fw_dir + ' not found — localrepo carries none" >&2; fi; '
)

# The store holds the firmware mirror and nothing else (the step above wipes it
# and re-populates it), and firmware must never be packed into cctkfs.img — so
# a copy under lib/, from an older build or a stray hand copy, is dropped here.
_script_store = (
  'rm -rf "' + lib_dir + '/firmware"; '
)

# Pack the store — the firmware mirror — into the archive the boot flow streams
# from (ustar so firmextr's reader can parse it).  The bash pipeline reports
# only zstd's status, so a failing `tar` needs pipefail; and a pack that dies
# half-way still leaves a file that looks like an archive, so the result is read
# back and its member list compared with the store's.  An archive that fails
# here would ride on the ISO as the `localrepo` module, boot fine, and only
# surface later as an empty /tmp copy the drivers cannot get firmware out of.
# The level is deliberately low: the mirror's blobs are already *.zst (and the
# raw remainder is ucode/GPU data), so -19 would spend minutes of CPU on the
# first full pass over a 500+ MiB tree for a few MiB of ISO.
_script_tar = (
  'set -o pipefail; ' +
  'if [ ! -d "' + store_dir + '/usr" ]; then ' +
  'echo "localrepo: store/usr is missing — run \`ninja stage\` first" >&2; exit 1; fi; ' +
  'want=$(tar --format=ustar -C "' + store_dir + '" -cf - usr | tar -tf -); ' +
  'rm -f "' + out_tar + '"; ' +
  'tar --format=ustar -C "' + store_dir + '" -cf - usr | ' +
  zstd.full_path() + ' -3 -q -o "' + out_tar + '" -; ' +
  'if ! got=$(' + zstd.full_path() + ' -dc "' + out_tar + '" | tar -tf -); then ' +
  'echo "localrepo: the packed archive is not readable — dropping ' + out_tar + '" >&2; ' +
  'rm -f "' + out_tar + '"; exit 1; fi; ' +
  'if [ "$want" != "$got" ]; then ' +
  'echo "localrepo: the packed archive does not match the store — dropping ' + out_tar + '" >&2; ' +
  'rm -f "' + out_tar + '"; exit 1; fi; ' +
  'echo "localrepo: wrote localrepo.tar.zst"; '
)

# sign + pack: the Makefile's $(OUT_IMG) rule.
_script_pack = (
  'cctk=$(ls "' + lib_dir + '"/*.cctk 2>/dev/null || true); ' +
  'if [ -z "$cctk" ]; then ' +
  'echo "ERROR: no ' + lib_dir + '/*.cctk — install kernel modules first" >&2; exit 1; fi; ' +
  'for f in $cctk; do ' + python3.full_path() + ' "' + signer + '" "$f"; done; ' +
  python3.full_path() + ' "' + packer + '" "' + lib_dir + '" "' + out_img + '"; '
)

# Base-system packages: wrap every staged tool in lib/{bin,sbin} as a .cpkg in
# the offline repository (versioned with the CactOS release) so cactpkg can list
# and install the base system too.  Must run after _script_bin, once all of the
# userland is staged; writes into the repo dir _script_cactpkg already filled.
_cactos_version = '2.0.0'
_cpkg_tool = cactpkg_mk / 'tools' / 'cpkg.py'
_script_sysrepo = (
  'if [ -f "' + _cpkg_tool + '" ] && [ -d "' + lib_dir + '/cactpkg/repo" ]; then ' +
  python3.full_path() + ' "' + _cpkg_tool + '" sysrepo "' + lib_dir + '" "' +
  lib_dir + '/cactpkg/repo" --version ' + _cactos_version + '; fi; '
)

run_target('libs',
  command: [bash, '-c', 'set -e; ' + _script_libs])

run_target('bin',
  command: [bash, '-c', 'set -e; ' + _script_bin])

run_target('font',
  command: [bash, '-c', 'set -e; ' + _script_font])

run_target('daemons',
  command: [bash, '-c', 'set -e; ' + _script_daemons])

run_target('userbins',
  command: [bash, '-c', 'set -e; ' + _script_daemons +
            _script_userbins + _script_cactpkg + _script_cactinst +
            _script_font + _script_fw + _script_store])

# The Makefile's `all`: stage everything, then sign + pack cctkfs.img — the
# userland, the drivers, the cactpkg repository and the installer media.  Only
# the store (the firmware mirror) stays out of it; the `localrepo` target packs
# that into localrepo.tar.zst.
run_target('stage',
  command: [bash, '-c', 'set -e; ' + _script_daemons + _script_userbins +
            _script_cactpkg + _script_cactinst +
            _script_libs + _script_bin + _script_font + _script_xfbdev +
            _script_sysrepo + _script_ca + _script_fw + _script_store +
            _script_pack])

# Build localrepo.tar.zst from the store.  Run after `stage` (it uses whatever
# the store holds, so it only has to re-pack when the store changed).
run_target('localrepo',
  command: [bash, '-c', 'set -e; ' + _script_tar])

# Trust anchors on their own, for when only the bundle changed.
run_target('ca',
  command: [bash, '-c', 'set -e; ' + _script_ca])

# Meson reserves "clean" (as it does "install"/"test"), hence "purge".
run_target('purge',
  command: [bash, '-c', 'set -e; ' +
            'rm -f "' + out_img + '" "' + out_tar + '"; ' +
            'rm -rf "' + store_dir + '" "' + bin_dir + '" "' + sbin_dir + '"; ' +
            'rm -f "' + lib_dir + '/clibc.so" "' + lib_dir + '/ld.so"; '])

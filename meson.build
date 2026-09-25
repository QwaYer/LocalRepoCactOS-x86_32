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
_userbins = get_option('userbins_mk')
userbins_mk = _userbins.startswith('/') ? _userbins : src_root / _userbins
_soleinc = get_option('cactsoleinc')
cactsoleinc = _soleinc.startswith('/') ? _soleinc : src_root / _soleinc

cactpkg_mk = siblings / 'CactPkg-x86_32'
cactinst_mk = siblings / 'Cact-install-x86_32'
xfbdev_bin = siblings / 'CactXfbdev-x86_32' / 'build-meson' / 'xfbdev'

libc_so_src = cactlib_dir / 'build-meson' / 'clibc.so'
ld_so_src = cactlib_dir / 'build-meson' / 'ld.so'

out_img = src_root / 'cctkfs.img'
packer = src_root / 'tools' / 'pack_cctkfs.py'
signer = src_root / 'tools' / 'cact_sign.py'

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
                 'audiod', 'wifid', 'networkd', 'dhcpd']

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

_script_cactinst = ''
if fs.exists(cactinst_mk / 'meson.build')
  _script_cactinst = _stage_tpl.format(
    cactinst_mk, _cactlib_opt + ' ' + _sbin_opt, 'stage')
endif

# ------------------------------------------------------------------------------
# Staging helpers
# ------------------------------------------------------------------------------

# libs: the shared CactLibc objects the image serves as /lib/*.so
_script_libs = (
  'mkdir -p "' + lib_dir + '"; ' +
  'cp -f "' + libc_so_src + '" "' + lib_dir + '/clibc.so"; ' +
  'cp -f "' + ld_so_src + '" "' + lib_dir + '/ld.so"; '
)

# bin: init and the supervisor both come from cgoct; the shell doubles as the
# rescue shell.
_script_bin = (
  'mkdir -p "' + bin_dir + '"; ' +
  'cp -f "' + cgoct_bin + '" "' + bin_dir + '/init"; ' +
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
# so the image carries the default under /lib: libc looks in
# /etc/ca-certificates.crt first and falls back to /lib/ca-certificates.crt.
# That way the anchors update with a package on a booted system instead of
# needing a kernel or image rebuild.
_script_ca = (
  'for src in /etc/ssl/certs/ca-certificates.crt ' +
             '/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem ' +
             '/etc/ssl/cert.pem; do ' +
  'if [ -f "$src" ]; then cp -fL "$src" "' + lib_dir + '/ca-certificates.crt"; ' +
  'echo "staged CA bundle: $src"; break; fi; done; '
)

# sign + pack: the Makefile's $(OUT_IMG) rule.
_script_pack = (
  'cctk=$(ls "' + lib_dir + '"/*.cctk 2>/dev/null || true); ' +
  'if [ -z "$cctk" ]; then ' +
  'echo "ERROR: no ' + lib_dir + '/*.cctk — install kernel modules first" >&2; exit 1; fi; ' +
  'for f in $cctk; do ' + python3.full_path() + ' "' + signer + '" "$f"; done; ' +
  python3.full_path() + ' "' + packer + '" "' + lib_dir + '" "' + out_img + '"; '
)

run_target('libs',
  command: [bash, '-c', 'set -e; ' + _script_libs])

run_target('bin',
  command: [bash, '-c', 'set -e; ' + _script_bin])

run_target('daemons',
  command: [bash, '-c', 'set -e; ' + _script_daemons])

run_target('userbins',
  command: [bash, '-c', 'set -e; ' + _script_daemons +
            _script_userbins + _script_cactpkg + _script_cactinst])

# The Makefile's `all`: everything, then sign + pack.
run_target('stage',
  command: [bash, '-c', 'set -e; ' + _script_daemons + _script_userbins +
            _script_cactpkg + _script_cactinst +
            _script_libs + _script_bin + _script_xfbdev + _script_ca +
            _script_pack])

# Trust anchors on their own, for when only the bundle changed.
run_target('ca',
  command: [bash, '-c', 'set -e; ' + _script_ca])

# Meson reserves "clean" (as it does "install"/"test"), hence "purge".
run_target('purge',
  command: [bash, '-c', 'set -e; ' +
            'rm -f "' + out_img + '"; ' +
            'rm -rf "' + bin_dir + '" "' + sbin_dir + '"; ' +
            'rm -f "' + lib_dir + '/clibc.so" "' + lib_dir + '/ld.so"; '])

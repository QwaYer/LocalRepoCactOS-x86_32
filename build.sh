#!/usr/bin/env bash
# build.sh — one-shot build pipeline for LocalRepoCactOS.
#
# Steps:
#   1. discover sibling driver repos (../<Name>-for-Cact)
#   2. `make -C <repo> install` for each — drops <name>.cctk into ./lib/
#   3. `make` here — user ELF → lib/bin/, pack lib/*.cctk + lib/bin/* → cctkfs.img
#
# Полный цикл под QEMU: ../build-cact-qemu.sh (ядро + пустой nvme.img + ISO).
#
# Env knobs:
#   KERN_ROOT  path to CactKernel sources           (default ../CactKernel-x86_32)
#   REPOS      space-separated list of repo names   (default: AHCI NVMe Virtio-net)
#   JOBS       parallel make jobs                   (default: nproc)
#   CLEAN=1    run `make clean` in each repo before build
#   SKIP_PACK=1 skip the final cctkfs.img pack step
#
# Usage:
#   ./build.sh                    # build everything, repack image
#   CLEAN=1 ./build.sh            # clean rebuild
#   REPOS="NVMe" ./build.sh       # only one driver
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$REPO_ROOT")"

KERN_ROOT="${KERN_ROOT:-$PARENT_DIR/CactKernel-x86_32}"
REPOS="${REPOS:-AHCI NVMe Virtio-net}"
JOBS="${JOBS:-$(nproc 2>/dev/null || echo 1)}"

c_red()    { printf '\033[1;31m%s\033[0m\n' "$*"; }
c_green()  { printf '\033[1;32m%s\033[0m\n' "$*"; }
c_yellow() { printf '\033[1;33m%s\033[0m\n' "$*"; }
c_cyan()   { printf '\033[1;36m%s\033[0m\n' "$*"; }

log()   { c_cyan   "[build.sh] $*"; }
ok()    { c_green  "[build.sh] $*"; }
warn()  { c_yellow "[build.sh] $*"; }
fatal() { c_red    "[build.sh] $*"; exit 1; }

[[ -d "$KERN_ROOT" ]] || fatal "KERN_ROOT not found: $KERN_ROOT"
[[ -x "$(command -v python3)" ]] || fatal "python3 is required"
[[ -x "$(command -v make)" ]]    || fatal "make is required"
[[ -x "$(command -v gcc)" ]]     || fatal "gcc is required"

mkdir -p "$REPO_ROOT/lib"

log "kernel sources : $KERN_ROOT"
log "driver repos   : $REPOS"
log "parallel jobs  : $JOBS"

failed=()
for repo in $REPOS; do
    dir="$PARENT_DIR/${repo}-for-Cact"
    if [[ ! -d "$dir" ]]; then
        warn "skip ${repo}: directory not found ($dir)"
        failed+=("${repo} (missing)")
        continue
    fi
    log "→ ${repo}: building in $dir"
    if [[ "${CLEAN:-0}" == "1" ]]; then
        make -C "$dir" clean >/dev/null 2>&1 || true
    fi
    if ! make -C "$dir" -j"$JOBS" KERN_ROOT="$KERN_ROOT" \
                                  LOCAL_REPO="$REPO_ROOT" install; then
        c_red "[build.sh] ${repo}: build/install FAILED"
        failed+=("${repo}")
        continue
    fi
    ok "${repo}: installed"
done

# Re-pack the cctkfs image (always, even if some modules failed — the
# image then reflects whatever subset succeeded).
if [[ "${SKIP_PACK:-0}" != "1" ]]; then
    log "packing cctkfs.img from lib/"
    make -C "$REPO_ROOT" all >/dev/null
    if [[ -f "$REPO_ROOT/cctkfs.img" ]]; then
        size=$(stat -c%s "$REPO_ROOT/cctkfs.img" 2>/dev/null || wc -c < "$REPO_ROOT/cctkfs.img")
        ok "cctkfs.img ready ($size bytes)"
    else
        fatal "cctkfs.img was not produced"
    fi
fi

echo
c_cyan "==================== summary ===================="
ls -lh "$REPO_ROOT/lib/" 2>/dev/null | tail -n +2
echo
if [[ ${#failed[@]} -gt 0 ]]; then
    c_red "failed: ${failed[*]}"
    exit 1
fi
ok "all drivers built; image lives at $REPO_ROOT/cctkfs.img"
ok "next:  cd $KERN_ROOT && make"

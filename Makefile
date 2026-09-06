CACTLIB_DIR ?= $(abspath ../CactLibc-x86_32)
CACTSOLE_BIN ?= $(abspath ../Cactsole-x86_32/cactsole)
CGOCT_BIN ?= $(abspath ../Cgoct-x86_32/cgoct)
XFBDEV_BIN ?= $(abspath ../CactXfbdev-x86_32/build/xfbdev)
USERBINS_MK ?= $(abspath ../CactUserBins-x86_32)
CACTSOLEINC ?= $(abspath ../Cactsole-x86_32/include)
LR_BIN ?= $(abspath lib/bin)
LR_SBIN ?= $(abspath lib/sbin)

_ACTIVE := $(filter-out clean,$(or $(MAKECMDGOALS),all))

ifneq ($(_ACTIVE),)
ifndef CACTLIB_DIR
$(error Set CACTLIB_DIR to the libc project root (see CactOS-x86_32 Makefile))
endif
ifndef CACTSOLE_BIN
$(error Set CACTSOLE_BIN to the path of the built cactsole binary)
endif
ifndef CGOCT_BIN
$(error Set CGOCT_BIN to the path of the built cgoct binary)
endif
ifndef USERBINS_MK
$(error Set USERBINS_MK to the CactUserBins-x86_32 directory)
endif
ifndef CACTSOLEINC
$(error Set CACTSOLEINC to the cactsole include directory)
endif
ifndef LR_BIN
$(error Set LR_BIN to the staging bin directory)
endif
ifndef LR_SBIN
$(error Set LR_SBIN to the staging sbin directory)
endif
endif

LIB_DIR     := lib
BIN_STAGING := $(LIB_DIR)/bin
OUT_IMG     := cctkfs.img
PACKER      := tools/pack_cctkfs.py
SIGNER      := tools/cact_sign.py

LIBC_SO_SRC  := $(CACTLIB_DIR)/clibc.so
LD_SO_SRC    := $(CACTLIB_DIR)/ld.so

CCTK_FILES := $(wildcard $(LIB_DIR)/*.cctk)
BIN_ELFS   := $(BIN_STAGING)/init $(BIN_STAGING)/cactsole $(BIN_STAGING)/cgoct \
              $(BIN_STAGING)/cactsole-rescue
# xfbdev (framebuffer compositor) is optional — only added if a built binary exists.
SBIN_ELFS  :=
ifneq ($(wildcard $(XFBDEV_BIN)),)
SBIN_ELFS  := $(LR_SBIN)/xfbdev
endif
LIB_SOS    := $(LIB_DIR)/clibc.so $(LIB_DIR)/ld.so

.PHONY: all clean userbins libs cactuserbins xfbdev cactpkg networkd dhcpd

all: $(OUT_IMG)

cactuserbins:
	$(MAKE) -C $(USERBINS_MK) install \
		CACTLIB="$(CACTLIB_DIR)" \
		CACTSOLEINC="$(CACTSOLEINC)" \
		LR_BIN="$(LR_BIN)" \
		LR_SBIN="$(LR_SBIN)"

# CactPkg (пакетный менеджер) — опциональный sibling: бинарь в /sbin,
# офлайн-репозиторий в /lib/cactpkg/repo. Присутствует в образе, только
# если каталог ../CactPkg-x86_32 существует.
CACTPKG_MK ?= $(abspath ../CactPkg-x86_32)
ifneq ($(wildcard $(CACTPKG_MK)/Makefile),)
CACTPKG_TARGET := cactpkg
endif

# Сетевые демоны (networkd/dhcpd) — опциональные sibling-репозитории.
# В образ попадают, только если каталог с Makefile существует.
NETWORKD_MK ?= $(abspath ../Cact-networkd-x86_32)
ifneq ($(wildcard $(NETWORKD_MK)/Makefile),)
NETWORKD_TARGET := networkd
endif
DHCPD_MK ?= $(abspath ../Cact-dhcpd-x86_32)
ifneq ($(wildcard $(DHCPD_MK)/Makefile),)
DHCPD_TARGET := dhcpd
endif

# Системные демоны (logd/devd/netd/powerd/quirkd/resolved/seatd/audiod/wifid) —
# опциональные sibling-репозитории Cact-<name>-x86_32. Каждый ставит свой
# бинарь через `make install` в $(LR_SBIN). Демоны поднимаются супервизором
# cgoct (см. Cgoct-x86_32, ключ services в /etc/cgoct.conf).
CACT_DAEMONS  := logd devd netd powerd quirkd resolved seatd audiod wifid
DAEMON_NAMES  := $(foreach d,$(CACT_DAEMONS),$(if $(wildcard ../Cact-$(d)-x86_32/Makefile),daemon-$(d)))

cactpkg:
	@echo "  CACTPKG  $(CACTPKG_MK)"
	$(MAKE) -s -C $(CACTPKG_MK) install \
		CACTLIB="$(CACTLIB_DIR)" \
		LR_SBIN="$(LR_SBIN)" \
		LR_LIB="$(abspath $(LIB_DIR))"

networkd:
	@echo "  NETWORKD $(NETWORKD_MK)"
	$(MAKE) -s -C $(NETWORKD_MK) install \
		CACTLIB="$(CACTLIB_DIR)" \
		LR_SBIN="$(LR_SBIN)"

dhcpd:
	@echo "  DHCPD    $(DHCPD_MK)"
	$(MAKE) -s -C $(DHCPD_MK) install \
		CACTLIB="$(CACTLIB_DIR)" \
		LR_SBIN="$(LR_SBIN)"

daemon-%:
	@echo "  DAEMON   ../Cact-$*-x86_32"
	$(MAKE) -s -C ../Cact-$*-x86_32 install \
		CACTLIB="$(CACTLIB_DIR)" \
		LR_SBIN="$(LR_SBIN)"

userbins: cactuserbins $(CACTPKG_TARGET) $(NETWORKD_TARGET) $(DHCPD_TARGET) $(DAEMON_NAMES) $(BIN_ELFS) $(SBIN_ELFS)

$(LR_SBIN)/xfbdev: $(XFBDEV_BIN)
	@mkdir -p $(LR_SBIN)
	cp -f $< $@

libs: $(LIB_SOS)

$(LIB_DIR)/clibc.so: $(LIBC_SO_SRC)
	@mkdir -p $(LIB_DIR)
	cp -f $< $@

$(LIB_DIR)/ld.so: $(LD_SO_SRC)
	@mkdir -p $(LIB_DIR)
	cp -f $< $@

$(BIN_STAGING)/init: $(CGOCT_BIN)
	@mkdir -p $(BIN_STAGING)
	cp -f $< $@

$(BIN_STAGING)/cactsole: $(CACTSOLE_BIN)
	@mkdir -p $(BIN_STAGING)
	cp -f $< $@

$(BIN_STAGING)/cgoct: $(CGOCT_BIN)
	@mkdir -p $(BIN_STAGING)
	cp -f $< $@

$(BIN_STAGING)/cactsole-rescue: $(CACTSOLE_BIN)
	@mkdir -p $(BIN_STAGING)
	cp -f $< $@

$(OUT_IMG): $(PACKER) $(SIGNER) userbins libs $(CCTK_FILES)
	@if [ -z "$(CCTK_FILES)" ]; then \
		echo "ERROR: no $(LIB_DIR)/*.cctk — install kernel modules first"; \
		exit 1; \
	fi
	for f in $(CCTK_FILES); do python3 $(SIGNER) $$f; done
	python3 $(PACKER) $(LIB_DIR) $@

clean:
	rm -f $(OUT_IMG)
	rm -rf $(BIN_STAGING) $(LIB_DIR)/sbin
	rm -f $(LIB_SOS)

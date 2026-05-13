CACTLIB_DIR ?= $(abspath ../CactLib-x86_32)
CACTSOLE_BIN ?= $(abspath ../Cactsole-x86_32/cactsole)
CGOCT_BIN ?= $(abspath ../Cgoct-x86_32/cgoct)
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

LIBC_SO_SRC  := $(CACTLIB_DIR)/libc.so

CCTK_FILES := $(wildcard $(LIB_DIR)/*.cctk)
BIN_ELFS   := $(BIN_STAGING)/init $(BIN_STAGING)/cactsole $(BIN_STAGING)/cgoct \
              $(BIN_STAGING)/cactsole-rescue
LIB_SOS    := $(LIB_DIR)/libc.so

.PHONY: all clean userbins libs cactuserbins

all: $(OUT_IMG)

cactuserbins:
	$(MAKE) -C $(USERBINS_MK) install \
		CACTLIB="$(CACTLIB_DIR)" \
		CACTSOLEINC="$(CACTSOLEINC)" \
		LR_BIN="$(LR_BIN)" \
		LR_SBIN="$(LR_SBIN)"

userbins: cactuserbins $(BIN_ELFS)

all: $(OUT_IMG)

libs: $(LIB_SOS)

$(LIB_DIR)/libc.so: $(LIBC_SO_SRC)
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

$(OUT_IMG): $(PACKER) userbins libs $(CCTK_FILES)
	@if [ -z "$(CCTK_FILES)" ]; then \
		echo "ERROR: no $(LIB_DIR)/*.cctk — install kernel modules first"; \
		exit 1; \
	fi
	python3 $(PACKER) $(LIB_DIR) $@

clean:
	rm -f $(OUT_IMG)
	rm -rf $(BIN_STAGING) $(LIB_DIR)/sbin
	rm -f $(LIB_SOS)

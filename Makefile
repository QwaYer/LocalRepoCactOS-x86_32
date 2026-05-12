# LocalRepoCactOS — pack lib/*.cctk and lib/bin/* ELF into cctkfs.img (GRUB
# multiboot2 module). /bin entries are used for early userspace bootstrap.

LIB_DIR     := lib
BIN_STAGING := $(LIB_DIR)/bin
OUT_IMG     := cctkfs.img
PACKER      := tools/pack_cctkfs.py
PARENT      := ..

CACTSOLE_BIN := $(PARENT)/Cactsole-x86_32/cactsole
CGOCT_BIN    := $(PARENT)/Cgoct-x86_32/cgoct
USERBINS_MK  := $(PARENT)/CactUserBins-x86_32
CACTLIB_DIR  := $(PARENT)/CactLib-x86_32
LIBC_SO_SRC  := $(CACTLIB_DIR)/libc.so

CCTK_FILES := $(wildcard $(LIB_DIR)/*.cctk)
# Ядро ищет /bin/init; cgoct ожидает /bin/cactsole и /bin/cactsole-rescue.
BIN_ELFS   := $(BIN_STAGING)/init $(BIN_STAGING)/cactsole $(BIN_STAGING)/cgoct \
              $(BIN_STAGING)/cactsole-rescue
# Разделяемые библиотеки — попадают в cctkfs:/lib/<name>.so и обслуживаются libfs.
LIB_SOS    := $(LIB_DIR)/libc.so

.PHONY: all clean userbins libs cactuserbins

cactuserbins:
	$(MAKE) -C $(USERBINS_MK) install

userbins: cactuserbins $(BIN_ELFS)

all: $(OUT_IMG)

libs: $(LIB_SOS)

$(LIB_DIR)/libc.so: $(LIBC_SO_SRC)
	@mkdir -p $(LIB_DIR)
	cp -f $< $@

$(LIBC_SO_SRC):
	$(MAKE) -C $(CACTLIB_DIR)

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

$(CACTSOLE_BIN):
	$(MAKE) -C $(PARENT)/Cactsole-x86_32

$(CGOCT_BIN):
	$(MAKE) -C $(PARENT)/Cgoct-x86_32

$(OUT_IMG): $(PACKER) userbins libs $(CCTK_FILES)
	@if [ -z "$(CCTK_FILES)" ]; then \
		echo "ERROR: no $(LIB_DIR)/*.cctk — run 'make install' in each *-for-Cact driver repo"; \
		exit 1; \
	fi
	python3 $(PACKER) $(LIB_DIR) $@

clean:
	rm -f $(OUT_IMG)
	rm -rf $(BIN_STAGING) $(LIB_DIR)/sbin
	rm -f $(LIB_SOS)

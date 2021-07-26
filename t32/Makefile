# To compile: T32_LIB_DIR="[t32_lib_src_dir]" make
.PHONY: all clean

MAIN_C ?= main.c
CC := gcc
CFLAGS := -std=gnu11 -Wall -Wextra
INCLUDE := -I $(T32_LIB_DIR)


all: trunner

hlinknet.o: $(T32_LIB_DIR)/hlinknet.c
	$(CC) $(INCLUDE) -c $< -o $@

hremote.o: $(T32_LIB_DIR)/hremote.c
	$(CC) $(INCLUDE) -c $< -o $@

main.o: $(MAIN_C)
	$(CC) $(INCLUDE) $(CFLAGS) -c $< -o $@

clean:
	$(RM) main.o
	$(RM) hlinknet.o
	$(RM) hremote.o
	$(RM) trunner

trunner: main.o hremote.o hlinknet.o
	gcc -o $@ $^

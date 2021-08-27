CC=hexagon-unknown-linux-musl-clang
CFLAGS=-mv67 -O2 -mhvx -Wall -g
LDFLAGS=-static -nostdlib -e start
ASM=-S

%.o : %.s
	$(CC) -c $(CFLAGS) $< -o $@

bn_llil_test: first.o bn_llil_test_app.o
	$(CC) $^ -o $@ $(LDFLAGS)


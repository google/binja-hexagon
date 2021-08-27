CC=hexagon-unknown-linux-musl-clang
CFLAGS=-mv67 -O2 -mhvx -Wall -g

%.o : %.s
	$(CC) -c $(CFLAGS) $< -o $@

bn_hlil_test: bn_hlil_test_app.o
	$(CC) $^ -o $@ $(LDFLAGS)


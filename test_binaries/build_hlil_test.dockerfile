FROM registry.gitlab.com/qemu-project/qemu/qemu/debian-hexagon-cross:latest as build

RUN mkdir /build
COPY build_hlil_test.makefile /build/Makefile
COPY bn_hlil_test_app.c /build
RUN make -C /build bn_hlil_test

CMD sleep 1

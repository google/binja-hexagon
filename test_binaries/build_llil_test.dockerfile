FROM registry.gitlab.com/qemu-project/qemu/qemu/debian-hexagon-cross:latest as build

RUN mkdir /build
COPY build_llil_test.makefile /build/Makefile
COPY bn_llil_test_app.s /build
COPY first.s /build
RUN make -C /build bn_llil_test

CMD sleep 1

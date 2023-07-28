FROM fedora:36 AS stage1

MAINTAINER Indraneel M <Indraneel.Mukherjee@wdc.com>

ARG FIO_VERSION=fio-3.30

COPY blkzoned.h /root/blkzoned.h

RUN dnf install -y libaio git && \
	dnf install -y \
	libaio-devel \
	zlib-devel \
	make \
	automake \
	gcc \
	gcc-c++ \
	kernel-headers \
	coreutils && \
	dnf group install -y "C Development Tools and Libraries" "Development Tools" && \
	mv /root/blkzoned.h /usr/include/linux/blkzoned.h && \
	git clone https://github.com/axboe/fio.git -b "$FIO_VERSION" /root/fio && \
	cd /root/fio && \
	./configure && \
	make -j "$(nproc)" && \
	make install

FROM stage1 AS stage2

RUN cd /root && \
#	dnf install -y vim bash && \
	git clone https://github.com/spdk/spdk.git -b v22.09 /root/spdk && \
	cd spdk && \
	git submodule update --init && \
	./scripts/pkgdep.sh --all && \
	./configure --with-fio=/root/fio --with-uring && \
	make -j4
COPY bdev_zoned_uring.json /root/spdk
COPY zbdbench_seccomp.json /root/spdk

FROM stage2 AS stage3

COPY spdk_launch.sh /root/spdk/
RUN chmod +x /root/spdk/spdk_launch.sh

FROM stage3
RUN dnf clean all && \
cd /root/spdk

ENTRYPOINT ["/root/spdk/spdk_launch.sh"]

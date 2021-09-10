FROM alpine:3.13
MAINTAINER Matias Bjørling <matias.bjorling@wdc.com>

ARG VERSION=fio-3.28

COPY blkzoned.h /root/blkzoned.h

RUN apk --no-cache add libaio git && \
    apk --no-cache add --virtual build-dependencies \
        libaio-dev \
        zlib-dev \
        build-base \
        linux-headers \
        coreutils && \
    mv /root/blkzoned.h /usr/include/linux/blkzoned.h && \
    git clone https://github.com/axboe/fio.git -b "$VERSION" /root/fio && \
    cd /root/fio && \
    ./configure && \
    make -j "$(nproc)" && \
    make install && \
    rm -rf /root/fio && \
    apk del build-dependencies

ENTRYPOINT ["fio"]

FROM alpine:3.15.4 as builder
MAINTAINER Matias Bjørling <matias.bjorling@wdc.com>

COPY blkzoned.h /root/blkzoned.h

# Installs libzbd and rocksdb's db_bench

RUN apk --no-cache add libaio snappy gflags && \
    apk --no-cache add --virtual build-dependencies \
        git libaio-dev \
        zlib-dev \
        build-base \
        linux-headers \
        snappy-dev \
        gflags-dev \
        autoconf \
        autoconf-archive \
        automake \
        libtool \
        cmake \
        coreutils && \
    mv /root/blkzoned.h /usr/include/linux/blkzoned.h && \
    git clone https://github.com/westerndigitalcorporation/libzbd.git -b v2.0.3 /root/libzbd && \
    cd /root/libzbd && \
    ./autogen.sh && \
    ./configure && \
    make && \
    make install && \
    cd /root && \
    rm -rf /root/libzbd && \
    git clone https://github.com/facebook/rocksdb.git -b v7.2.2 /root/rocksdb && \
    cd /root/rocksdb && \
    git clone https://github.com/westerndigitalcorporation/zenfs.git -b v2.1.0 /root/rocksdb/plugin/zenfs && \
    DEBUG_LEVEL=0 ROCKSDB_PLUGINS=zenfs make -j "$(nproc)" db_bench install && \
    cp db_bench /usr/local/bin && \
    cd plugin/zenfs/util && \
    make && \
    cp zenfs /usr/local/bin && \
    cd /root && \
    rm -rf /root/rocksdb && \
    apk del build-dependencies

ENTRYPOINT ["db_bench"]

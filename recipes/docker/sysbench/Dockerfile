FROM docker.io/ubuntu:20.04 AS builder

RUN apt-get update \
    && \
    DEBIAN_FRONTEND=noninteractive \
    DEBCONF_NONINTERACTIVE_SEEN=true \
    apt-get install --yes --quiet=2 \
    build-essential \
    git \
    pkg-config \
    cmake \
    autoconf \
    autoconf-archive \
    automake \
    libtool \
    zlib1g-dev \
    valgrind \
    libssl-dev \
    libssl1.1 \
    libncurses-dev \
    libncurses6 \
    libncursesw6 \
    libldap2-dev \
    libldap-2.4-2 \
    libreadline-dev \
    libcurl4-openssl-dev \
    libgflags-dev \
    libgflags2.2 \
    libcurl4 \
    uuid-dev \
    libblkid-dev \
    liblzo2-dev \
    libzstd-dev \
    zlib1g \
    e2fsprogs \
    libgcrypt-dev \
    libsodium-dev \
    libkcapi-dev \
    libudev-dev \
    e2fslibs-dev \
    linux-libc-dev \
    asciidoc \
    xmlto \
    bison \
    libreadline8 \
    perl \
    python3-dev \
    python3-pip \
    python-is-python3 \
    python3-sphinx \
    gnupg2 \
    lsb-release \
    wget \
    libaio-dev \
    xfsprogs \
    && apt-get clean

COPY blkzoned.h /usr/include/linux/blkzoned.h

# Install btrfs-progs
RUN git clone https://github.com/kdave/btrfs-progs.git \
    && cd btrfs-progs \
    && git checkout v5.18 \
    && ./autogen.sh \
    && ./configure --disable-documentation --enable-zoned \
    && make \
    && make install

# Following instructions form https://github.com/percona/percona-server/blob/8.0/doc/source/myrocks/zenfs.rst
# and choose the repository from https://docs.percona.com/percona-software-repositories/repository-location.html
RUN wget https://repo.percona.com/apt/percona-release_latest.$(lsb_release -sc)_all.deb \
    && apt-get install --yes --quiet=2 \
    ./percona-release_latest.*_all.deb \
    && percona-release setup ps80
# For unreleased percona server use the following instead:
#    && percona-release enable ps-80 testing

# To find out the selections that need to be made for an unattended
# percona-server-server installation run
# `debconf-show --listowners | grep percona | xargs debconf-show`
# on a system where percona-server-server was previously installed.
RUN ["/bin/bash", "-c", "debconf-set-selections <<< 'percona-server-server percona-server-server/root-pass password pw'"]
RUN ["/bin/bash", "-c", "debconf-set-selections <<< 'percona-server-server percona-server-server/re-root-pass password pw'"]
RUN ["/bin/bash", "-c", "debconf-set-selections <<< 'percona-server-server percona-server-server/default-auth-override select Use Strong Password Encryption (RECOMMENDED)'"]

RUN apt-get update \
    && apt-get install --yes --quiet=2 \
    percona-server-server \
    percona-server-rocksdb

# Install sysbench
RUN apt-get install --yes --quiet=2 \
    libmysqlclient-dev \
    libssl-dev \
    && git clone https://github.com/akopytov/sysbench.git \
    && cd sysbench \
    && ./autogen.sh \
    && ./configure \
    && make -j \
    && make install

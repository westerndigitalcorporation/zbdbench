FROM docker.io/library/percona:ps-8.0.33-25

USER root
RUN dnf -y install \
    autoconf \
    automake \
    libuuid \
    libuuid-devel \
    libblkid \
    libblkid-devel \
    lzo \
    lzo-devel \
    zlib \
    zlib-devel \
    libzstd-devel \
    libzstd \
    libudev-devel \
    gcc \
    e2fsprogs \
    e2fsprogs-devel \
    util-linux \
    python3 \
    python3-devel \
    python3-pip \
    git;

# Install btrfs-progs
RUN git clone https://github.com/kdave/btrfs-progs.git \
    && cd btrfs-progs \
    && git checkout v5.18 \
    && ./autogen.sh \
    && ./configure --disable-documentation --enable-zoned \
    && make \
    && make install


RUN dnf -y install \
    libtool;

# Install sysbench
RUN git clone https://github.com/akopytov/sysbench.git \
    && cd sysbench \
    && ./autogen.sh \
    && ./configure \
    && make -j \
    && make install

RUN dnf -y install xfsprogs
RUN yum install sudo

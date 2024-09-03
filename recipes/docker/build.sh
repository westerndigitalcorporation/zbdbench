#!/bin/sh

# to prune all images, execute "podman prune -a". Note that it will remove ALL! images loaded.

podman build --jobs=$(nproc) -t zfio fio
podman build --jobs=$(nproc) -t zspdk-fio spdk/uring
podman build --jobs=$(nproc) -t zrocksdb rocksdb
podman build --jobs=$(nproc) -t zf2fs f2fs
podman build --jobs=$(nproc) -t zxfs xfs
podman build --jobs=$(nproc) -t zsysbench sysbench

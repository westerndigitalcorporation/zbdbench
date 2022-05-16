#!/bin/sh

# to prune all images, execute "podman prune -a". Note that it will remove ALL! images loaded.

podman build -t zfio fio
podman build -t zrocksdb rocksdb
podman build -t zzenfs zenfs

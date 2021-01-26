#!/bin/sh

# to prune all images in docker. Execute "docker prune -a". Note that it will remove ALL! images loaded.

docker build -t zfio fio
docker build -t zrocksdb rocksdb
docker build -t zzenfs zenfs

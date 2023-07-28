#!/usr/bin/bash
set -e

# spdk build script for use with zbdbench
# Cmdline Args:
# $1 - Dir where spdk(and fio) will be checked out and built
# $2 - nvme dev name (/dev/nvmeXnY)


SPDK_INSTALL_DIR=$1
DEVNAME=$2
SPDK_VER=v22.09
FIO_VER=fio-3.30

ZBDBENCH_DIR=$PWD

CURR_FIO_VER=$(fio --version)

# Check if Fio version of host system matches the one used for Fio in this script(for spdk build)
if [[ $CURR_FIO_VER != $FIO_VER ]]
then
	echo "Mis-match b/w system installed FIO and FIO version script will use( for spdK build)."
	echo "Install $FIO_VER or update the script's fio version to match the host system's FIO."
	exit 1
fi

if [[ -f "$SPDK_INSTALL_DIR/fio/fio" ]]
then
    echo "Existing FIO build detected.."
else
	echo "Building FIO.."
	git clone https://github.com/axboe/fio.git $SPDK_INSTALL_DIR/fio
	cd $SPDK_INSTALL_DIR/fio
	git checkout $FIO_VER
	./configure
	make -j "$(nproc)"
fi

cd ..

if [[ -f "$SPDK_INSTALL_DIR/spdk/build/fio/spdk_bdev" ]]
then
    echo "Existing SPDK build detected.."
else
	echo "Building SPDK.."
	git clone https://github.com/spdk/spdk.git $SPDK_INSTALL_DIR/spdk
	cd $SPDK_INSTALL_DIR/spdk
	git checkout $SPDK_VER
	git submodule update --init
	sudo ./scripts/pkgdep.sh --all
	./configure --with-fio=$SPDK_INSTALL_DIR/fio --with-uring
	make -j "$(nproc)"
fi
cp -a $ZBDBENCH_DIR/recipes/docker/spdk/uring/bdev_zoned_uring.json .
# Edit the json file and update /dev/nvmeXnY as per phys nvme dev passed as cmdline arg
sed -i 's|\/dev\/nvme.*|'$DEVNAME'",|g' bdev_zoned_uring.json


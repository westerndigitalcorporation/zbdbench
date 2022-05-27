#!/bin/bash
set -e
#set -x
chown mysql:mysql /dev/$dev
chmod 640 /dev/$dev
mkfs.btrfs -d single -m single /dev/$dev -f
mkdir -p /mnt/test
chown mysql:mysql /mnt/test
mount -t btrfs /dev/$dev /mnt/test
cp -Rp /var/lib/mysql /mnt/test/mysql

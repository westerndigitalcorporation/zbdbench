#!/bin/bash
set -e
set -x
chown mysql:mysql /dev/$dev
chmod 640 /dev/$dev
mkfs.xfs -f /dev/$dev
#su mysql -c 'mkfs -t xfs -s size=`blockdev --getbsz /dev/$dev` /dev/$dev -f'
mkdir -p /mnt/test
chown mysql:mysql /mnt/test
mount -t xfs /dev/$dev /mnt/test
cp -Rp /var/lib/mysql /mnt/test/mysql

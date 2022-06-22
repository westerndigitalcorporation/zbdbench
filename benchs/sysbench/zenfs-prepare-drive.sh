#!/bin/bash
set -e
#set -x
chown mysql:mysql /dev/$dev
chmod 640 /dev/$dev
mkdir /var/lib/mysql_aux_$dev
chown mysql:mysql /var/lib/mysql_aux_$dev
chmod 750 /var/lib/mysql_aux_$dev
zenfs mkfs --zbd=$dev --aux_path=/var/lib/mysql_aux_$dev --finish_threshold=0 --force
zenfs --version | tee -a /output/zenfs-version.txt

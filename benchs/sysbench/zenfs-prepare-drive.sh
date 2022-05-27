#!/bin/bash
set -e
#set -x
chown mysql:mysql /dev/$dev
chmod 640 /dev/$dev
mkdir /var/lib/mysql/aux_$dev
chown mysql:mysql /var/lib/mysql/aux_$dev
chmod 750 /var/lib/mysql/aux_$dev
zenfs mkfs --zbd=$dev --aux_path=/var/lib/mysql/aux_$dev --finish_threshold=0 --force

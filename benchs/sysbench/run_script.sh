#!/bin/bash
set -e
set -x
SOCKET=/var/run/mysqld/mysql.sock
sudo cp /output/init-mysqld.cnf /etc/my.cnf
sudo -u mysql mysqld --initialize-insecure
bash /output/prepare-drive.sh
sudo -u mysql mysqld &
sleep 10

sudo ps-admin --enable-rocksdb -u root -S $SOCKET
mysql -u root -S $SOCKET -e "SET GLOBAL default_storage_engine=ROCKSDB;"
sleep 5

sudo cp /output/bulkload-mysqld.cnf /etc/my.cnf
cat /etc/my.cnf
mysqladmin -S $SOCKET shutdown
sudo -u mysql mysqld &
sleep 10

mysql -u root -S $SOCKET -e "create database sbtest;"
sleep 2
#mysql -u root --password=pw -e "show engines;"
#mysql -u root --password=pw -e "show databases;"
export TABLESIZE=200000000
export TABLES=20
export THREADS=32
export TIME=3600
#TODO: How to kill the rest of this script when interrupted by the user?
/sysbench/src/lua/oltp_write_only.lua --db-driver=mysql --mysql-user=root --time=0 --create_secondary=off --mysql-host=localhost --mysql-db=sbtest --mysql-storage-engine=rocksdb --mysql-socket=$SOCKET --table-size=$TABLESIZE --tables=$TABLES --threads=$THREADS --report-interval=5 prepare | tee -a /output/sysbench-prepare.txt

sudo cp /output/workload-mysqld.cnf /etc/my.cnf
cat /etc/my.cnf
mysqladmin -S $SOCKET shutdown
sudo -u mysql mysqld &
sleep 10

/sysbench/src/lua/oltp_update_index.lua --db-driver=mysql --mysql-user=root --time=$TIME --create_secondary=off --mysql-host=localhost --mysql-db=sbtest --mysql-storage-engine=rocksdb --mysql-socket=$SOCKET --table-size=$TABLESIZE --tables=$TABLES --threads=$THREADS --report-interval=5 run | tee -a /output/sysbench-oltp_update_index.txt
/sysbench/src/lua/oltp_update_non_index.lua --db-driver=mysql --mysql-user=root --time=$TIME --create_secondary=off --mysql-host=localhost --mysql-db=sbtest --mysql-storage-engine=rocksdb --mysql-socket=$SOCKET --table-size=$TABLESIZE --tables=$TABLES --threads=$THREADS --report-interval=5 run | tee -a /output/sysbench-oltp_update_non_index.txt
/sysbench/src/lua/oltp_delete.lua --db-driver=mysql --mysql-user=root --time=$TIME --create_secondary=off --mysql-host=localhost --mysql-db=sbtest --mysql-storage-engine=rocksdb --mysql-socket=$SOCKET --table-size=$TABLESIZE --tables=$TABLES --threads=$THREADS --report-interval=5 run | tee -a /output/sysbench-oltp_delete.txt
/sysbench/src/lua/oltp_write_only.lua --db-driver=mysql --mysql-user=root --time=$TIME --create_secondary=off --mysql-host=localhost --mysql-db=sbtest --mysql-storage-engine=rocksdb --mysql-socket=$SOCKET --table-size=$TABLESIZE --tables=$TABLES --threads=$THREADS --report-interval=5 run | tee -a /output/sysbench-oltp_write_only.txt
/sysbench/src/lua/oltp_insert.lua --db-driver=mysql --mysql-user=root --time=$TIME --create_secondary=off --mysql-host=localhost --mysql-db=sbtest --mysql-storage-engine=rocksdb --mysql-socket=$SOCKET --table-size=$TABLESIZE --tables=$TABLES --threads=$THREADS --report-interval=5 run | tee -a /output/sysbench-oltp_insert.txt
/sysbench/src/lua/oltp_read_write.lua --db-driver=mysql --mysql-user=root --time=$TIME --create_secondary=off --mysql-host=localhost --mysql-db=sbtest --mysql-storage-engine=rocksdb --mysql-socket=$SOCKET --table-size=$TABLESIZE --tables=$TABLES --threads=$THREADS --report-interval=5 run | tee -a /output/sysbench-oltp_read_write.txt
/sysbench/src/lua/oltp_read_only.lua --db-driver=mysql --mysql-user=root --time=$TIME --create_secondary=off --mysql-host=localhost --mysql-db=sbtest --mysql-storage-engine=rocksdb --mysql-socket=$SOCKET --table-size=$TABLESIZE --tables=$TABLES --threads=$THREADS --report-interval=5 run | tee -a /output/sysbench-oltp_read_only.txt

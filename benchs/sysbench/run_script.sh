#!/bin/bash
set -e
#set -x
service mysql stop
bash /output/prepare-drive.sh
cp /output/bulkload-mysqld.cnf /etc/mysql/mysql.conf.d/mysqld.cnf
cat /etc/mysql/mysql.conf.d/mysqld.cnf
service mysql restart
mysql -u root --password=pw -e "create database sbtest;"
#mysql -u root --password=pw -e "show engines;"
#mysql -u root --password=pw -e "show databases;"
export TABLESIZE=200000000
export TABLES=20
export THREADS=32
export TIME=3600
/sysbench/src/lua/oltp_write_only.lua --db-driver=mysql --mysql-user=root --time=0 --create_secondary=off --mysql-password=pw --mysql-host=localhost --mysql-db=sbtest --mysql-storage-engine=rocksdb --table-size=$TABLESIZE --tables=$TABLES --threads=$THREADS --report-interval=5 prepare | tee -a /output/sysbench-prepare.txt
service mysql stop
cp /output/workload-mysqld.cnf /etc/mysql/mysql.conf.d/mysqld.cnf
cat /etc/mysql/mysql.conf.d/mysqld.cnf
service mysql restart
/sysbench/src/lua/oltp_update_index.lua --db-driver=mysql --mysql-user=root --time=$TIME --create_secondary=off --mysql-password=pw --mysql-host=localhost --mysql-db=sbtest --mysql-storage-engine=rocksdb --table-size=$TABLESIZE --tables=$TABLES --threads=$THREADS --report-interval=5 run | tee -a /output/sysbench-oltp_update_index.txt
/sysbench/src/lua/oltp_update_non_index.lua --db-driver=mysql --mysql-user=root --time=$TIME --create_secondary=off --mysql-password=pw --mysql-host=localhost --mysql-db=sbtest --mysql-storage-engine=rocksdb --table-size=$TABLESIZE --tables=$TABLES --threads=$THREADS --report-interval=5 run | tee -a /output/sysbench-oltp_update_non_index.txt
/sysbench/src/lua/oltp_delete.lua --db-driver=mysql --mysql-user=root --time=$TIME --create_secondary=off --mysql-password=pw --mysql-host=localhost --mysql-db=sbtest --mysql-storage-engine=rocksdb --table-size=$TABLESIZE --tables=$TABLES --threads=$THREADS --report-interval=5 run | tee -a /output/sysbench-oltp_delete.txt
/sysbench/src/lua/oltp_write_only.lua --db-driver=mysql --mysql-user=root --time=$TIME --create_secondary=off --mysql-password=pw --mysql-host=localhost --mysql-db=sbtest --mysql-storage-engine=rocksdb --table-size=$TABLESIZE --tables=$TABLES --threads=$THREADS --report-interval=5 run | tee -a /output/sysbench-oltp_write_only.txt
/sysbench/src/lua/oltp_insert.lua --db-driver=mysql --mysql-user=root --time=$TIME --create_secondary=off --mysql-password=pw --mysql-host=localhost --mysql-db=sbtest --mysql-storage-engine=rocksdb --table-size=$TABLESIZE --tables=$TABLES --threads=$THREADS --report-interval=5 run | tee -a /output/sysbench-oltp_insert.txt
/sysbench/src/lua/oltp_read_write.lua --db-driver=mysql --mysql-user=root --time=$TIME --create_secondary=off --mysql-password=pw --mysql-host=localhost --mysql-db=sbtest --mysql-storage-engine=rocksdb --table-size=$TABLESIZE --tables=$TABLES --threads=$THREADS --report-interval=5 run | tee -a /output/sysbench-oltp_read_write.txt
/sysbench/src/lua/oltp_read_only.lua --db-driver=mysql --mysql-user=root --time=$TIME --create_secondary=off --mysql-password=pw --mysql-host=localhost --mysql-db=sbtest --mysql-storage-engine=rocksdb --table-size=$TABLESIZE --tables=$TABLES --threads=$THREADS --report-interval=5 run | tee -a /output/sysbench-oltp_read_only.txt

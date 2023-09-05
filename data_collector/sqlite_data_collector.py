#!/usr/bin/env python3
import csv
import sys
import socket
import os
import sqlite3
from sqlite3 import Error
from benchs import fio_steady_state_performance, fio_zone_throughput_avg_lat

class DatabaseConnection(object):
    sqlite_connection = None
    cursor = None

    def __init__(self, db_file_path):
        try:
            self.sqlite_connection = sqlite3.connect(db_file_path)
            print("Connected to sqlite db %s - Version %s" % (db_file_path, sqlite3.version))
            self.cursor = self.sqlite_connection.cursor()
            self.create_required_tables_if_not_exists()
        except Error as e:
            print(e)
            if self.cursor:
                self.cursor.close()
            if self.sqlite_connection:
                self.sqlite_connection.close()
            exit(1)

    def __del__(self):
        if self.sqlite_connection:
            self.sqlite_connection.commit()
        if self.cursor:
            self.cursor.close()
        if self.sqlite_connection:
            self.sqlite_connection.close()

    def get_hostname(self):
        return socket.gethostname()

    def get_username(self):
        return os.getlogin()

    def get_device_info_field(self, results_dir, info_field):
        device_info_field = "Not found"
        try:
            with open(os.path.join(results_dir, "udevadm-info.txt"), 'r') as f:
                for line in f.readlines():
                    if info_field in line:
                        device_info_field = line.split("=")[-1].strip()
                        break
        except FileNotFoundError as e:
            pass
        return device_info_field

    def get_device_serial(self, results_dir):
        return self.get_device_info_field(results_dir, "ID_SERIAL=")

    def get_device_fw(self, results_dir):
        return self.get_device_info_field(results_dir, "ID_REVISION=")

    def get_file_content(self, results_dir, filename):
        file_content = "Not found"
        try:
            with open(os.path.join(results_dir, filename), 'r') as f:
                file_content = " ".join(f.readlines()).strip()
        except FileNotFoundError as e:
            pass
        return file_content

    def get_benchmark(self, results_dir):
        return self.get_file_content(results_dir, "benchmark.txt")

    def get_benchmark_call(self, results_dir):
        return self.get_file_content(results_dir, "benchmark_call.txt")

    def get_zbdbench_version(self, results_dir):
        return self.get_file_content(results_dir, "zbdbench_version.txt")

    def get_user_annotation(self, results_dir):
        return self.get_file_content(results_dir, "user_annotation.txt")

    def create_required_tables_if_not_exists(self):
        self.create_ZBDBENCH_RUN_table_if_not_exists()
        self.create_bench_table_if_not_exists(fio_zone_throughput_avg_lat)
        self.create_bench_table_if_not_exists(fio_steady_state_performance)

    #TODO: add benchmark itself in that table
    def create_ZBDBENCH_RUN_table_if_not_exists(self):
        sql_query = ("CREATE TABLE IF NOT EXISTS zbdbench_run ("
                     "id integer PRIMARY KEY,"
                     "user_annotation text NOT_NULL,"
                     "result_dir text NOT_NULL,"
                     "hostname text NOT_NULL,"
                     "username text NOT_NULL,"
                     "device_serial text NOT_NULL,"
                     "device_fw text NOT_NULL,"
                     "benchmark text NOT_NULL,"
                     "benchmark_call text NOT_NULL,"
                     "zbdbench_version text NOT_NULL"
                     ");")
        self.cursor.execute(sql_query)

    def create_bench_table_if_not_exists(self, bench):
        csv_header = bench.csv_header
        table_fields = (", ".join(["%s text"] * len(csv_header))
                        % tuple(csv_header))
        bench_name = bench.__name__.split("benchs.")[-1]
        sql_query = (f"CREATE TABLE IF NOT EXISTS {bench_name} ("
                     f"id integer PRIMARY KEY,"
                     f"zbdbench_run_id integer NOT NULL,"
                     f"{table_fields},"
                     f"FOREIGN KEY (zbdbench_run_id) REFERENCES zbdbench_run (id)"
                     f");")
        self.cursor.execute(sql_query)

    def insert_entry_into_ZBDBENCH_RUN(self, content):
        sql_query = ("INSERT INTO zbdbench_run("
                     "user_annotation,"
                     "result_dir,"
                     "hostname,"
                     "username,"
                     "device_serial,"
                     "device_fw,"
                     "benchmark,"
                     "benchmark_call,"
                     "zbdbench_version"
                     ")"
                     "VALUES(?,?,?,?,?,?,?,?,?)")
        self.cursor.execute(sql_query, content)
        return self.cursor.lastrowid

    def insert_entry_into_bench_table(self, bench, content):
        csv_header = bench.csv_header
        bench_name = bench.__name__.split("benchs.")[-1]
        table_fields = (",".join(["%s"] * len(csv_header))
                        % tuple(csv_header))
        values_placeholder = ",".join(["?"] * (len(csv_header) + 1))
        if len(csv_header) + 1 != len(content):
            print(f"Header mismatch for the {bench_name} content attempted to be added to the DB. Exiting!")
            exit(1)
        sql_query = (f"INSERT INTO {bench_name}("
                     f"zbdbench_run_id,"
                     f"{table_fields}"
                     f")"
                     f"VALUES({values_placeholder})")
        self.cursor.execute(sql_query, content)
        return self.cursor.lastrowid

    def collect_fio_results_from_directory(self, results_dir):
        if not os.path.isdir(results_dir):
            print("Can not collect results from non existing directory '%s'" % results_dir)
            sys.exit(1)

        benchmark = self.get_benchmark(results_dir);
        #TODO: check if that ZBDBENCH_RUN already exists
        zbdbench_run_id = self.insert_entry_into_ZBDBENCH_RUN((self.get_user_annotation(results_dir),
                                                               results_dir,
                                                               self.get_hostname(),
                                                               self.get_username(),
                                                               self.get_device_serial(results_dir),
                                                               self.get_device_fw(results_dir),
                                                               benchmark,
                                                               self.get_benchmark_call(results_dir),
                                                               self.get_zbdbench_version(results_dir)))

        if benchmark == "fio_zone_throughput_avg_lat":
            csv_file_path = os.path.join(results_dir, "fio_zone_throughput_avg_lat.csv")
            bench_module = fio_zone_throughput_avg_lat
        if benchmark == "fio_steady_state_performance":
            csv_file_path = os.path.join(results_dir, "fio_steady_state_performance.csv")
            bench_module = fio_steady_state_performance
        else:
            #TODO: Remove zbdbench_run_id entry
            print(f"The data collection for benchmark '{benchmark}' is not implemented. Skipping this step.")
            exit(0)

        with open(csv_file_path, 'r') as file:
            try:
                header = next(csv.reader(file, delimiter=';'))
                if header != bench_module.csv_header:
                    print(f"Header expected for the {benchmark} is different form the actuall csv report. Exiting!")
                    exit(1)
                data=[tuple(line) for line in csv.reader(file, delimiter=';')]
                for dataline in data:
                    content = tuple(str(zbdbench_run_id)) + dataline
                    self.insert_entry_into_bench_table(bench_module, content)
            except Error as e:
                print(e)

if __name__ == "__main__":
    print("%s is not meant to run as a stand alone script." % os.path.basename(__file__))


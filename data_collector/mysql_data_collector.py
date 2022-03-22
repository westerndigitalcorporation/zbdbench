#!/usr/bin/env python3
import csv
import json
import sys
import socket
import os
import glob
import pandas
import flatten_json
import mysql.connector
import run
from dotenv import dotenv_values

class DatabaseConnection(object):
    database_name = "zbdbench"
    files_table = "files"
    data_table = "data"
    files_to_data_table = "files_to_data"
    files_table_fields = ['zbdbench_results_dir',
                         'zbdbench_result_filename',
                         'zbdbench_hostname',
                         'zbdbench_username',
                         'zbdbench_version',
                         'zbdbench_device_serial',
                         'zbdbench_device_fw',
                         'zbdbench_benchmark_call']
    mysql_connection = None
    mysql_cursor = None

    def get_mysql_config(self, config_file_path):
        config = {}
        if not os.path.exists(config_file_path):
           print("No %s found. Please refer to the README.md" % config_file_path)
           sys.exit(1)
        config = dotenv_values(config_file_path)
        if config == {}:
            print("Empty %s found. Please refer to the README.md" % config_file_path)
            sys.exit(1)
        return config

    def __init__(self, config_file_path):
        config = self.get_mysql_config(config_file_path)
        self.mysql_connection = mysql.connector.connect(**config)
        self.mysql_cursor = self.mysql_connection.cursor(buffered=True)
        self.create_zbdbench_database_if_not_exists()
        self.create_zbdbench_tables_if_not_exists()

    def __del__(self):
        if self.mysql_connection != None:
            self.mysql_connection.commit()
        if self.mysql_cursor != None:
            self.mysql_cursor.close()
        if self.mysql_connection != None:
            self.mysql_connection.close()

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

    def get_benchmark_call(self, results_dir):
        benchmark_call = "Not found"
        try:
            with open(os.path.join(results_dir, "benchmark_call.txt"), 'r') as f:
                benchmark_call = " ".join(f.readlines()).strip()
        except FileNotFoundError as e:
            pass
        return benchmark_call

    def exec_mysql_query_notes_disabled(self, query):
        self.mysql_cursor.execute("SET sql_notes = 0; ")
        self.mysql_cursor.execute(query)
        lastrowid = self.mysql_cursor.lastrowid
        self.mysql_cursor.execute("SET sql_notes = 1; ")
        return lastrowid

    def create_zbdbench_database_if_not_exists(self):
        query = "CREATE DATABASE IF NOT EXISTS %s" % self.database_name
        self.exec_mysql_query_notes_disabled(query)

    def create_zbdbench_tables_if_not_exists(self):
        self.create_files_table_if_not_exists()
        self.create_data_table_if_not_exists()
        self.create_files_to_data_table_if_not_exists()

    def create_files_table_if_not_exists(self):
        table_fields = (", ".join(["`%s` LONGTEXT "] * len(self.files_table_fields))
                        % tuple(self.files_table_fields))
        query = ("CREATE TABLE IF NOT EXISTS `%s`.`%s`("
                 "`f_id` INT UNSIGNED NOT NULL auto_increment, "
                 "%s, "
                 "PRIMARY KEY(`f_id`));"
                 % (self.database_name, self.files_table, table_fields))
        self.exec_mysql_query_notes_disabled(query)

    def create_data_table_if_not_exists(self):
        query = ("CREATE TABLE IF NOT EXISTS `%s`.`%s`("
                 "`d_id` INT UNSIGNED NOT NULL auto_increment, "
                 "`value` LONGTEXT, PRIMARY KEY(`d_id`));"
                 % (self.database_name, self.data_table))
        self.exec_mysql_query_notes_disabled(query)

    def create_files_to_data_table_if_not_exists(self):
        query = ("CREATE TABLE IF NOT EXISTS `%s`.`%s`("
                 "`f_id` INT UNSIGNED NOT NULL, "
                 "`d_id` INT UNSIGNED NOT NULL, "
                 "`field` LONGTEXT, "
                 "PRIMARY KEY(`f_id`, `d_id`), "
                 "FOREIGN KEY(`f_id`) REFERENCES `%s`.`%s`(`f_id`), "
                 "FOREIGN KEY(`d_id`) REFERENCES `%s`.`%s`(`d_id`));"
                 % (self.database_name,
                    self.files_to_data_table,
                    self.database_name,
                    self.files_table,
                    self.database_name,
                    self.data_table))
        self.exec_mysql_query_notes_disabled(query)

    def insert_new_files_entry(self, data):
        table_fields = ", ".join(self.files_table_fields)
        values = ""
        for table_field in self.files_table_fields:
            values += str(data.get(str(table_field)))
            if table_field != self.files_table_fields[-1]:
                values += "', '"
        query = ("INSERT INTO `%s`.`%s` (%s) VALUES ('%s')"
                 % (self.database_name, self.files_table, table_fields, values))
        return self.exec_mysql_query_notes_disabled(query)

    def insert_new_data_entry(self, value):
        query = ("INSERT INTO `%s`.`%s` (value) VALUES ('%s')"
                 % (self.database_name, self.data_table, value))
        return self.exec_mysql_query_notes_disabled(query)

    def insert_new_files_to_data_entry(self, f_id, d_id, field):
        query = ("INSERT INTO `%s`.`%s` (f_id, d_id, field) VALUES ('%s', '%s', '%s')"
                 % (self.database_name, self.files_to_data_table, f_id, d_id, field))
        return self.exec_mysql_query_notes_disabled(query)

    def insert_entry_in_database(self, data):
        f_id = self.insert_new_files_entry(data)
        for field_key, field_value in data.items():
            if field_key in self.files_table_fields:
                continue
            d_id = self.insert_new_data_entry(str(field_value))
            self.insert_new_files_to_data_entry(f_id, d_id, field_key)

    def clean_dict_data_for_mysql(self, data):
        clean_data = {}
        for key in data.keys():
            newValue = str(data[key]).replace(",", "##").replace("'"," ").replace(";", "', '").replace("##", ";")
            newKey = key.replace(" ", "_").replace(".", "_").replace(">=", "geq").replace("<=", "leq")
            clean_data[newKey] = newValue
        return clean_data

    def convert_json_to_flat_dict(self, json_data):
        json_data = flatten_json.flatten(json_data, '_')
        json_data = pandas.json_normalize(json_data)
        dataframe = pandas.DataFrame(json_data)
        return dataframe.to_dict('records')[0]

    def insert_json_as_benchmark_entry(self, json_data):
        data = self.convert_json_to_flat_dict(json_data)
        data = self.clean_dict_data_for_mysql(data)
        self.insert_entry_in_database(data)

    def collect_json_results_from_directory(self, results_dir):
        if not os.path.isdir(results_dir):
            print("Can not collect results from non existing directory '%s'" % results_dir)
            sys.exit(1)

        for file_path in glob.glob(os.path.join(results_dir, "*")):
            if not os.path.isfile(file_path):
                continue
            with open(file_path, 'r') as file:
                try:
                    json_data = json.load(file)
                except:
                    continue
                json_data['zbdbench_results_dir'] = results_dir
                json_data['zbdbench_result_filename'] = file.name
                json_data['zbdbench_hostname'] = self.get_hostname()
                json_data['zbdbench_username'] = self.get_username()
                json_data['zbdbench_version'] = run.get_zbdbench_version()
                json_data['zbdbench_device_serial'] = self.get_device_serial(results_dir)
                json_data['zbdbench_device_fw'] = self.get_device_fw(results_dir)
                json_data['zbdbench_benchmark_call'] = self.get_benchmark_call(results_dir)
                self.insert_json_as_benchmark_entry(json_data)

if __name__ == "__main__":
    print("%s is not meant to run as a standalone script." % os.path.basename(__file__))


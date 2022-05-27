import csv
import sys
import os.path
import shutil
import glob
import re
from string import Template
from statistics import mean
from .base import base_benches, Bench, DeviceScheduler
from benchs.base import is_dev_zoned

class Run(Bench):
    jobname = "sysbench"
    filesystem = "btrfs"
    valid_conventional_filesystems = ["btrfs", "xfs"]
    valid_zoned_filesystems = ["btrfs", "zenfs"]

    def __init__(self):
        pass

    def get_default_device_scheduler(self):
        return DeviceScheduler.MQ_DEADLINE

    def id(self):
        return self.jobname

    def prepare_config_files(self, dev):
        dev_string = dev.strip('/dev/')
        sysbench_dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sysbench')
        for abs_file in glob.glob(str(os.path.join(sysbench_dir_path, '*'))):
            file_name = os.path.basename(abs_file)
            src_file = os.path.join(sysbench_dir_path, file_name)
            dest_file = os.path.join(self.output, file_name)
            shutil.copyfile(src_file, dest_file)
            file_content = ''
            with open(dest_file, "r") as file:
                file_content = file.read()
            with open(dest_file, "w+") as file:
                file.write(Template(file_content).safe_substitute(dev=dev_string))

    def copy_filesystem_related_files(self):
        selected_prepare_drive_script = os.path.join(self.output, "%s-prepare-drive.sh" % self.filesystem)
        prepare_drive_script_path = os.path.join(self.output, 'prepare-drive.sh')
        shutil.copyfile(selected_prepare_drive_script, prepare_drive_script_path)

        cnf_selector = self.filesystem
        if self.filesystem != "zenfs":
            cnf_selector = "posix-fs"
        selected_bulkload_cnf = os.path.join(self.output, "%s-bulkload-mysqld.cnf" % cnf_selector)
        bulkload_cnf_path = os.path.join(self.output, 'bulkload-mysqld.cnf')
        shutil.copyfile(selected_bulkload_cnf, bulkload_cnf_path)
        selected_workload_cnf = os.path.join(self.output, "%s-workload-mysqld.cnf" % cnf_selector)
        workload_cnf_path = os.path.join(self.output, 'workload-mysqld.cnf')
        shutil.copyfile(selected_workload_cnf, workload_cnf_path)

    def verify_filesystem_choice(self, dev):
        if is_dev_zoned(dev):
            if self.filesystem not in self.valid_zoned_filesystems:
                print(f"Invalid file-system choice '{self.filesystem}'. Valid choices are {self.valid_zoned_filesystems}.")
                sys.exit(1)
        else:
            if self.filesystem not in self.valid_conventional_filesystems:
                print(f"Invalid file-system choice '{self.filesystem}'. Valid choices are {self.valid_conventional_filesystems}.")
                sys.exit(1)

    def setup(self, dev, container, output, arguments):
        super(Run, self).setup(container, output, arguments)

        if container == "no":
            print(f"The {self.jobname} benchmark requires the use of container. Consider using '-c yes'")
            sys.exit(1)

        if len(arguments) > 1:
            print(f"The {self.jobname} benchmark supports only one parameter which should be a supported file-system.")
            sys.exit(1)

        if is_dev_zoned(dev):
            self.filesystem = "zenfs"
        else:
            self.filesystem = "xfs"

        if len(arguments) > 0:
            self.filesystem = str(arguments[0])

        self.verify_filesystem_choice(dev)

        self.discard_dev(dev)
        self.prepare_config_files(dev)
        self.copy_filesystem_related_files()

    def required_container_tools(self):
        return super().required_container_tools() |  {'sysbench'}

    def run(self, dev, container):
        #TODO persist relevant mysql dirs from the container so that the existing db can be reused
        run_script_path = os.path.join(self.output, 'run_script.sh')
        with open(run_script_path, 'r') as run_script:
            print("Run instructions:\n%s" % run_script.read())
        self.run_cmd(dev, container, 'sysbench', "bash /output/run_script.sh")

    def teardown(self, dev, container):
        pass

    def report(self, path):
        csv_file = path + "/" + self.jobname + ".csv"
        with open(csv_file, 'w') as csvfile:
            cw = csv.writer(csvfile, delimiter=',')
            cw.writerow(['oltp_workload_log', 'transactions_per_s', 'min_lat_ms', 'avg_lat_ms', 'max_lat_ms', 'p95th_lat_ms'])
            for oltp_log in glob.glob(path + '/sysbench-oltp*.txt'):
                with open(oltp_log, 'r') as oltp_file:
                    oltp_workload_log = oltp_log
                    transactions_per_s = ''
                    min_lat_ms = ''
                    avg_lat_ms = ''
                    max_lat_ms = ''
                    p95th_lat_ms = ''
                    for line in oltp_file:
                        if re.search("eps", line):
                            transactions_per_s = line.split()[-1]
                        elif re.search("min:", line):
                            min_lat_ms = line.split()[-1]
                        elif re.search("avg:", line):
                            avg_lat_ms = line.split()[-1]
                        elif re.search("max:", line):
                            max_lat_ms = line.split()[-1]
                        elif re.search("percentile:", line):
                            p95th_lat_ms = line.split()[-1]
                    cw.writerow([str(oltp_workload_log), str(transactions_per_s), str(min_lat_ms), str(avg_lat_ms), str(max_lat_ms), str(p95th_lat_ms)])

        print("  Output written to: %s" % csv_file)
        return csv_file

base_benches.append(Run())

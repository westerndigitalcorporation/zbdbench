import csv
import sys
import subprocess
import re
import glob
import os
from datetime import datetime
from .base import base_benches, Bench, DeviceScheduler
from benchs.base import is_dev_zoned

operation_list = ["randwrite", "randwrite"]
log_interval_sec = 10
fio_runtime = "0"
fio_ramptime = "0"
direct = 1
output_format = "terse"
offset_increment = "0"
device_cap = 0

fio_metadata_header = ['cmd', 'fio_run_start_time', 'ioengine', 'direct', 'zonemode', 'output_format', 'max_open_zones', 'filename', 'rw', 'bs', 'offset_increment', 'iodepth', 'numjobs', 'name', 'size', 'time_based', 'ramp_time', 'runtime']
fio_terse_header = ['terse_version_3', 'fio_version', 'jobname', 'groupid', 'error', 'read_kb', 'read_bandwidth_kb', 'read_iops', 'read_runtime_ms', 'read_slat_min_us', 'read_slat_max_us', 'read_slat_mean_us', 'read_slat_dev_us', 'read_clat_min_us', 'read_clat_max_us', 'read_clat_mean_us', 'read_clat_dev_us', 'read_clat_pct01', 'read_clat_pct02', 'read_clat_pct03', 'read_clat_pct04', 'read_clat_pct05', 'read_clat_pct06', 'read_clat_pct07', 'read_clat_pct08', 'read_clat_pct09', 'read_clat_pct10', 'read_clat_pct11', 'read_clat_pct12', 'read_clat_pct13', 'read_clat_pct14', 'read_clat_pct15', 'read_clat_pct16', 'read_clat_pct17', 'read_clat_pct18', 'read_clat_pct19', 'read_clat_pct20', 'read_tlat_min_us', 'read_lat_max_us', 'read_lat_mean_us', 'read_lat_dev_us', 'read_bw_min_kb', 'read_bw_max_kb', 'read_bw_agg_pct', 'read_bw_mean_kb', 'read_bw_dev_kb', 'write_kb', 'write_bandwidth_kb', 'write_iops', 'write_runtime_ms', 'write_slat_min_us', 'write_slat_max_us', 'write_slat_mean_us', 'write_slat_dev_us', 'write_clat_min_us', 'write_clat_max_us', 'write_clat_mean_us', 'write_clat_dev_us', 'write_clat_pct01', 'write_clat_pct02', 'write_clat_pct03', 'write_clat_pct04', 'write_clat_pct05', 'write_clat_pct06', 'write_clat_pct07', 'write_clat_pct08', 'write_clat_pct09', 'write_clat_pct10', 'write_clat_pct11', 'write_clat_pct12', 'write_clat_pct13', 'write_clat_pct14', 'write_clat_pct15', 'write_clat_pct16', 'write_clat_pct17', 'write_clat_pct18', 'write_clat_pct19', 'write_clat_pct20', 'write_tlat_min_us', 'write_lat_max_us', 'write_lat_mean_us', 'write_lat_dev_us', 'write_bw_min_kb', 'write_bw_max_kb', 'write_bw_agg_pct', 'write_bw_mean_kb', 'write_bw_dev_kb', 'cpu_user', 'cpu_sys', 'cpu_csw', 'cpu_mjf', 'cpu_minf', 'iodepth_1', 'iodepth_2', 'iodepth_4', 'iodepth_8', 'iodepth_16', 'iodepth_32', 'iodepth_64', 'lat_2us', 'lat_4us', 'lat_10us', 'lat_20us', 'lat_50us', 'lat_100us', 'lat_250us', 'lat_500us', 'lat_750us', 'lat_1000us', 'lat_2ms', 'lat_4ms', 'lat_10ms', 'lat_20ms', 'lat_50ms', 'lat_100ms', 'lat_250ms', 'lat_500ms', 'lat_750ms', 'lat_1000ms', 'lat_2000ms', 'lat_over_2000ms', 'disk_name', 'disk_read_iops', 'disk_write_iops', 'disk_read_merges', 'disk_write_merges', 'disk_read_ticks', 'write_ticks', 'disk_queue_time', 'disk_util']
bw_log_header = ["time_sec", "write_bw_kB"]
csv_header = bw_log_header

class Run(Bench):
    jobname = "fio_steady_state_performance"

    def __init__(self):
        pass

    def get_default_device_scheduler(self):
        return DeviceScheduler.NONE

    def id(self):
        return self.jobname

    def setup(self, dev, container, output):
        global device_cap
        super(Run, self).setup(container, output)

        device_cap = self.get_nvme_drive_capacity_gb(output)
        self.discard_dev(dev)

    def required_host_tools(self):
        return super().required_host_tools() | {'iostat'}

    def required_container_tools(self):
        return super().required_container_tools() |  {'fio'}

    def run(self, dev, container):
        global fio_runtime
        global fio_ramptime
        global device_cap
        extra = ''
        ioengine = "psync"
        numjobs = 1
        iodepth = 1
        zonemode = "zbd"
        number_parallel_jobs = 16
        queue_depth = number_parallel_jobs
        block_size = "64K"
        offset_increment = ""
        dev_max_open_zones = 0

        if not is_dev_zoned(dev):
            print("Running on conventional block device")
            zonemode = "none"
            increment_size = str(int(device_cap / float(number_parallel_jobs)))
            offset_increment = f"{increment_size}Gi"
        else:
            dev_number_zones = self.get_number_of_zones(dev)
            dev_max_open_zones = self.get_number_of_max_open_zones(dev)

            if dev_number_zones < number_parallel_jobs:
                print(f"Warning: The number of parallel jobs is greater then the number of zones. Running with {dev_number_zones} parallel jobs")
                number_parallel_jobs = dev_number_zones

            increment_size = str(int(dev_number_zones / number_parallel_jobs))
            offset_increment = f"{increment_size}z"
            extra = (f"--job_max_open_zone=1"
                    f" --max_open_zones={dev_max_open_zones}")

        numjobs = int(number_parallel_jobs)
        fio_output_log_file = os.path.join(self.result_path(), "write_prep.log")
        fio_bw_log_file = os.path.join(self.result_path(), "write_prep_bw")

        self.discard_dev(dev)

        print("About to prep the drive by completely filling it")
        iostat_log_file = os.path.join(self.output, "iostat.log")
        iostat_process = subprocess.Popen(f"exec iostat {log_interval_sec} -t > {iostat_log_file}", stdout=subprocess.PIPE,  shell=True)
        init_param = (f"--ioengine={ioengine}"
                    f" --direct={direct}"
                    f" --zonemode={zonemode}"
                    f" --output-format={output_format}"
                    f" --filename={dev}"
                    f" --offset_increment={offset_increment}"
                    f" --numjobs={numjobs}"
                    f" --group_reporting"
                    f" --rw=write"
                    f" --norandommap"
                    f" --bs={block_size}"
                    f" --log_avg_msec=10000"
                    f" --write_bw_log={fio_bw_log_file}"
                    f" {extra}")

        prep_param = (f"--name=prep"
                    f" --size={offset_increment}"
                    f" --output {fio_output_log_file}")

        fio_param = f"{init_param} {prep_param}"

        fio_run_start_time = datetime.now()
        cmd = self.run_cmd(dev, container, 'fio', fio_param)

        fio_run_metadata = [str(cmd),
                            str(fio_run_start_time),
                            str(ioengine),
                            str(direct),
                            str(zonemode),
                            str(output_format),
                            str(dev_max_open_zones),
                            str(dev),
                            str("write"),
                            str(block_size),
                            str(offset_increment),
                            str(iodepth),
                            str(numjobs),
                            str("prep"),
                            str(offset_increment),
                            str("false"),
                            str("0"),
                            str("0")
                            ]
        self.safe_csv_metadata(os.path.basename(fio_output_log_file) + "metadata", fio_run_metadata)

        print("Finished preping the drive")

        for operation in operation_list:

            output_name = (f"{operation}-"
                        f"{number_parallel_jobs}-"
                        f"{queue_depth}-"
                        f"{block_size}-"
                        f"{self.jobname}")

            print(f"About to start job {output_name}")
            fio_output_log_file = os.path.join(self.result_path(), f"{output_name}.log")
            fio_bw_log_file = os.path.join(self.result_path(), f"{operation}_bw")
            init_param = (f"--ioengine={ioengine}"
                        f" --direct={direct}"
                        f" --zonemode={zonemode}"
                        f" --output-format={output_format}"
                        f" --filename={dev}"
                        f" --offset_increment={offset_increment}"
                        f" --numjobs={numjobs}"
                        f" --group_reporting"
                        f" --rw={operation}"
                        f" --norandommap"
                        f" --bs={block_size}"
                        f" --log_avg_msec=10000"
                        f" --write_bw_log={fio_bw_log_file}"
                        f" {extra}")

            exec_param = (f"--name={operation} "
                        f" --size={offset_increment}"
                        f" --output {fio_output_log_file}")

            fio_param = f"{init_param} {exec_param}"

            fio_run_start_time = datetime.now()
            cmd = self.run_cmd(dev, container, 'fio', fio_param)

            fio_run_metadata = [str(cmd),
                                str(fio_run_start_time),
                                str(ioengine),
                                str(direct),
                                str(zonemode),
                                str(output_format),
                                str(dev_max_open_zones),
                                str(dev),
                                str(operation),
                                str(block_size),
                                str(offset_increment),
                                str(iodepth),
                                str(numjobs),
                                str(operation),
                                str(offset_increment),
                                str("true"),
                                str(fio_ramptime),
                                str(fio_runtime)
                                ]
            self.safe_csv_metadata(os.path.basename(fio_output_log_file) + "metadata", fio_run_metadata)
            print("Finished job")
        iostat_process.kill()

    def teardown(self, dev, container):
        pass

    def report(self, path):
        log = os.path.join(path, "iostat.log")
        dev = ""
        with open(os.path.join(path, "udevadm-info.txt")) as f:
            dev = f.readline().strip('\n').split('/')[-1]

        csv_file = os.path.join(path, self.jobname + ".csv")
        with open(csv_file, 'w') as f:
            w = csv.writer(f, delimiter=';')
            w.writerow(bw_log_header)
            with open(log, 'r') as f_data_log:
                i = 1
                for line in f_data_log:
                    if re.search(dev, line):
                        line_columns = line.split()
                        if len(line_columns) > 4:
                            w.writerow([str(i*log_interval_sec), str(int(line.split()[3].split('.')[0]))])
                            i += 1

        print(f"  Output written to: {csv_file}")
        return csv_file

    def plot(self, csv_files):
        from plotter import matplotlib_plotter
        plot = matplotlib_plotter.Plot(self.output, csv_files)
        plot.gen_FIO_STEADY_STATE_PERFORMANCE()
        print("  Done generateing graphs")

base_benches.append(Run())



import csv
import sys
import glob
import os
from datetime import datetime
from .base import base_benches, Bench, DeviceScheduler, spdk_bdev
from benchs.base import is_dev_zoned, spdk_build

operation_list = ["read", "randread", "write"]
number_parallel_jobs_list = [1, 2, 4, 8, 16, 32, 64, 128]
queue_depth_list = [1, 2, 4, 8, 16, 32, 64, 128]
block_size_list = ["4K", "8K", "16K", "32K", "64K", "128K"]
block_size_K_list = [str(x[:-1]) for x in block_size_list]
fio_runtime = "30"
fio_ramptime = "15"
runs = 1
size = "9z"

direct = 1
zonemode = "zbd"
output_format = "terse"
offset_increment = "0z"

fio_metadata_header = ['cmd', 'fio_run_start_time', 'ioengine', 'direct', 'zonemode', 'output_format', 'max_open_zones', 'filename', 'rw', 'bs', 'offset_increment', 'iodepth', 'numjobs', 'name', 'size', 'time_based', 'ramp_time', 'runtime']
fio_terse_header = ['terse_version_3', 'fio_version', 'jobname', 'groupid', 'error', 'read_kb', 'read_bandwidth_kb', 'read_iops', 'read_runtime_ms', 'read_slat_min_us', 'read_slat_max_us', 'read_slat_mean_us', 'read_slat_dev_us', 'read_clat_min_us', 'read_clat_max_us', 'read_clat_mean_us', 'read_clat_dev_us', 'read_clat_pct01', 'read_clat_pct02', 'read_clat_pct03', 'read_clat_pct04', 'read_clat_pct05', 'read_clat_pct06', 'read_clat_pct07', 'read_clat_pct08', 'read_clat_pct09', 'read_clat_pct10', 'read_clat_pct11', 'read_clat_pct12', 'read_clat_pct13', 'read_clat_pct14', 'read_clat_pct15', 'read_clat_pct16', 'read_clat_pct17', 'read_clat_pct18', 'read_clat_pct19', 'read_clat_pct20', 'read_tlat_min_us', 'read_lat_max_us', 'read_lat_mean_us', 'read_lat_dev_us', 'read_bw_min_kb', 'read_bw_max_kb', 'read_bw_agg_pct', 'read_bw_mean_kb', 'read_bw_dev_kb', 'write_kb', 'write_bandwidth_kb', 'write_iops', 'write_runtime_ms', 'write_slat_min_us', 'write_slat_max_us', 'write_slat_mean_us', 'write_slat_dev_us', 'write_clat_min_us', 'write_clat_max_us', 'write_clat_mean_us', 'write_clat_dev_us', 'write_clat_pct01', 'write_clat_pct02', 'write_clat_pct03', 'write_clat_pct04', 'write_clat_pct05', 'write_clat_pct06', 'write_clat_pct07', 'write_clat_pct08', 'write_clat_pct09', 'write_clat_pct10', 'write_clat_pct11', 'write_clat_pct12', 'write_clat_pct13', 'write_clat_pct14', 'write_clat_pct15', 'write_clat_pct16', 'write_clat_pct17', 'write_clat_pct18', 'write_clat_pct19', 'write_clat_pct20', 'write_tlat_min_us', 'write_lat_max_us', 'write_lat_mean_us', 'write_lat_dev_us', 'write_bw_min_kb', 'write_bw_max_kb', 'write_bw_agg_pct', 'write_bw_mean_kb', 'write_bw_dev_kb', 'cpu_user', 'cpu_sys', 'cpu_csw', 'cpu_mjf', 'cpu_minf', 'iodepth_1', 'iodepth_2', 'iodepth_4', 'iodepth_8', 'iodepth_16', 'iodepth_32', 'iodepth_64', 'lat_2us', 'lat_4us', 'lat_10us', 'lat_20us', 'lat_50us', 'lat_100us', 'lat_250us', 'lat_500us', 'lat_750us', 'lat_1000us', 'lat_2ms', 'lat_4ms', 'lat_10ms', 'lat_20ms', 'lat_50ms', 'lat_100ms', 'lat_250ms', 'lat_500ms', 'lat_750ms', 'lat_1000ms', 'lat_2000ms', 'lat_over_2000ms', 'disk_name', 'disk_read_iops', 'disk_write_iops', 'disk_read_merges', 'disk_write_merges', 'disk_read_ticks', 'write_ticks', 'disk_queue_time', 'disk_util']
csv_header = fio_terse_header + fio_metadata_header

class Run(Bench):
    jobname = "fio_zone_throughput_avg_lat"

    def __init__(self):
        pass

    def get_default_device_scheduler(self):
        return DeviceScheduler.NONE

    def id(self):
        return self.jobname

    def setup(self, dev, container, output):
        super(Run, self).setup(container, output)

        self.discard_dev(dev)

    def required_container_tools(self):
        return super().required_container_tools() |  {'fio'}

    def run(self, dev, container):
        global fio_runtime
        global fio_ramptime
        extra = ''
        numjobs = 1
        iodepth = 1
        # Backup the nvme dev as it's changed to spdk bdev for spdk runs
        backup_dev = dev

        if not is_dev_zoned(dev):
            print("This test is ment to be run on a zoned dev")
            sys.exit(1)

        dev_number_zones = self.get_number_of_zones(dev)
        dev_max_open_zones = self.get_number_of_max_open_zones(dev)

        max_parallel_jobs = max(dev_max_open_zones, max(number_parallel_jobs_list))
        if dev_number_zones < max_parallel_jobs * int(size[:-1]):
            max_parallel_jobs = int(dev_number_zones/ int(size[:-1]))
            print("Warning: the provided device has not enough space to run the benchmark for the given workload size. Skipping some jobs.")

        number_prep_jobs = 2.0
        increment_size = str(int(int(size[:-1]) * max_parallel_jobs / number_prep_jobs))
        if dev_number_zones < (int(increment_size) * number_prep_jobs):
            print("The provided device has not enough space to prepare it for the given workload size")
            sys.exit(1)

        if self.spdk_path:
            if container == 'no':
                # Checkout and build SPDK for Host system
                spdk_build("spdk/uring", self.spdk_path, dev)

        for operation in operation_list:
            tmp_number_parallel_jobs_list = number_parallel_jobs_list

            if "read" in operation:
                if "randread" == operation:
                    tmp_number_parallel_jobs_list = [1]
                extra = ''
                offset_increment = f"{increment_size}z"
                numjobs = int(number_prep_jobs)
                iodepth = 1
                ioengine = "psync"
                block_size = "128K"
                fio_output_log_file = os.path.join(self.result_path(), operation + "_prep.log")

                print("About to prep the drive for read job")
                self.discard_dev(dev)

                if self.spdk_path:
                    #spdk specific args
                    ioengine = f"{self.spdk_path}/spdk/build/fio/spdk_bdev"
                    extra = extra + f" --spdk_json_conf={self.spdk_path}/spdk/bdev_zoned_uring.json --thread=1 "
                    if container == 'no':
                        dev = spdk_bdev

                init_param = (f" --ioengine={ioengine}"
                            f" --direct={direct}"
                            f" --zonemode={zonemode}"
                            f" --output-format={output_format}"
                            f" --filename={dev}"
                            f" --offset_increment={offset_increment}"
                            f" --job_max_open_zone=1"
                            f" --max_open_zones={dev_max_open_zones}"
                            f" --numjobs={numjobs}"
                            f" --group_reporting"
                            f" --rw=write"
                            f" --bs={block_size}"
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
                                    str(size),
                                    str("false"),
                                    str("0"),
                                    str("0")
                                    ]
                self.safe_csv_metadata(os.path.basename(fio_output_log_file) + "metadata", fio_run_metadata)

                print("Finished preping the drive")

            #Restore the physical nvme dev name
            dev = backup_dev
            for number_parallel_jobs in tmp_number_parallel_jobs_list:

                for queue_depth in queue_depth_list:
                    if number_parallel_jobs > queue_depth:
                        continue

                    if number_parallel_jobs * int(size[:-1]) > dev_number_zones:
                        print(f"Skipping number_parallel_jobs={number_parallel_jobs} because the device is to small for size={size}.")
                        continue

                    if ("write" in operation or "read" == operation) and queue_depth > number_parallel_jobs:
                        continue

                    for block_size in block_size_list:
                        for run in range(1, runs+1):
                            extra = ''
                            output_name = (f"{operation}-"
                                        f"{number_parallel_jobs}-"
                                        f"{queue_depth}-"
                                        f"{block_size}-"
                                        f"{self.jobname}-"
                                        f"{run}of{runs}")

                            ioengine = "io_uring"
                            offset_increment = "0z"
                            numjobs = 1
                            iodepth = queue_depth

                            extra = f" --iodepth={iodepth} "
                            if "randread" == operation:
                                fio_runtime = "15"

                            if "write" == operation or "read" == operation:
                                ioengine = "psync"
                                iodepth = 1
                                numjobs = queue_depth
                                offset_increment = size
                                extra = (f" --offset_increment={offset_increment}"
                                        f" --numjobs={numjobs}"
                                        f" --group_reporting ")

                            print(f"About to start job {output_name}")
                            fio_output_log_file = os.path.join(self.result_path(), output_name + ".log")

                            if "write" in operation:
                                self.discard_dev(dev)

                            if self.spdk_path:
                                #spdk specific args
                                ioengine = f"{self.spdk_path}/spdk/build/fio/spdk_bdev"
                                extra = extra + f" --spdk_json_conf={self.spdk_path}/spdk/bdev_zoned_uring.json --thread=1 "
                                if container == 'no':
                                    dev = spdk_bdev

                            init_param = (f"--ioengine={ioengine}"
                                        f" --direct={direct}"
                                        f" --zonemode={zonemode}"
                                        f" --output-format={output_format}"
                                        f" --max_open_zones={dev_max_open_zones}"
                                        f" --filename={dev}"
                                        f" --rw={operation}"
                                        f" --bs={block_size}"
                                        f" {extra}")

                            exec_param = (f"--name={operation} "
                                        f" --size={size}"
                                        f" --time_based"
                                        f" --ramp_time={fio_ramptime}"
                                        f" --runtime={fio_runtime}"
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
                                                str(size),
                                                str("true"),
                                                str(fio_ramptime),
                                                str(fio_runtime)
                                                ]
                            self.safe_csv_metadata(os.path.basename(fio_output_log_file) + "metadata", fio_run_metadata)
                            print("Finished job")
                            #Restore the physical nvme dev name for the next pass
                            dev = backup_dev


    def teardown(self, dev, container):
        pass

    def report(self, path):
        logs = glob.glob(path + "/*.log")
        logs.sort()

        csv_file = os.path.join(path, self.jobname + ".csv")
        with open(csv_file, 'w') as f:
            w = csv.writer(f, delimiter=';')
            w.writerow(csv_header)
            for log in logs:
                if log.endswith("prep.log"):
                    continue
                with open(log, 'r') as f_data_log:
                    r_data = csv.reader(f_data_log, delimiter=';')
                    with open(log + 'metadata', 'r') as f_meta_log:
                        r_meta = csv.reader(f_meta_log, delimiter=';')
                        fio_data = next(r_data)
                        fio_metadata = next(r_meta)
                        w.writerow(fio_data + fio_metadata)

        print(f"  Output written to: {csv_file}")
        return csv_file

    def plot(self, csv_files):
        from plotter import matplotlib_plotter
        plot = matplotlib_plotter.Plot(self.output, csv_files)
        for op in operation_list:
            plot.gen_FIO_ZONE_THROUGHPUT_AVG_LAT(op)
        print("  Done generating graphs")

base_benches.append(Run())



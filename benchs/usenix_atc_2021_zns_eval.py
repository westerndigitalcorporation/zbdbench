import csv
import shutil
import subprocess
import sys
import os
from statistics import mean
from .base import base_benches, Bench
from benchs.base import is_dev_zoned

class Run(Bench):
    def __init__(self):
        self.jobname = "usenix_atc_2021_zns_eval"

    def id(self):
        return self.jobname

    conventional_filesystems = ['xfs', 'f2fs']
    zns_filesystems = ['zenfs', 'f2fs']
    conv_nullblk_dev = ''
    db_env_param = '--fs_uri=zenfs://dev:MISSING'

    # Number of entries. Value is used to scale all rocksdb benchmarks
    # Quick run: 10000000 (10M)
    # Original run on a 2TB ZNS SSD: (3.8B)
    # scale_num = 3800000000
    # The current state of ZenFS creates a bit more space amplification
    scale_num = 3300000000

    # All benchmarks
    wb_size = str(2 * 1024 * 1024 * 1024)
    max_bytes_for_level_base = str(4 * 1024 * 1024 * 1024)

    key_size = '20'
    value_size = '800'

    stats_dump_period = '15'
    delete_obsolete_files_period = str(30 * 1000000)

    # Readwhilewriting benchmarks
    # Time in seconds per run
    read_duration = str(60 * 30)

    write_limit = str(1024 * 1024 * 20) # 20MB/s

    target_fz_base = -1

    def required_container_tools(self):
        return super().required_container_tools() | {
            'mkfs.xfs',
            'mkfs.f2fs',
            'zenfs',
            'db_bench',
        }

    def get_target_fz_base(self, dev):
        if is_dev_zoned(dev):
            zonecap = self.get_zone_capacity_mb(dev)
            return str(int(2 * zonecap * 95 / 100) * 1024 * 1024)
        else:
            return str(int(128 * 1024 * 1024))

    def get_run_string(self, dev, bench_params, name):
        params = " ", self.db_env_param, \
                      " --key_size=", self.key_size, \
                      " --value_size=", self.value_size, \
                      " --target_file_size_base=", self.target_fz_base, \
                      " --write_buffer_size=", self.wb_size, \
                      " --max_bytes_for_level_base=", self.max_bytes_for_level_base, \
                      " --max_bytes_for_level_multiplier=4", \
                      " --max_background_jobs=8", \
                      " --max_background_compactions=8", \
                      " --use_direct_io_for_flush_and_compaction", \
                      " --stats_dump_period_sec=", self.stats_dump_period, \
                      " --delete_obsolete_files_period_micros=", self.delete_obsolete_files_period, \
                      " --statistics", \
                      ''.join(bench_params), \
                      " > ", os.path.join(self.output, name + ".txt"), " 2>&1"

        return ''.join(params)

    def create_csv_file(self, filename):
        try:
            with open(filename, 'x') as f:
                w = csv.writer(f, delimiter=',')
                w.writerow(("benchmark", "ops/s", "MB/s", "readwhilewrite_write_MB/s"))
        except:
            pass

    def get_result_from_test(self, filename, testname):
        with open(filename, 'r') as f:
            lines = f.readlines()

            for line in lines:
                if testname not in line:
                    continue

                return [i for i in line.split(' ') if i]

    def report_bench(self, path, bench):
        results = []
        csv_filename = "%s.csv" % bench
        csv_file = os.path.join(path, csv_filename)
        self.create_csv_file(csv_file)

        for filename in os.listdir(path):
            if filename.endswith(".txt") and bench in filename:
                if bench == 'fillrandom' or bench == 'overwrite':
                    entries = self.get_result_from_test(os.path.join(path, filename), bench)
                    with open(csv_file, 'a') as f:
                        w = csv.writer(f, delimiter=',')
                        w.writerow((entries[0], entries[4], entries[6], '-'))
                    return csv_file
                else:
                    entries = self.get_result_from_test(os.path.join(path, filename), bench.split('_')[0])
                    writes = self.get_result_from_test(os.path.join(path, filename), 'Cumulative writes')
                    results.append((bench, float(entries[4]), float(entries[6]), float(writes[17])))
        if len(results) > 0:
            ops = mean(list(zip(*results))[1])
            mbs = mean(list(zip(*results))[2])
            write_mbs = mean(list(zip(*results))[3])

            with open(csv_file, 'a') as f:
                w = csv.writer(f, delimiter=',')
                w.writerow((bench, ops, mbs, write_mbs))
        else:
            csv_file = ''
        return csv_file

    def get_extra_container_params(self):
        if self.conv_nullblk_dev != '':
            return f'-v \"{self.conv_nullblk_dev}:{self.conv_nullblk_dev}\"'
        else:
            return ''

    def fill_prep(self, dev, container):
        num = str(self.scale_num)

        bench_params = " --benchmarks=fillrandom,stats",  \
                       " --num=", num

        self.run_cmd(dev, container, 'db_bench', self.get_run_string(dev, bench_params, "fillrandom"), self.get_extra_container_params())

    def overwrite(self, dev, container):
        num = str(self.scale_num)

        bench_params = " --benchmarks=overwrite,stats --use_existing_db",  \
                       " --num=", num

        self.run_cmd(dev, container, 'db_bench', self.get_run_string(dev, bench_params, "overwrite"), self.get_extra_container_params())

    def read_workload(self, dev, container):
        num = str(self.scale_num)

        for runid in [1, 2]:
            bench_params = " --benchmarks=readwhilewriting,stats", \
                           " --use_existing_db --histogram --threads=32",  \
                           " --num=", num, \
                           " --duration=", self.read_duration

            self.run_cmd(dev, container, 'db_bench', self.get_run_string(dev, bench_params, "readwhilewriting_%s" % runid), self.get_extra_container_params())

            bench_params = " --benchmarks=readrandom,stats", \
                           " --use_existing_db --histogram --threads=32",  \
                           " --num=", num, \
                           " --duration=", self.read_duration

            self.run_cmd(dev, container, 'db_bench', self.get_run_string(dev, bench_params, "readrandom_%s" % runid), self.get_extra_container_params())

            bench_params = " --benchmarks=readwhilewriting,stats", \
                           " --use_existing_db --histogram --threads=32",  \
                           " --num=", num, \
                           " --duration=", self.read_duration, \
                           " --benchmark_write_rate_limit=", self.write_limit

            self.run_cmd(dev, container, 'db_bench', self.get_run_string(dev, bench_params, "readwhilewriting_writelimit_%s" % runid), self.get_extra_container_params())


    def setup(self, dev, container, output):
        super(Run, self).setup(output)
        self.discard_dev(dev)
        self.target_fz_base = self.get_target_fz_base(dev)
        if is_dev_zoned(dev):
            print("Running benchmark on a ZNS device")
        else:
            print("Running benchmark on a conventional drive")

    def create_mountpoint(self, dev, filesystem):
        relative_mountpoint = "%s_%s" % (dev.strip('/dev/'), filesystem)
        mountpoint = os.path.join(self.output, relative_mountpoint)
        os.mkdir(mountpoint)
        return mountpoint, relative_mountpoint

    def create_new_nullblk_dev_config_path(self):
        subprocess.check_call('sudo modprobe null_blk', shell=True)
        dev_config_path_base = "/sys/kernel/config/nullb/nullb"
        nid = 1
        dev_config_path = dev_config_path_base + str(nid)
        while os.path.exists(dev_config_path):
            nid = nid + 1
            dev_config_path = dev_config_path_base + str(nid)
        os.mkdir(dev_config_path)
        return dev_config_path

    def destroy_nullblk_dev(self, dev):
        dev_config_path = "/sys/kernel/config/nullb/" + dev.strip('/dev/')
        with open(os.path.join(dev_config_path, 'power') , "w") as f:
            f.write("0")
        shutil.rmtree(dev_config_path, ignore_errors=True)

    def create_f2fs_nullblk_dev(self, dev, container):
        dev_config_path = self.create_new_nullblk_dev_config_path()
        with open(os.path.join(dev_config_path, 'blocksize') , "w") as f:
            f.write(str(self.get_sector_size(dev)))
        with open(os.path.join(dev_config_path, 'memory_backed') , "w") as f:
            f.write("1")
        with open(os.path.join(dev_config_path, 'power') , "w") as f:
            f.write("1")
        dev_basename = os.path.basename(os.path.normpath(dev_config_path))
        return f'/dev/{dev_basename}'

    def setup_zns(self, dev, container, filesystem):
        devname = dev.strip('/dev/')
        self.conv_nullblk_dev = ''
        if filesystem == 'zenfs':
            self.run_cmd(dev, container, 'zenfs', f'mkfs --zbd={devname} --finish_threshold=20 --aux_path=/tmp/zenfs_aux --force')
            self.db_env_param = f'--fs_uri=zenfs://dev:{devname}'
            return ''
        elif filesystem == 'f2fs':
            mountpoint, relative_mountpoint = self.create_mountpoint(dev, filesystem)
            # We need to store metadata on a nullblock device.
            self.conv_nullblk_dev = self.create_f2fs_nullblk_dev(dev, container)
            self.run_cmd(dev, container, 'mkfs.f2fs', f'-f -o 5 -m -c {dev} {self.conv_nullblk_dev}', f'-v "{self.conv_nullblk_dev}:{self.conv_nullblk_dev}"')
            subprocess.check_call('sudo modprobe f2fs', shell=True)
            subprocess.check_call(f'mount -t f2fs -o active_logs=6,whint_mode=user-based {self.conv_nullblk_dev} {mountpoint}', shell=True)
            self.db_env_param = f'--db=/output/{relative_mountpoint}/eval'
            return mountpoint
        else:
            print("Filesystem %s is not currently not supported for ZNS drives in this benchmark" % filesystem)
            exit(1)

    def setup_conventional(self, dev, container, filesystem):
        self.conv_nullblk_dev = ''
        mountpoint, relative_mountpoint = self.create_mountpoint(dev, filesystem)
        force_flag = '-f'
        if filesystem == 'ext4':
            force_flag = '-F'
        mount_opt = ''
        if filesystem == 'f2fs':
            mount_opt = '-o whint_mode=user-based'
        self.run_cmd(dev, container, f'mkfs.{filesystem}' , f'{force_flag} {dev}')
        subprocess.check_call(f'mount {mount_opt} {dev} {mountpoint}', shell=True)
        self.db_env_param = f'--db=/output/{relative_mountpoint}/eval'
        return mountpoint

    def get_filesystems_to_test(self, is_device_zoned):
        if is_device_zoned:
            return self.zns_filesystems
        else:
            return self.conventional_filesystems

    def run(self, dev, container):
        root_output = self.output
        is_device_zoned = is_dev_zoned(dev)
        for filesystem in self.get_filesystems_to_test(is_device_zoned):
            mountpoint = ''
            sub_output = os.path.join(root_output, filesystem)
            os.makedirs(sub_output)
            self.output = sub_output
            if is_device_zoned:
                mountpoint = self.setup_zns(dev, container, filesystem)
            else:
                mountpoint = self.setup_conventional(dev, container, filesystem)
            try:
                print("Starting to prepare the device with a fillrandom workload...")
                self.fill_prep(dev, container)
                print("Starting to prepare the device with an overwrite workload...")
                self.overwrite(dev, container)
                print("Starting to issue the benchmark read workload...")
                self.read_workload(dev, container)
            except Exception as e:
                raise e
            finally:
                if mountpoint != '':
                    subprocess.check_call(f'umount {mountpoint}', shell=True)
                if self.conv_nullblk_dev != '':
                    self.destroy_nullblk_dev(self.conv_nullblk_dev)

        self.output = root_output

    def report(self, dev, path):
        csv_files = []
        is_device_zoned = os.path.exists(os.path.join(path, "zenfs"))
        subpaths = self.get_filesystems_to_test(is_device_zoned)

        for subpath in subpaths:
            reportpath = os.path.join(path, subpath)
            fill_prep_csv_file = self.report_bench(reportpath, 'fillrandom')
            print("  Fill prepare output written to: %s" % (fill_prep_csv_file))
            overwrite_csv_file = self.report_bench(reportpath, 'overwrite')
            print("  Overwrite output written to: %s" % (overwrite_csv_file))
            self.report_bench(reportpath, 'readwhilewriting')
            self.report_bench(reportpath, 'readrandom')
            csv_file = self.report_bench(reportpath, 'readwhilewriting_writelimit')
            csv_files.append(csv_file)
            print("  Output written to: %s" % (csv_file))
        return csv_files

    def teardown(self, dev, container):
        pass

base_benches.append(Run())

import csv
import sys
from statistics import mean
from .base import base_benches, Bench
from benchs.base import is_dev_zoned

class RocksDBBase(Bench):

    jobname = "rocksdb_base"

    def __init__(self):
        pass

    def id(self):
        return self.jobname

    def teardown(self, dev, container):
        pass

    # Number of entries. Value is used to scale all rocksdb benchmarks
    # Quick run: 10000000 (10M)
    # 1TB ZNS SSD: 1650000000 (1.65B)
    scale_num = 1650000000

    # All benchmarks
    wb_size = str(2 * 1024 * 1024 * 1024)
    max_bytes_for_level_base = str(4 * 1024 * 1024 * 1024)

    key_size = '20'
    value_size = '800'

    stats_dump_period = '15'
    delete_obsolete_files_period = str(30 * 100000)

    # Overwrite benchmark
    overwrite_duration = str(60 * 60 * 2) # two hours

    # Readwhilewriting benchmarks
    # Time in seconds per run
    read_duration = str(60 * 2)

    write_limit = str(1024 * 1024 * 20) # 20MB/s

    def required_container_tools(self):
        return super().required_container_tools() | {
            'zenfs',
            'db_bench',
        }

    def get_target_fz_base(self, dev):
        zonecap = self.get_zone_capacity_mb(dev)
        return str(int(zonecap * 95 / 100) * 1024 * 1024)

    def get_run_string(self, dev, bench_params, name=jobname):
        devname = dev.strip('/dev/')

        params = " --fs_uri=zenfs://dev:", devname, \
                      " --key_size=", self.key_size, \
                      " --value_size=", self.value_size, \
                      " --target_file_size_base=", self.get_target_fz_base(dev), \
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
                      " > ", self.output_host_path, "/", name, ".txt 2>&1"

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

    def report(self, dev, path):
        devcap = self.get_nvme_drive_capacity_gb(path)
        if devcap is None:
            print("Could not get drive capacity for report")
            sys.exit(1)

        print("  Output written to: ")


class RocksDBFillPrep(RocksDBBase):
    def __init__(self):
        self.jobname = "rocksdb_fillprep"
        pass

    def setup(self, dev, container, output):
        super(RocksDBFillPrep, self).setup(output, container)

        self.discard_dev(dev)

        devname = dev.strip('/dev/')
        self.run_cmd(dev, container, 'zenfs', f'mkfs --zbd={devname} --finish_threshold=20 --aux_path=/tmp/zenfs_aux')

    def run(self, dev, container):
        num = str(self.scale_num)

        bench_params = " --benchmarks=fillrandom,stats",  \
                       " --num=", num

        self.run_cmd(dev, container, 'db_bench', self.get_run_string(dev, bench_params, self.jobname))

    def report(self, dev, path):
        filename = path + "/" + self.jobname + ".txt"
        entries = self.get_result_from_test(filename, 'fillrandom')

        csv_file = path + "/rocksdb.csv"
        self.create_csv_file(csv_file)

        with open(csv_file, 'a') as f:
            w = csv.writer(f, delimiter=',')
            w.writerow((entries[0], entries[4], entries[6]))

        print("  Output written to: %s" % csv_file)


class RocksDBOverwrite(RocksDBBase):
    def __init__(self):
        self.jobname = "rocksdb_overwrite"
        pass

    def setup(self, dev, container, output):
        super(RocksDBOverwrite, self).setup(output, container)

    def run(self, dev, container):
        num = str(int(self.scale_num * 0.1))

        bench_params = " --benchmarks=overwrite,stats --use_existing_db",  \
                       " --num=", num, \
                       " --duration=", self.overwrite_duration


        self.run_cmd(dev, container, 'db_bench', self.get_run_string(dev, bench_params, self.jobname))

    def report(self, dev, path):
        filename = path + "/" + self.jobname + ".txt"
        entries = self.get_result_from_test(filename, 'overwrite')

        csv_file = path + "/rocksdb.csv"
        self.create_csv_file(csv_file)

        with open(csv_file, 'a') as f:
            w = csv.writer(f, delimiter=',')
            w.writerow((entries[0], entries[4], entries[6]))

        print("  Output written to: %s" % csv_file)

class RocksDBReadwhilewriting(RocksDBBase):
    def __init__(self):
        self.jobname = "rocksdb_readwhilewriting"
        pass

    def setup(self, dev, container, output):
        super(RocksDBReadwhilewriting, self).setup(output, container)

    def run(self, dev, container):

        for runid in [1, 2, 3]:
            bench_params = " --benchmarks=readrandom,stats", \
                           " --use_existing_db --histogram --threads=32",  \
                           " --duration=", self.read_duration

            self.run_cmd(dev, container, 'db_bench', self.get_run_string(dev, bench_params, "rocksdb_readwhilewriting_readrandom_%s" % runid))

            bench_params = " --benchmarks=readwhilewriting,stats", \
                           " --use_existing_db --histogram --threads=32",  \
                           " --duration=", self.read_duration

            self.run_cmd(dev, container, 'db_bench', self.get_run_string(dev, bench_params, "rocksdb_readwhilewriting_write_%s" % runid))

            bench_params = " --benchmarks=readwhilewriting,stats", \
                           " --use_existing_db --histogram --threads=32",  \
                           " --duration=", self.read_duration, \
                           " --benchmark_write_rate_limit=", self.write_limit

            self.run_cmd(dev, container, 'db_bench', self.get_run_string(dev, bench_params, "rocksdb_readwhilewriting_writelimit_%s" % runid))

    def report_bench(self, path, file_bench, bench):
        csv_file = path + "/rocksdb.csv"
        self.create_csv_file(csv_file)

        with open(csv_file, 'a') as f:
            results = []

            for runid in [1, 2, 3]:
                filename = path + "/" + self.jobname + "_" + file_bench + "_" + str(runid) + ".txt"
                entries = self.get_result_from_test(filename, bench)
                writes = self.get_result_from_test(filename, 'Cumulative writes')

                results.append((file_bench, float(entries[4]), float(entries[6]), float(writes[17])))

            micros = mean(list(zip(*results))[1])
            ops = mean(list(zip(*results))[2])
            mbs = mean(list(zip(*results))[3])

            w = csv.writer(f, delimiter=',')
            w.writerow(('readwhilewriting_' + file_bench, micros, ops, mbs))

        return csv_file

    def report(self, dev, path):
        self.report_bench(path, 'readrandom', 'readrandom')
        self.report_bench(path, 'write', 'readwhilewriting')
        csv_file = self.report_bench(path, 'writelimit', 'readwhilewriting')

        print("  Output written to: %s" % (csv_file))
        return csv_file

# Fill must be first, as it initialized zenfs
base_benches.append(RocksDBFillPrep())
base_benches.append(RocksDBOverwrite())
base_benches.append(RocksDBReadwhilewriting())

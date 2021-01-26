import json
import csv
import sys
import glob
from .base import base_benches, Bench
from benchs.base import is_dev_zoned

class Run(Bench):
    jobname = "fio_zone_throughput_avg_lat"

    def __init__(self):
        pass

    def id(self):
        return self.jobname

    def setup(self, dev, container, output):
        super(Run, self).setup(output)

        self.discard_dev(dev)

    def run(self, dev, container):
        extra = ''

        if is_dev_zoned(dev):
            # Zone Capacity (52% of zone size)
            zonecap=52
            zonesize=self.get_zone_size_mb(dev)
        else:
            print("This test is ment to be run on a zoned dev")
            sys.exit(1)
        
        #write/read 2 zones for this benchmark
        size = zonesize * 2 
        max_size = int(((self.get_dev_size(dev) * zonecap) / 100) * 2)
        if max_size < size:
            size = max_size
        io_size = size

        for operation in ["write", "randwrite", "read", "randread"]:
            max_open_zones_list = [1, 2, 4, 8, 16]
            if "read" in operation:
                max_open_zones_list = [1]
                print("About to prep the drive for read job")
                self.discard_dev(dev)
                init_param = ("--ioengine=io_uring --direct=1 --zonemode=zbd"
                            " --output-format=json"
                            " --max_open_zones=2"
                            " --filename=%s "
                            " --rw=write --bs=64K --iodepth=4"
                            " %s") %  (dev, extra)

                prep_param = ("--name=prep "
                            " --size=%sM"
                            " --output output/%s_prep.log") % (size, operation)

                fio_param = "%s %s" % (init_param, prep_param)

                self.run_cmd(dev, container, 'fio', fio_param)
                print("Finished preping the drive")

            for max_open_zones in max_open_zones_list:
                for queue_depth in [1, 4, 16, 64]:
                    for block_size in ["4K", "8K", "16K", "64K", "128K"]:
                        output_name = ("%s-%s-%s-%s-%s") % (operation, max_open_zones, queue_depth, block_size, self.jobname)
                        print("About to start job %s" % output_name)
                        if "write" in operation:
                            self.discard_dev(dev)
                        init_param = ("--ioengine=io_uring --direct=1 --zonemode=zbd"
                                    " --output-format=json"
                                    " --max_open_zones=%s"
                                    " --filename=%s "
                                    " --rw=%s --bs=%s --iodepth=%s"
                                    " %s") % (max_open_zones, dev, operation, block_size, queue_depth, extra)

                        exec_param = ("--name=%s "
                                    " --size=%sM"
                                    " --output output/%s.log") % (operation, size, output_name)
                        fio_param = "%s %s" % (init_param, exec_param)

                        self.run_cmd(dev, container, 'fio', fio_param)
                        print("Finished job")

    def teardown(self, dev, container):
        pass

    def report(self, path):

        csv_data = []
        for log in (glob.glob(path + "/*.log")):
            with open(log, 'r') as f:
                try:
                    data = json.load(f)
                except:
                    print("Sktipping %s because it does not contain a json" % log)
                    continue

            for job in data['jobs']:
                avg_lat_us = 0
                throughput = 0 
                runtime = 0
                io_MiB = 0

                if "prep" in job['jobname']:
                    continue

                if "write" in job['jobname']:
                    avg_lat_us = "%0.3f" % float(job['write']['lat_ns']['mean'] / 1000.0)
                    io_MiB = float(job['write']['io_bytes'] / 1024.0 / 1024.0)
                    runtime = float(job['write']['runtime'])
                else:
                    avg_lat_us = "%0.3f" % float(job['read']['lat_ns']['mean'] / 1000.0)
                    io_MiB = float(job['read']['io_bytes'] / 1024.0 / 1024.0)
                    runtime = float(job['read']['runtime'])
               
                if runtime > 0:
                    throughput = "%0.3f" % float(io_MiB / (runtime / 1000.0))
                job_name = log[log.rindex('/')+1:]
                options = job_name.split("-")
                t = [options[0], options[1], options[2], options[3], avg_lat_us, throughput]
                csv_data.append(t)

        csv_file = path + "/" + self.jobname + ".csv"
        with open(csv_file, 'w') as f:
            w = csv.writer(f, delimiter=',')
            w.writerow(['operation', 'max_open_zones', 'queue_depth', 'block_size', 'avg_lat_us', 'throughput_MiBs'])
            w.writerows(csv_data)

        print("  Output written to: %s" % csv_file)

base_benches.append(Run())



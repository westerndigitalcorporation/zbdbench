import csv
import sys
from statistics import mean
from .base import base_benches, Bench
from benchs.base import is_dev_zoned

class Run(Bench):
    jobname = "fio_zone_write"
    loops = 6

    def __init__(self):
        pass

    def id(self):
        return self.jobname

    def setup(self, dev, container, output):
        super(Run, self).setup(output)

        self.discard_dev(dev)

    def required_container_tools(self):
        return super().required_container_tools() |  {'fio'}

    def run(self, dev, container):
        extra = ''
        max_open_zones = 14

        if is_dev_zoned(dev):
            # Zone Capacity (52% of zone size)
            zonecap=52
        else:
            # Zone Size = Zone Capacity on a conv. drive
            zonecap=100
            extra = '--zonesize=1102848k'

        io_size = int(((self.get_dev_size(dev) * zonecap) / 100) * self.loops)

        fio_param = ("--filename=%s"
                    " --io_size=%sk"
                    " --log_avg_msec=1000"
                    " --write_bw_log=output/fio_zone_write"
                    " --output=output/fio_zone_write.log"
                    " --ioengine=libaio --direct=1 --zonemode=zbd"
                    " --name=seqwriter --rw=randwrite"
                    " --bs=64k --max_open_zones=%s %s") % (dev, io_size, max_open_zones, extra)

        self.run_cmd(dev, container, 'fio', fio_param)

    def teardown(self, dev, container):
        pass

    def get_drive_size_gb(self, path):
        filename = path + "/nvme_id-ns.txt"
        with open(filename, 'r') as f:
            for l in f:
                if 'nvmcap' in l:
                    return int(int(l.strip("nvmcap  : ")) / 1024 / 1024 / 1024)
        return None

    def report(self, path):

        devsize = self.get_drive_size_gb(path)
        if devsize is None:
            print("Could not get drive size for report")
            sys.exit(1)

        dp = []
        dy = []

        filename = (path + "/" + self.jobname + "_bw.1.log")
        with open(filename, 'r') as f:
            data = csv.reader(f, delimiter=',')
            for n in data:
                dy.append(int(n[1]) / 1024)

        ds = range(0, devsize)
        sum_max = sum(dy) / devsize

        spill = 0
        prev = 0
        for i in enumerate(ds):
            s = spill
            new_prev = prev
            while s < sum_max and new_prev < len(dy):
                s = s + dy[new_prev]
                if s < sum_max:
                    new_prev += 1
                else:
                    spill = s - sum_max

            dp.append(int(mean(dy[prev:new_prev])))
            prev = new_prev + 1

        dsx = [i * self.loops for i in ds]

        csv_file = path + "/" + self.jobname + ".csv"
        with open(csv_file, 'w') as csvfile:
            cw = csv.writer(csvfile, delimiter=',')
            cw.writerow(['written_gb', 'write_avg_mbs'])
            cw.writerows(list(map(list, zip(*[dsx, dp]))))

        print("  Output written to: %s" % csv_file)
        return csv_file

base_benches.append(Run())

import json
import csv
from .base import base_benches, Bench, DeviceScheduler
from benchs.base import is_dev_zoned

class Run(Bench):
    jobname = "fio_zone_mixed"

    def __init__(self):
        pass

    def get_default_device_scheduler(self):
        return DeviceScheduler.MQ_DEADLINE

    def id(self):
        return self.jobname

    def setup(self, dev, container, output):
        super(Run, self).setup(container, output)

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

        io_size = int(((self.get_dev_size(dev) * zonecap) / 100) * 2)

        init_param = ("--ioengine=io_uring --direct=1 --zonemode=zbd"
                    " --output-format=json"
                    " --max_open_zones=%s"
                    " --filename=%s "
                    " --rw=randwrite --bs=16k --iodepth=8"
                    " %s") % (max_open_zones, dev, extra)

        prep_param = ("--name=prep "
                    " --io_size=%sk"
                    " --output %s/%s.log") % (io_size, self.result_path(), self.jobname)

        mixs_param = "--name=mix_0_r --wait_for_previous --rw=randread --bs=4k --runtime=180 --ramp_time=30 --time_based --significant_figures=6 --percentile_list=1:5:10:20:30:40:50:60:70:80:90:99:99.9:99.99:99.999:99.9999:99.99999:100 "
        for s in [25, 50, 75, 100, 125, 150, 175, 200, 300, 400, 500, 600, 700, 800, 900, 1000]:
            mixs_param += ("--name=mix_%s_w --wait_for_previous --rate=%sm --iodepth=8 --bs=16k --runtime=180 --time_based"
                " --name=mix_%s_r --rw=randread --bs=4k --runtime=180 --ramp_time=30 --time_based --significant_figures=6 --percentile_list=1:5:10:20:30:40:50:60:70:80:90:99:99.9:99.99:99.999:99.9999:99.99999:100 ") % (s, s, s)

        fio_param = "%s %s %s" % (init_param, prep_param, mixs_param)

        self.run_cmd(dev, container, 'fio', fio_param)

    def teardown(self, dev, container):
        pass

    def report(self, path):

        csv_data = []
        with open(path + "/" + self.jobname + ".log", 'r') as f:
            data = json.load(f)

        write_avg = 0
        for job in data['jobs']:
            if "prep" in job['jobname']:
                continue

            if "w" in job['jobname']:
                write_avg = int(int(job['write']['bw_mean']) / 1024)
                continue


            write_target = int(job['jobname'].strip("mix_").strip("_r"))
            lat_us = "%0.3f" % float(job['read']['lat_ns']['mean'] / 1000)
            p = []
            p.append(int(job['read']['bw']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['1.000000']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['5.000000']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['10.000000']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['20.000000']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['30.000000']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['40.000000']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['50.000000']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['60.000000']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['70.000000']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['80.000000']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['90.000000']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['99.000000']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['99.900000']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['99.990000']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['99.999000']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['99.999900']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['99.999990']) / 1000)
            p.append(int(job['read']['clat_ns']['percentile']['100.000000']) / 1000)

            lat_reported = ''
            if write_target == write_avg:
                lat_reported = lat_us

            t = [write_target, lat_reported, write_avg, lat_us]
            t.extend(p)

            csv_data.append(t)

        csv_file = path + "/" + self.jobname + ".csv"
        with open(csv_file, 'w') as f:
            w = csv.writer(f, delimiter=',')
            w.writerow(['write_avg_mbs_target', 'read_lat_avg_us', 'write_avg_mbs', 'read_lat_avg_us_measured', 'read_avg_mbs', \
                        'clat_p1_us','clat_p5_us', 'clat_p10_us', 'clat_p20_us', 'clat_p30_us', 'clat_p40_us', \
                        'clat_p50_us','clat_p60_us','clat_p70_us','clat_p80_us', \
                        'clat_p90_us', 'clat_p99_us','clat_p99.9_us','clat_p99.99_us', 'clat_p99.999_us', \
                        'clat_p99.9999_us', 'clat_p99.99999_us', 'clat_max_us'])
            w.writerows(csv_data)

        print("  Output written to: %s" % csv_file)
        return csv_file

base_benches.append(Run())

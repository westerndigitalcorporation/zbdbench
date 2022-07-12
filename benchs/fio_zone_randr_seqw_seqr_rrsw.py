import json
import csv
from .base import base_benches, Bench, DeviceScheduler
from benchs.base import is_dev_zoned

class Run(Bench):
    jobname = "fio_zone_randr_seqw_seqr_rrsw"

    def __init__(self):
        pass

    def get_default_device_scheduler(self):
        return DeviceScheduler.NONE

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
        output_path_prefix = "output"

        if container == 'no':
            output_path_prefix = self.output

        if is_dev_zoned(dev):
            # Zone Capacity (52% of zone size)
            zonecap=52
            io_size = int(((self.get_zone_capacity_mb(dev) * self.get_number_of_zones(dev) * 1024 * 1024) * 3))
        else:
            # Zone Size = Zone Capacity on a conv. drive
            zonecap=100
            extra = '--zonesize=1102848k'
            io_size = int(((self.get_dev_size(dev) * zonecap) / 100) * 3)
        # Get correct offset to avoid rounding up/down msg from fio, which causes parsing issues
        offset1 = int(int(self.get_number_of_zones(dev) / 4) * 0 * self.get_zone_size_mb(dev))
        offset2 = int(int(self.get_number_of_zones(dev) / 4) * 1 * self.get_zone_size_mb(dev))
        offset3 = int(int(self.get_number_of_zones(dev) / 4) * 2 * self.get_zone_size_mb(dev))
        offset4 = int(int(self.get_number_of_zones(dev) / 4) * 3 * self.get_zone_size_mb(dev))

        init_param = ("--ioengine=io_uring --direct=1 --zonemode=zbd"
                    " --output-format=json"
                    " --max_open_zones=%s"
                    " --filename=%s"
                    " --output %s/%s.log"
                    " %s") % (max_open_zones, dev, output_path_prefix, self.jobname, extra)
        prep_param = ("--name=prep "
                    " --io_size=%s"
                    " --rw=write "
                    " --bs=16k --iodepth=64"
                    " --output %s/%s_prep.log") % (io_size, output_path_prefix, self.jobname)
        fio_param = "%s %s" % (init_param, prep_param)
        self.run_cmd(dev, container, 'fio', fio_param)

        print("Prep Done...")

        init_param_rr = ("--ioengine=io_uring --direct=1 --zonemode=zbd"
                    " --output-format=json"
                    " --rw=randread --bs=4k --ramp_time=30 --time_based --runtime=180 --significant_figures=6"
                    " --percentile_list=1:5:10:20:30:40:50:60:70:80:90:99:99.9:99.99:99.999:99.9999:99.99999:100"
                    " --group_reporting"
                    " --filename=%s"
                    " --output %s/%s_rr.log"
                    " %s") % (dev, output_path_prefix, self.jobname, extra)
        # Use offset2 to define size
        rr_param = (" --name=4K_R_READ_256QD_1 --offset=%sm --size=%sm --iodepth=64") % (offset1,  offset3)
        rr_param += (" --name=4K_R_READ_256QD_2 --offset=%sm --size=%sm --iodepth=64") % (offset1, offset3)
        rr_param += (" --name=4K_R_READ_256QD_3 --offset=%sm --size=%sm --iodepth=64") % (offset3, offset2)
        rr_param += (" --name=4K_R_READ_256QD_4 --offset=%sm --size=%sm --iodepth=64") % (offset4, offset2)

        fio_param_rr = "%s %s" % (init_param_rr, rr_param)
        self.run_cmd(dev, container, 'fio', fio_param_rr)

        rw_param = (" --name=128K_S_READ_QD64"
                    " --wait_for_previous --rw=read --bs=128k --iodepth=64 --ramp_time=30 --time_based --runtime=180 --significant_figures=6 --percentile_list=1:5:10:20:30:40:50:60:70:80:90:99:99.9:99.99:99.999:99.9999:99.99999:99.999999:100 ")

        rw_param += (" --name=128K_70-30_R_READ_S_WRITE_QD64"
                    " --wait_for_previous --rw=randrw --rwmixread=70 --bs=128k --iodepth=64 --ramp_time=30 --time_based --runtime=180 --significant_figures=6 --percentile_list=1:5:10:20:30:40:50:60:70:80:90:99:99.9:99.99:99.999:99.9999:99.99999:100")
        rw_param += (" --name=128KB_S_WRITE_QD64"
                  " --wait_for_previous --rw=write --bs=128k --iodepth=64 --ramp_time=30 --time_based --runtime=180 --significant_figures=6 --percentile_list=1:5:10:20:30:40:50:60:70:80:90:99:99.9:99.99:99.999:99.9999:99.99999:100 ")

        fio_param = "%s %s" % (init_param, rw_param)
        self.run_cmd(dev, container, 'fio', fio_param)

    def teardown(self, dev, container):
        pass

    def report(self, dev, path):

        csv_data = []

        with open(path + "/" + self.jobname + "_rr.log", 'r') as f1:
            data_rr = json.load(f1)

        for job_rr in data_rr['jobs']:
            write_avg_bw = int(int(job_rr['write']['bw_mean']) / 1024)
            write_lat_us = "%0.3f" % float(job_rr['write']['lat_ns']['mean'] / 1000)
            write_iops = int(job_rr['write']['iops'])
            read_avg_bw = int(int(job_rr['read']['bw_mean']) / 1024)
            read_lat_us = "%0.3f" % float(job_rr['read']['lat_ns']['mean'] / 1000)
            read_iops = int(job_rr['read']['iops'])

            prr = []
            if "4K_R_READ_256QD" in job_rr['jobname']:
                prr.append(int(job_rr['read']['bw']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['1.000000']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['5.000000']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['10.000000']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['20.000000']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['30.000000']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['40.000000']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['50.000000']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['60.000000']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['70.000000']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['80.000000']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['90.000000']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['99.000000']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['99.900000']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['99.990000']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['99.999000']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['99.999900']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['99.999990']) / 1000)
                prr.append(int(job_rr['read']['clat_ns']['percentile']['100.000000']) / 1000)
                trr = [read_avg_bw, read_lat_us, write_avg_bw, write_lat_us, read_iops, write_iops]
                trr.extend(prr)
                csv_data.append(trr)
                

        with open(path + "/" + self.jobname + ".log", 'r') as f:
            data = json.load(f)

        for job in data['jobs']:
            if "prep" in job['jobname']:
                continue

            write_avg_bw = int(int(job['write']['bw_mean']) / 1024)
            write_lat_us = "%0.3f" % float(job['write']['lat_ns']['mean'] / 1000)
            write_iops = int(job['write']['iops'])
            read_avg_bw = int(int(job['read']['bw_mean']) / 1024)
            read_lat_us = "%0.3f" % float(job['read']['lat_ns']['mean'] / 1000)
            read_iops = int(job['read']['iops'])
            pr = []
            pw = []
            if "READ" in job['jobname']:
                pr.append(int(job['read']['bw']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['1.000000']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['5.000000']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['10.000000']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['20.000000']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['30.000000']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['40.000000']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['50.000000']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['60.000000']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['70.000000']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['80.000000']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['90.000000']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['99.000000']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['99.900000']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['99.990000']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['99.999000']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['99.999900']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['99.999990']) / 1000)
                pr.append(int(job['read']['clat_ns']['percentile']['100.000000']) / 1000)
                tr = [read_avg_bw, read_lat_us, write_avg_bw, write_lat_us, read_iops, write_iops]
                tr.extend(pr)
                csv_data.append(tr)


            if "WRITE" in job['jobname']:
                pw.append(int(job['write']['bw']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['1.000000']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['5.000000']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['10.000000']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['20.000000']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['30.000000']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['40.000000']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['50.000000']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['60.000000']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['70.000000']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['80.000000']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['90.000000']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['99.000000']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['99.900000']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['99.990000']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['99.999000']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['99.999900']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['99.999990']) / 1000)
                pw.append(int(job['write']['clat_ns']['percentile']['100.000000']) / 1000)
                tw = [read_avg_bw, read_lat_us, write_avg_bw, write_lat_us, read_iops, write_iops]
                tw.extend(pw)
                csv_data.append(tw)

         
        csv_file = path + "/" + self.jobname + ".csv"
        with open(csv_file, 'w') as f:
            w = csv.writer(f, delimiter=',')
            w.writerow(['read_avg_mbs', 'read_lat_avg_us', 'write_avg_mbs', 'write_lat_avg_us', 'read_iops', 'write_iops', \
                        'clat_p1_us','clat_p5_us', 'clat_p10_us', 'clat_p20_us', 'clat_p30_us', 'clat_p40_us', \
                        'clat_p50_us','clat_p60_us','clat_p70_us','clat_p80_us', \
                        'clat_p90_us', 'clat_p99_us','clat_p99.9_us','clat_p99.99_us', 'clat_p99.999_us', \
                        'clat_p99.9999_us', 'clat_p99.99999_us', 'clat_max_us'])
            w.writerows(csv_data)

        print("  Output written to: %s" % csv_file)
        return csv_file

base_benches.append(Run())

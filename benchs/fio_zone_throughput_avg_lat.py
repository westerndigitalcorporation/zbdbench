import json
import csv
import sys
import glob
import matplotlib.pyplot as plt
from .base import base_benches, Bench, Plot
from benchs.base import is_dev_zoned

class BenchPlot(Plot):

    def __init__(self, csv_file):
        super().__init__(csv_file)
        self.headline_additions = "All test runs where executed with the size of two times of the devices zone size.\nThe runs where executed twice, the reported numbers are averaged over these two runs."

    def generateBarGraph(self, operation, value_of_interest, comparison_csv_file=""):
        filter_dict = {}
        filter_dict['operation'] = [operation]
        #Label consits of the values form columns 1, 2 and 3 for a given row
        label_row_items = list(range(1, 4))
        self.setupGenericBarGraph(filter_dict, value_of_interest, label_row_items, comparison_csv_file, (25, 10))

        if value_of_interest == "throughput_MiBs":
            plt.title("Throughput [MiBs] on %s.\n%s" % (operation, self.headline_additions))
            plt.ylabel("Throughput [MiBs]")
            self.saveInOutputDir(("Throughput_%s.pdf" % operation))
        elif value_of_interest == "avg_lat_us":
            plt.title("Average Latency [µs] on %s.\n%s" % (operation, self.headline_additions))
            plt.ylabel("Average Latency [µs]")
            self.saveInOutputDir(("AverageLatency_%s.pdf" % operation))
        else:
            plt.title("%s on %s.\n%s" % (value_of_interest, operation, self.headline_additions))
            plt.ylabel(value_of_interest)
            self.saveInOutputDir(("%s_%s.pdf" % (value_of_interest, operation)))

    def generateBlockSizeGraph(self, operation, max_open_zones, value_of_interest):
        self.resetPlot()
        benchmarkRows = csv.DictReader(open(self.csv_file))
        y_values_QD1 = []
        y_values_QD2 = []
        y_values_QD4 = []
        y_values_QD8 = []
        y_values_QD16 = []
        y_values_QD32 = []
        y_values_QD64 = []

        x_ticks = ["4", "8", "16", "64", "128"]
        x_values = [4, 8, 16, 64, 128]
        for row in benchmarkRows:
            if row['operation'] == operation and row['max_open_zones'] == max_open_zones:
                if row['queue_depth'] == "1":
                    y_values_QD1.append(int(row[value_of_interest]))
                elif row['queue_depth'] == "2":
                    y_values_QD2.append(int(row[value_of_interest]))
                elif row['queue_depth'] == "4":
                    y_values_QD4.append(int(row[value_of_interest]))
                elif row['queue_depth'] == "8":
                    y_values_QD8.append(int(row[value_of_interest]))
                elif row['queue_depth'] == "16":
                    y_values_QD16.append(int(row[value_of_interest]))
                elif row['queue_depth'] == "32":
                    y_values_QD32.append(int(row[value_of_interest]))
                elif row['queue_depth'] == "64":
                    y_values_QD64.append(int(row[value_of_interest]))

        plt.figure(figsize=(20,9))
        plt.xticks(x_values, x_ticks)
        label_additions = ""
        if "write" in operation:
            label_additions = str(", max_open_zones=%s" % max_open_zones)

        if len(y_values_QD1) == len(x_values):
            plt.plot(x_values, y_values_QD1, '-mo', label=("QD=1%s" % label_additions) )
        if len(y_values_QD2) == len(x_values):
            plt.plot(x_values, y_values_QD2, '-gs', label=("QD=2%s" % label_additions) )
        if len(y_values_QD4) == len(x_values):
            plt.plot(x_values, y_values_QD4, '-yv', label=("QD=4%s" % label_additions) )
        if len(y_values_QD8) == len(x_values):
            plt.plot(x_values, y_values_QD8, '-bd', label=("QD=8%s" % label_additions) )
        if len(y_values_QD16) == len(x_values):
            plt.plot(x_values, y_values_QD16, '-rx', label=("QD=16%s" % label_additions) )
        if len(y_values_QD32) == len(x_values):
            plt.plot(x_values, y_values_QD32, '-c8', label=("QD=32%s" % label_additions) )
        if len(y_values_QD64) == len(x_values):
            plt.plot(x_values, y_values_QD64, '-k4', label=("QD=64%s" % label_additions) )
        plt.legend()
        plt.xlabel("Block Size [KiB]")

        if value_of_interest == "throughput_MiBs":
            plt.title("Throughput [MiBs] on %s.\n%s" % (operation, self.headline_additions))
            plt.ylabel("Throughput [MiBs]")
            self.saveInOutputDir(("Throughput_%s_MOZ%s.pdf" % (operation, max_open_zones)))
        elif value_of_interest == "avg_lat_us":
            plt.title("Average Latency [µs] on %s.\n%s" % (operation, self.headline_additions))
            plt.ylabel("Average Latency [µs]")
            self.saveInOutputDir(("AverageLatency_%sMOZ%s.pdf" % (operation, max_open_zones)))

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
        runs = 2
        max_size = int(((self.get_dev_size(dev) * zonecap) / 100) * 2)
        if max_size < size:
            size = max_size
        io_size = size

        for operation in ["write", "randwrite", "read", "randread"]:
            max_open_zones_list = [1, 2, 4, 8, 12]
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
                for queue_depth in [1, 2, 4, 8, 16, 32, 64]:
                    if max_open_zones > queue_depth:
                        continue

                    for block_size in ["4K", "8K", "16K", "64K", "128K"]:
                        for run in range(1, runs+1):
                            output_name = ("%s-%s-%s-%s-%s-%sof%s") % (operation, max_open_zones, queue_depth, block_size, self.jobname, run, runs)
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
                                        " --percentile_list=1:5:10:20:30:40:50:60:70:80:90:99:99.9:99.99:99.999:99.9999:99.99999:100"
                                        " --output output/%s.log") % (operation, size, output_name)
                            fio_param = "%s %s" % (init_param, exec_param)

                            self.run_cmd(dev, container, 'fio', fio_param)
                            print("Finished job")

    def teardown(self, dev, container):
        pass

    def report(self, path):

        csv_data = []
        csv_row = []
        logs = glob.glob(path + "/*.log")
        logs.sort()
        for log in logs:
            with open(log, 'r') as f:
                try:
                    data = json.load(f)
                except:
                    print("Sktipping %s because it does not contain a json" % log)
                    continue

            options = log[log.rindex('/')+1:].split("-")
            for job in data['jobs']:
                avg_lat_us = 0
                throughput = 0
                runtime = 0
                io_MiB = 0
                operation = "read"

                if "prep" in job['jobname']:
                    continue

                run = int(options[5].split("of")[0])
                runs = int((options[5].split("of")[1])[:-4])

                if "write" in job['jobname']:
                    operation = "write"
                    avg_lat_us = float(job['write']['lat_ns']['mean'] / 1000.0)
                    io_MiB = float(job['write']['io_bytes'] / 1024.0 / 1024.0)
                    runtime = float(job['write']['runtime'])
                else:
                    avg_lat_us = float(job['read']['lat_ns']['mean'] / 1000.0)
                    io_MiB = float(job['read']['io_bytes'] / 1024.0 / 1024.0)
                    runtime = float(job['read']['runtime'])

                if runtime > 0:
                    throughput = float(io_MiB / (runtime / 1000.0))

                p0 = int(job[operation]['clat_ns']['percentile']['1.000000']) / 1000
                p1 = int(job[operation]['clat_ns']['percentile']['5.000000']) / 1000
                p2 = int(job[operation]['clat_ns']['percentile']['10.000000']) / 1000
                p3 = int(job[operation]['clat_ns']['percentile']['20.000000']) / 1000
                p4 = int(job[operation]['clat_ns']['percentile']['30.000000']) / 1000
                p5 = int(job[operation]['clat_ns']['percentile']['40.000000']) / 1000
                p6 = int(job[operation]['clat_ns']['percentile']['50.000000']) / 1000
                p7 = int(job[operation]['clat_ns']['percentile']['60.000000']) / 1000
                p8 = int(job[operation]['clat_ns']['percentile']['70.000000']) / 1000
                p9 = int(job[operation]['clat_ns']['percentile']['80.000000']) / 1000
                p10 = int(job[operation]['clat_ns']['percentile']['90.000000']) / 1000
                p11 = int(job[operation]['clat_ns']['percentile']['99.000000']) / 1000
                p12 = int(job[operation]['clat_ns']['percentile']['99.900000']) / 1000
                p13 = int(job[operation]['clat_ns']['percentile']['99.990000']) / 1000
                p14 = int(job[operation]['clat_ns']['percentile']['99.999000']) / 1000
                p15 = int(job[operation]['clat_ns']['percentile']['99.999900']) / 1000
                p16 = int(job[operation]['clat_ns']['percentile']['99.999990']) / 1000
                p17 = int(job[operation]['clat_ns']['percentile']['100.000000']) / 1000
                #logs are sorted
                if run == 1:
                    globalOptions = data['global options']
                    csv_row = []
                    csv_row.append(options[0])
                    csv_row.append(globalOptions['max_open_zones'])
                    csv_row.append(globalOptions['iodepth'])
                    csv_row.append(globalOptions['bs'])
                    csv_row.append(avg_lat_us)
                    csv_row.append(throughput)
                    csv_row.append(p0)
                    csv_row.append(p1)
                    csv_row.append(p2)
                    csv_row.append(p3)
                    csv_row.append(p4)
                    csv_row.append(p5)
                    csv_row.append(p6)
                    csv_row.append(p7)
                    csv_row.append(p8)
                    csv_row.append(p9)
                    csv_row.append(p10)
                    csv_row.append(p11)
                    csv_row.append(p12)
                    csv_row.append(p13)
                    csv_row.append(p14)
                    csv_row.append(p15)
                    csv_row.append(p16)
                    csv_row.append(p17)
                else:
                    csv_row[4] += avg_lat_us
                    csv_row[5] += throughput
                    csv_row[6] += p0
                    csv_row[7] += p1
                    csv_row[8] += p2
                    csv_row[9] += p3
                    csv_row[10] += p4
                    csv_row[11] += p5
                    csv_row[12] += p6
                    csv_row[13] += p7
                    csv_row[14] += p8
                    csv_row[15] += p9
                    csv_row[16] += p10
                    csv_row[17] += p11
                    csv_row[18] += p12
                    csv_row[19] += p13
                    csv_row[20] += p14
                    csv_row[21] += p15
                    csv_row[22] += p16
                    csv_row[23] += p17

                if run == runs:
                    csv_row[4] = str(int(round(csv_row[4] / runs)))
                    csv_row[5] = str(int(round(csv_row[5] / runs)))
                    csv_row[6] = str(int(round(csv_row[6] / runs)))
                    csv_row[7] = str(int(round(csv_row[7] / runs)))
                    csv_row[8] = str(int(round(csv_row[8] / runs)))
                    csv_row[9] = str(int(round(csv_row[9] / runs)))
                    csv_row[10] = str(int(round(csv_row[10] / runs)))
                    csv_row[11] = str(int(round(csv_row[11] / runs)))
                    csv_row[12] = str(int(round(csv_row[12] / runs)))
                    csv_row[13] = str(int(round(csv_row[13] / runs)))
                    csv_row[14] = str(int(round(csv_row[14] / runs)))
                    csv_row[15] = str(int(round(csv_row[15] / runs)))
                    csv_row[16] = str(int(round(csv_row[16] / runs)))
                    csv_row[17] = str(int(round(csv_row[17] / runs)))
                    csv_row[18] = str(int(round(csv_row[18] / runs)))
                    csv_row[19] = str(int(round(csv_row[19] / runs)))
                    csv_row[20] = str(int(round(csv_row[20] / runs)))
                    csv_row[21] = str(int(round(csv_row[21] / runs)))
                    csv_row[22] = str(int(round(csv_row[22] / runs)))
                    csv_row[23] = str(int(round(csv_row[23] / runs)))
                    csv_data.append(csv_row)

        csv_file = path + "/" + self.jobname + ".csv"
        with open(csv_file, 'w') as f:
            w = csv.writer(f, delimiter=',')
            w.writerow(['operation', 'max_open_zones', 'queue_depth', 'block_size_K', 'avg_lat_us', 'throughput_MiBs', 'clat_p1_us', 'clat_p5_us', 'clat_p10_us', 'clat_p20_us', 'clat_p30_us', 'clat_p40_us', 'clat_p50_us', 'clat_p60_us', 'clat_p70_us', 'clat_p80_us', 'clat_p90_us', 'clat_p99_us', 'clat_p99.9_us', 'clat_p99.99_us', 'clat_p99.999_us', 'clat_p99.9999_us', 'clat_p99.99999_us', 'clat_p100_us'])
            w.writerows(csv_data)

        print("  Output written to: %s" % csv_file)
        return csv_file

    def plot(self, csv_file):
        plot = BenchPlot(csv_file)

        plot.generateBlockSizeGraph("write", "1", "throughput_MiBs")
        plot.generateBlockSizeGraph("write", "8", "throughput_MiBs")
        plot.generateBlockSizeGraph("randwrite", "1", "throughput_MiBs")
        plot.generateBlockSizeGraph("randwrite", "8", "throughput_MiBs")
        plot.generateBlockSizeGraph("read", "1", "throughput_MiBs")
        plot.generateBlockSizeGraph("randread", "1", "throughput_MiBs")

        plot.generateBlockSizeGraph("write", "1", "avg_lat_us")
        plot.generateBlockSizeGraph("write", "8", "avg_lat_us")
        plot.generateBlockSizeGraph("randwrite", "8", "avg_lat_us")
        plot.generateBlockSizeGraph("randwrite", "1", "avg_lat_us")
        plot.generateBlockSizeGraph("read", "1", "avg_lat_us")
        plot.generateBlockSizeGraph("randread", "1", "avg_lat_us")

        plot.generateBarGraph("read", "throughput_MiBs")
        plot.generateBarGraph("write", "throughput_MiBs")
        plot.generateBarGraph("randread", "throughput_MiBs")
        plot.generateBarGraph("readwrite", "throughput_MiBs")

        plot.generateBarGraph("read", "avg_lat_us")
        plot.generateBarGraph("write", "avg_lat_us")
        plot.generateBarGraph("randread", "avg_lat_us")
        plot.generateBarGraph("randwrite", "avg_lat_us")

        print("  Done generateing graphs")

base_benches.append(Run())



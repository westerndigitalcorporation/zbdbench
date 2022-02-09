import json
import csv
import sys
import glob
import re
import math
import matplotlib.pyplot as plt
from .base import base_benches, Bench, Plot
from benchs.base import is_dev_zoned

operation_list = ["read", "randread", "write"]
number_parallel_jobs_list = [1, 2, 4, 8, 14, 16, 32, 64, 128]
queue_depth_list = [1, 2, 4, 8, 14, 16, 32, 64, 128] #attention when adjusting: hardcoded sections in generateBlockSizeGraph
block_size_list = ["4K", "8K", "16K", "32K", "64K", "128K"]
block_size_K_list = [str(x[:-1]) for x in block_size_list]
fio_runtime = "30"
fio_ramptime = "15"
runs = 1
size = "9z"

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

    def generateBlockSizeGraph(self, operation, number_parallel_jobs_list, value_of_interest):
        self.resetPlot()
        benchmarkRows = csv.DictReader(open(self.csv_file))

        x_ticks = block_size_K_list
        x_values = [int(i) for i in x_ticks]

        y_values_QD1 = [-1] * len(x_ticks)
        y_values_QD2 = [-1] * len(x_ticks)
        y_values_QD4 = [-1] * len(x_ticks)
        y_values_QD8 = [-1] * len(x_ticks)
        y_values_QD14 = [-1] * len(x_ticks)
        y_values_QD16 = [-1] * len(x_ticks)
        y_values_QD32 = [-1] * len(x_ticks)
        y_values_QD64 = [-1] * len(x_ticks)
        y_values_QD128 = [-1] * len(x_ticks)
        for row in benchmarkRows:
            if row['operation'] == operation and row['number_parallel_jobs'] in  number_parallel_jobs_list:
                if row['queue_depth'] == "1":
                    y_values_QD1[x_ticks.index(row['block_size_K'])] = int(row[value_of_interest])
                elif row['queue_depth'] == "2":
                    y_values_QD2[x_ticks.index(row['block_size_K'])] = int(row[value_of_interest])
                elif row['queue_depth'] == "4":
                    y_values_QD4[x_ticks.index(row['block_size_K'])] = int(row[value_of_interest])
                elif row['queue_depth'] == "8":
                    y_values_QD8[x_ticks.index(row['block_size_K'])] = int(row[value_of_interest])
                elif row['queue_depth'] == "14":
                    y_values_QD14[x_ticks.index(row['block_size_K'])] = int(row[value_of_interest])
                elif row['queue_depth'] == "16":
                    y_values_QD16[x_ticks.index(row['block_size_K'])] = int(row[value_of_interest])
                elif row['queue_depth'] == "32":
                    y_values_QD32[x_ticks.index(row['block_size_K'])] = int(row[value_of_interest])
                elif row['queue_depth'] == "64":
                    y_values_QD64[x_ticks.index(row['block_size_K'])] = int(row[value_of_interest])
                elif row['queue_depth'] == "128":
                    y_values_QD128[x_ticks.index(row['block_size_K'])] = int(row[value_of_interest])

        plt.figure(figsize=(10,4.5))
        axis = plt.gca()
        axis.set_ylim([0, 5000])
        plt.xticks(x_values, x_ticks)
        label_additions = ""
        if "write" in operation:
            label_additions = ", Number of parallel jobs=QD"

        if -1 not in y_values_QD1:
            plt.plot(x_values, y_values_QD1, '-mo', label=("QD=1%s" % label_additions) )
        if -1 not in y_values_QD2:
            plt.plot(x_values, y_values_QD2, '-gs', label=("QD=2%s" % label_additions) )
        if -1 not in y_values_QD4:
            plt.plot(x_values, y_values_QD4, '-yv', label=("QD=4%s" % label_additions) )
        if -1 not in y_values_QD8:
            plt.plot(x_values, y_values_QD8, '-bd', label=("QD=8%s" % label_additions) )
        if -1 not in y_values_QD14:
            plt.plot(x_values, y_values_QD14, '-rx', label=("QD=14%s" % label_additions) )
        if -1 not in y_values_QD16:
            plt.plot(x_values, y_values_QD16, '-rx', label=("QD=16%s" % label_additions) )
        if -1 not in y_values_QD32:
            plt.plot(x_values, y_values_QD32, '-c8', label=("QD=32%s" % label_additions) )
        if -1 not in y_values_QD64:
            plt.plot(x_values, y_values_QD64, '-k4', label=("QD=64%s" % label_additions) )
        if -1 not in y_values_QD128:
            plt.plot(x_values, y_values_QD128, '-k4', label=("QD=128%s" % label_additions) )
        plt.legend()
        plt.xlabel("Block Size [KiB]")

        if value_of_interest == "throughput_MiBs":
            plt.title("Throughput [MiBs] on %s.\n%s" % (operation, self.headline_additions))
            plt.ylabel("Throughput [MiBs]")
            self.saveInOutputDir(("Throughput_%s_variableBS.pdf" % (operation)))
        elif value_of_interest == "avg_lat_us":
            plt.title("Average Latency [µs] on %s.\n%s" % (operation, self.headline_additions))
            plt.ylabel("Average Latency [µs]")
            self.saveInOutputDir(("AverageLatency_%s_variableBS.pdf" % (operation)))

    def generatePercentileGraph(self, pinned_variables):
        self.resetPlot()
        plt.figure(figsize=(10,4.5))
        benchmarkRows = csv.DictReader(open(self.csv_file))
        lines = []
        for row in benchmarkRows:
            row_of_interest = True
            for var_name, var_value in pinned_variables.items():
                if row[var_name] != var_value:
                    row_of_interest = False
                    break

            if row_of_interest:
                label = ""
                line = {}
                for k, v in row.items():
                    if 'clat_p' in k:
                        line[str(float(k.split('_')[1][1:]))] = v
                    else:
                        label += str(k) + ":" + str(v) + " "
                line['label'] = label[:-1]
                lines.append(line)

        if len(lines) == 0:
            self.resetPlot()
            return

        for line in lines:
            latency_line = dict(filter(lambda elem: 'label' not in elem[0], line.items()))
            values = [int(i) for i in latency_line.values()]
            keys = [float(i) for i in latency_line.keys()]
            plt.plot(values, keys, label=line['label'])

        plt.legend()
        axis = plt.gca()
        axis.set_xlim([0, 7000])
        plt.title("%s Latency Percentiles.\n%s" % (pinned_variables['operation'].capitalize(), self.headline_additions))
        plt.ylabel("Latency Percentiles")
        plt.xlabel("Average Latency [µs]")
        filename = "LatencyPercentiles_"
        for var_name, var_value in pinned_variables.items():
            filename += var_name + str(var_value) + "-"
        filename = filename[:-1] + ".pdf"
        self.saveInOutputDir(filename)

class Run(Bench):
    jobname = "fio_zone_throughput_avg_lat"

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
        global fio_runtime
        global fio_ramptime
        extra = ''

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

        for operation in operation_list:
            tmp_number_parallel_jobs_list = number_parallel_jobs_list

            if "read" in operation:
                if "randread" == operation:
                    tmp_number_parallel_jobs_list = [1]
                extra = ''
                print("About to prep the drive for read job")
                self.discard_dev(dev)
                init_param = ("--ioengine=psync --direct=1 --zonemode=zbd"
                            " --output-format=json"
                            " --filename=%s "
                            " --offset_increment=%sz --job_max_open_zone=1 --max_open_zones=%s --numjobs=%s --group_reporting"
                            " --rw=write --bs=128K"
                            " %s") %  (dev, increment_size, dev_max_open_zones, str(int(number_prep_jobs)), extra)

                prep_param = ("--name=prep "
                            " --size=%sz"
                            " --output output/%s_prep.log") % (increment_size, operation)

                fio_param = "%s %s" % (init_param, prep_param)

                self.run_cmd(dev, container, 'fio', fio_param)
                print("Finished preping the drive")

            for number_parallel_jobs in tmp_number_parallel_jobs_list:

                for queue_depth in queue_depth_list:
                    if number_parallel_jobs > queue_depth:
                        continue

                    if number_parallel_jobs * int(size[:-1]) > dev_number_zones:
                        print("Skipping number_parallel_jobs=%s because the device is to small for size=%s." % (str(number_parallel_jobs), size))
                        continue

                    if ("write" in operation or "read" == operation) and queue_depth > number_parallel_jobs:
                        continue

                    for block_size in block_size_list:
                        for run in range(1, runs+1):
                            extra = ''
                            output_name = ("%s-%s-%s-%s-%s-%sof%s") % (operation, number_parallel_jobs, queue_depth, block_size, self.jobname, run, runs)

                            ioengine = "io_uring"

                            extra = " --iodepth=%s " % queue_depth
                            if "randread" == operation:
                                fio_runtime = "15"

                            if "write" == operation or "read" == operation:
                                ioengine = "psync"
                                extra = " --offset_increment=%s --numjobs=%s --group_reporting "  % (size, queue_depth)

                            print("About to start job %s" % output_name)
                            if "write" in operation:
                                self.discard_dev(dev)

                            init_param = ("--ioengine=%s --direct=1 --zonemode=zbd"
                                        " --output-format=json"
                                        " --max_open_zones=%s"
                                        " --filename=%s"
                                        " --rw=%s --bs=%s"
                                        " %s") % (ioengine, dev_max_open_zones, dev, operation, block_size, extra)

                            exec_param = ("--name=%s "
                                        " --size=%s"
                                        " --time_based"
                                        " --ramp_time=%s --runtime=%s"
                                        " --percentile_list=1:5:10:20:30:40:50:60:70:80:90:99:99.9:99.99:99.999:99.9999:99.99999:100"
                                        " --output output/%s.log") % (operation, size, fio_ramptime, fio_runtime, output_name)
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
                    parallel_jobs = int(1)
                    if 'numjobs' in globalOptions:
                        parallel_jobs = int(globalOptions['numjobs'])
                    csv_row.append(parallel_jobs)
                    iodepth = int(1)
                    if 'iodepth' in globalOptions:
                        iodepth = int(globalOptions['iodepth'])
                    csv_row.append(iodepth)
                    #Cut SI prefix from bs for further processing
                    csv_row.append(re.sub('[a-zA-Z]', '', globalOptions['bs']))
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
            w.writerow(['operation', 'number_parallel_jobs', 'queue_depth', 'block_size_K', 'avg_lat_us', 'throughput_MiBs', 'clat_p1_us', 'clat_p5_us', 'clat_p10_us', 'clat_p20_us', 'clat_p30_us', 'clat_p40_us', 'clat_p50_us', 'clat_p60_us', 'clat_p70_us', 'clat_p80_us', 'clat_p90_us', 'clat_p99_us', 'clat_p99.9_us', 'clat_p99.99_us', 'clat_p99.999_us', 'clat_p99.9999_us', 'clat_p99.99999_us', 'clat_p100_us'])
            w.writerows(csv_data)

        print("  Output written to: %s" % csv_file)
        return csv_file

    def plot(self, csv_file):
        plot = BenchPlot(csv_file)
        for operation in operation_list:
            plot.generateBarGraph(operation, "throughput_MiBs")
            plot.generateBarGraph(operation, "avg_lat_us")

            if "write" in operation:
                plot.generateBlockSizeGraph(operation, [str(x) for x in number_parallel_jobs_list], "throughput_MiBs")
                plot.generateBlockSizeGraph(operation, [str(x) for x in number_parallel_jobs_list], "avg_lat_us")

            if "read" in operation:
                plot.generateBlockSizeGraph(operation, ["1"], "throughput_MiBs")
                plot.generateBlockSizeGraph(operation, ["1"], "avg_lat_us")

            for block_size_K in block_size_K_list:
                if "read" in operation:
                    plot.generatePercentileGraph({"operation": operation, "block_size_K": block_size_K, "number_parallel_jobs": "1"})

                for number_parallel_jobs in number_parallel_jobs_list:
                    if "write" in operation:
                        plot.generatePercentileGraph({"operation": operation, "block_size_K": block_size_K, "number_parallel_jobs": str(number_parallel_jobs)})

                tmp_queue_depth_list = queue_depth_list
                if "read" in operation:
                    tmp_queue_depth_list = [1, 2, 4, 8, 16, 32, 64]

                for queue_depth in tmp_queue_depth_list:
                    plot.generatePercentileGraph({"operation": operation, "block_size_K": block_size_K, "queue_depth": str(queue_depth)})

        print("  Done generateing graphs")

base_benches.append(Run())



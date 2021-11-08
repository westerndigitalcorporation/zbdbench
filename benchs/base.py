import subprocess
import re
import sys
import csv
import os
import matplotlib.pyplot as plt

# Global list of available benchmarks
base_benches = []

# Generic class that a benchmark definition must implement.
class Bench(object):
    # output overwritten by setup()
    output = 'output/'

    # Interface to be implemented by inheriting classes
    def id(self):
        return "Generic benchmark (name)"

    def setup(self, output):
        self.output = output

    def run(self):
        print("Not implemented (run)")

    def teardown(self):
        print("Not implemented (teardown)")

    def report(self, path):
        print("Not implemented (report)")

    def plot(self, csv_file):
        print("Not implemented (plot)")

    # Helpers
    def docker_sys_cmd(self, dev):
        return "docker run -v \"%s:%s\" -v \"%s:/output\" --privileged=true" % (dev, dev, self.output)

    def required_host_tools(self):
        return {'blkzone', 'blkdiscard'}

    def required_container_tools(self):
        return set()

    def sys_cmd(self, tool, dev, container):
        exec_cmd = tool
        container_cmd = ''

        if container == 'docker':
            if tool == 'fio':
                exec_cmd = 'zfio'
            if tool == 'db_bench':
                exec_cmd = 'zrocksdb'
            if tool == 'zenfs':
                exec_cmd = 'zzenfs'

            container_cmd = self.docker_sys_cmd(dev)

        return "%s %s" % (container_cmd, exec_cmd)

    def sys_container_dev(self, dev, container):
            return dev

    def get_dev_size(self, dev):
        devname = dev.strip('/dev/')

        with open('/sys/block/%s/size' % devname, 'r') as f:
            dev_size = int(f.readline())

        # Reported in 512B
        return (dev_size / 2)

    def get_number_of_zones(self, dev):
        nr_zones = 0
        with open('%s/nvme_zns_report-zones.txt' % (self.output), 'r') as f:
            nr_zones = int(f.readline().strip('nr_zones: '))

        return nr_zones

    def get_zone_size_mb(self, dev):
       devname = dev.strip('/dev/')
       zonesize = 0

       with open('/sys/block/%s/queue/chunk_sectors' % devname, 'r') as f:
           zonesize = int(((int(f.readline()) * 512) / 1024) / 1024)
       return zonesize

    def get_zone_capacity_mb(self, dev):
        devname = dev.strip('/dev/')

        with open('%s/nvme_zns_report-zones.txt' % (self.output), 'r') as f:
            f.readline() # first line is total number of zones
            res = f.readline()

            m = re.search('Cap: 0[xX][0-9a-fA-F]+', res)

            if m is None:
                print("No zones reported to get zone capacity")
                sys.exit(1)

            zonecap = int(m.group().strip('Cap: '), 16)

        with open('/sys/block/%s/queue/hw_sector_size' % devname, 'r') as f:
            bs = int(f.readline())

        return int(zonecap * bs / 1024 / 1024)

    def discard_dev(self, dev):
#        v = raw_input('Do you want to discard (y/N)?')
#        if v != 'y':
#            sys.exit(1)

        if is_dev_zoned(dev):
            subprocess.call("blkzone reset %s" % dev, shell=True)
        else:
            subprocess.call("blkdiscard %s" % dev, shell=True)

    def run_cmd(self, dev, container, tool, tool_params):
        cmd = "%s %s" % (self.sys_cmd(tool, dev, container), tool_params)

        print("Exec: %s" % cmd)

#        v = raw_input('Do you want to execute: %s (y/N)?' % cmd)
#        if v != 'y':
#            sys.exit(1)

        subprocess.call(cmd, shell=True)

# Generic Plot class that supplies rudimentary matplotlib helper functions
class Plot(object):

    def __init__(self, csv_file):
        self.csv_file = csv_file
        with open(self.csv_file, 'r') as f:
            d_reader = csv.DictReader(f)
            self.header = d_reader.fieldnames
        self.output_dir = os.path.dirname(os.path.abspath(csv_file))

    def resetPlot(self):
        plt.cla()
        plt.clf()
        plt.close()

    def saveInOutputDir(self, name):
        plt.savefig(os.path.join(self.output_dir, name), bbox_inches="tight")

    def getGenericLabel(self, row_dict, row_items):
        label = ""
        keys = list(row_dict.keys())
        values = list(row_dict.values())
        for item in row_items:
            label += str(str(keys[item]) + str(values[item]) + "_")
        return (label[:-1])

    def setupGenericBarGraph(self, filter_dict, value_of_interest, label_row_items, comparison_csv_file="", figure_size=()):
        self.resetPlot()
        benchmark_rows = csv.DictReader(open(self.csv_file))
        y_values = []
        x_ticks = []
        x_values = []
        i = 1
        for row in benchmark_rows:
            row_passes_filter = True
            for key, values in filter_dict.items():
                if str(row[key]) not in [str(value) for value in values]:
                    row_passes_filter = False
                    break

            if row_passes_filter:
                y_values.append(float(row[value_of_interest]))
                x_ticks.append(self.getGenericLabel(row, label_row_items))
                x_values.append(i)
                i += 1
        if len(figure_size) > 0:
            plt.figure(figsize=figure_size)
        plt.xticks(x_values, x_ticks, rotation=90)

        if not comparison_csv_file:
            plt.bar(x_values, y_values, width=0.2, zorder=3, label=self.csv_file)
        else:
            comparision_benchmark_rows = csv.DictReader(open(comparison_csv_file))
            comparison_y_values = []
            i = 0
            for row in comparision_benchmark_rows:
                row_passes_filter = True
                for key, values in filter_dict.items():
                    if str(row[key]) not in [str(value) for value in values]:
                        row_passes_filter = False
                        break

                if row_passes_filter:
                    comparison_y_values.append(float(row[value_of_interest]))
                    if x_ticks[i] != self.getGenericLabel(row, label_row_items):
                        print("The sorting of the comparision csv does not line up!")
                        exit(1)
                    i += 1

            plt.bar([x - 0.1 for x in x_values], y_values, width=0.2, zorder=3, label=self.csv_file)
            plt.bar([x + 0.1 for x in x_values], comparison_y_values, width=0.2, zorder=3, label=comparison_csv_file)
            plt.legend()

# Helper functions shared by scripts
def is_dev_zoned(dev):
    devname = dev.strip('/dev/')

    with open('/sys/block/%s/queue/zoned' % devname, 'r') as f:
        res = f.readline()

    return ("host-managed" in res)

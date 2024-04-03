#!/usr/bin/env python3
import csv
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import hashlib
from itertools import groupby
from benchs import fio_steady_state_performance

# Generic Plot class that supplies rudimentary matplotlib helper functions
# Inspired by https://stackoverflow.com/questions/54965009/grouped-x-axis-variability-plot-in-python
class Plot(object):
    #TODO: Optionally use the data_collector as the plot source
    def __init__(self, output_base, csv_files):
        self.header = []
        if not isinstance(csv_files, list):
            csv_files = [csv_files]
        self.csv_files = csv_files
        for csv_file in self.csv_files:
            with open(csv_file, 'r') as f:
                d_reader = csv.DictReader(f)
                header = d_reader.fieldnames
                if self.header == []:
                    self.header = header
                elif self.header != header:
                    print("The headers of the given csv_files are not compatible with each other. Exiting.")
                    exit(1)

        desc = '\n'.join(self.csv_files)
        desc_hash = hashlib.sha1(desc.encode()).hexdigest()[:10]
        self.output_dir = os.path.join(output_base, f"plot-{desc_hash}")
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)
            with open(os.path.join(self.output_dir, 'plot-description.txt'), 'a') as comp_desc_file:
                comp_desc_file.write(desc)
        else:
            print(f"  Plots already exist. Overwriting the plots in {self.output_dir}.")

    def reset_plot(self):
        plt.cla()
        plt.clf()
        plt.close()

    def check_env_and_set_title(self, ax, title):
        PLOT_TITLE = os.getenv('PLOT_TITLE')
        if PLOT_TITLE == None:
            ax.set_title(title, fontweight="bold")
        else:
            ax.set_title(str(PLOT_TITLE), fontweight="bold")

    def save_graph_plt_in_output_dir(self, name):
        filename = os.path.join(self.output_dir, name)
        print(f"Saving {filename}")
        plt.savefig(filename, bbox_inches="tight")

    def add_line(self, ax, xpos, ypos):
        line = plt.Line2D([xpos, xpos], [ypos + .1, ypos],
                        transform=ax.transAxes, color='gray')
        line.set_clip_on(False)
        ax.add_line(line)

    def label_len(self, my_index,level):
        labels = my_index.get_level_values(level)
        return [(k, sum(1 for i in g)) for k,g in groupby(labels)]

    def label_group_bar_table(self, ax, df):
        ypos = -.1
        scale = 1./df.index.size
        for level in range(df.index.nlevels)[::-1]:
            pos = 0
            for label, rpos in self.label_len(df.index,level):
                lxpos = (pos + .5 * rpos)*scale
                if level == 0:
                    label = f"{label} KiB"
                ax.text(lxpos, ypos, label, ha='center', transform=ax.transAxes)
                self.add_line(ax, pos*scale, ypos)
                pos += rpos
            self.add_line(ax, pos*scale , ypos)
            ypos -= .1

    def get_file_content(self, results_dir, filename):
        file_content = "Not found"
        try:
            with open(os.path.join(results_dir, filename), 'r') as f:
                file_content = " ".join(f.readlines()).strip()
        except FileNotFoundError as e:
            pass
        return file_content

    def get_user_annotation(self, results_dir):
        return self.get_file_content(results_dir, "user_annotation.txt")

    def gen_FIO_STEADY_STATE_PERFORMANCE(self):
        self.reset_plot()
        datapoints = {}
        time_step_sec = fio_steady_state_performance.log_interval_sec
        max_data_points = 0

        #Collect all datapoints in GB/s
        for csv_file in self.csv_files:
            max_data_points = max(max_data_points, sum(1 for _ in open(csv_file)) - 1)
            tmp = pd.read_csv(csv_file, delimiter = ';')['write_bw_kB'].values.tolist()
            data = [float(x/1000000.0) for x in tmp]
            datapoints[str(self.get_user_annotation(os.path.dirname(csv_file)))] = data

        #Extend smaller data vectors
        for key, value in datapoints.items():
            if len(value) < max_data_points:
                value.extend([np.nan]*(max_data_points - len(value)))
                datapoints[key] = value

        datapoints['time_sec'] = range(time_step_sec,(time_step_sec*max_data_points + 1),time_step_sec)
        df = pd.DataFrame(datapoints)
        df = df.set_index(['time_sec'])
        ax = df.plot(figsize=(8,7))

        ax.set_xlabel("Time [s]", fontweight="bold")
        ax.set_ylabel("Throughput [GB/s]", fontweight="bold")
        self.check_env_and_set_title(ax, "Sequential Fill + 2x Device Capacity Random Overwrite @ 64KiB, QD 16")
        self.save_graph_plt_in_output_dir(f"steady-state-performance.pdf")

    def gen_FIO_ZONE_THROUGHPUT_AVG_LAT(self, operation):
        self.reset_plot()
        number_datapoints = len(self.csv_files)
        parallel_requests = []
        parallel_label = 'Number of Jobs'
        block_sizes = []
        benchmarking_labels = []
        throughput = []
        latency = []
        max_throughput = 0
        min_throughput = sys.maxsize
        for csv_file in self.csv_files:
            with open(csv_file, 'r') as f:
                d_reader = csv.DictReader(f, delimiter=";")
                for row in d_reader:
                    if row['rw'] != operation:
                        continue
                    benchmarking_labels.append(self.get_user_annotation(os.path.dirname(csv_file)))
                    #TODO: Include the unit of BS -> The graph and table should be sorted correctly.
                    block_sizes.append(int(row['bs'][:-1]))
                    if operation == 'randread':
                        parallel_requests.append(int(row['iodepth']))
                        parallel_label = 'Queue Depth'
                    else:
                        parallel_requests.append(int(row['numjobs']))
                    if 'read' in operation:
                        tp = float(row['read_bandwidth_kb'])/1024.0
                        lat = float(row['read_clat_mean_us'])
                    else:
                        tp = float(row['write_bandwidth_kb'])/1024.0
                        lat = float(row['write_clat_mean_us'])
                    throughput.append(tp)
                    latency.append(lat)
                    max_throughput = max(tp, max_throughput)
                    min_throughput = min(tp, min_throughput)

        if len(throughput) == 0:
            print(f"Skipping plot for fio {operation} workload because there is data for it.")
            return
        self.generate_graph_FIO_ZONE_THROUGHPUT_AVG_LAT(parallel_label, parallel_requests, block_sizes, benchmarking_labels, operation, throughput, min_throughput, max_throughput, number_datapoints)
        self.generate_table_FIO_ZONE_THROUGHPUT_AVG_LAT(parallel_label, parallel_requests, block_sizes, benchmarking_labels, operation, latency)

    def generate_graph_FIO_ZONE_THROUGHPUT_AVG_LAT(self, parallel_label, parallel_requests, block_sizes, benchmarking_labels, operation, throughput, min_throughput, max_throughput, number_datapoints):
        df = pd.DataFrame({'parallel_request':parallel_requests,
                        'block_size_group':block_sizes,
                        'Label':benchmarking_labels,
                        'Data':throughput})
        df = df.set_index(['block_size_group','parallel_request','Label'])['Data'].unstack()
        min_throughput -= 20
        if min_throughput < 0:
            min_throughput = 0
        ax = df.plot.bar(xlim=(-.5, (len(benchmarking_labels)/number_datapoints)-0.5), ylim=(min_throughput, max_throughput + 200), figsize=(15,7.5))

        #Disable x ticks and regular labels
        ax.set_xticklabels('')
        ax.set_xlabel('')
        plt.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)

        ax.annotate('Block Size', xy=(1,-0.190), xytext=(5, 0), ha='left', va='top', xycoords='axes fraction', textcoords='offset points', fontweight="bold")
        ax.set_ylabel("Throughput [MiB]", fontweight="bold")
        ax.set_xlabel(parallel_label, fontweight="bold")
        ax.xaxis.set_label_coords(0.5,-0.22)
        self.check_env_and_set_title(ax, f"Throughput fio {operation} workload")
        self.label_group_bar_table(ax, df)
        self.save_graph_plt_in_output_dir(f"throughput-graph-{operation}.pdf")

    def generate_table_FIO_ZONE_THROUGHPUT_AVG_LAT(self, parallel_label, parallel_requests, block_sizes, benchmarking_labels, operation, latency):
        self.reset_plot()
        df = pd.DataFrame({'parallel_requests':parallel_requests,
                           'block_sizes':block_sizes,
                           'benchmarking_labels':benchmarking_labels,
                           'Data':latency})
        df = pd.pivot_table(df, values='Data', index='parallel_requests', columns=['block_sizes', 'benchmarking_labels'])
        df = df.rename_axis(parallel_label, axis='index')
        df = df.rename_axis(["Block Size [KiB]:", "Benchmark:"], axis='columns')
        #print(df)
        s = df.style

        filename = os.path.join(self.output_dir, f"latency-table-{operation}.tex")
        print(f"Saving {filename}")
        with open(filename, 'w') as f:
            f.write(s.to_latex())

        filename = os.path.join(self.output_dir, f"latency-table-{operation}.xlsx")
        print(f"Saving {filename}")
        df.style.to_excel(filename, engine='openpyxl')

        cell_hover = {
            'selector': 'td:hover',
            'props': [('background-color', '#ffffb3')]
        }
        row_hover = {
            'selector': 'tr:hover',
            'props': [('background-color', '#d4d6ff')]
        }
        index_names = {
            'selector': '.index_name',
            'props': 'font-style: italic; color: darkgrey; font-weight:normal;'
        }
        headers = {
            'selector': 'th:not(.index_name)',
            'props': 'background-color: #000066; color: white;'
        }
        s.set_table_styles([cell_hover, row_hover, index_names, headers])

        filename = os.path.join(self.output_dir, f"latency-table-{operation}.html")
        print(f"Saving {filename}")
        with open(filename, 'w') as f:
            f.write(s.to_html())

if __name__ == "__main__":
    print("%s is not meant to run as a stand alone script." % os.path.basename(__file__))


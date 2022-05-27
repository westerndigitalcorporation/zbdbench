#!/usr/bin/env python3

import sys
import subprocess
import os
import re
import distutils.spawn
import argparse

from datetime import datetime
from benchs.base import base_benches, is_dev_zoned, DeviceScheduler, set_spdk_install_dir
from benchs import *

def get_zbdbench_version():
    version_process = subprocess.Popen(["git", "describe", "--abbrev=7", "--dirty", "--always"], stdout=subprocess.PIPE)
    return version_process.communicate()[0].strip().decode('ascii')

def check_dev_mounted(dev):
    with open('/proc/mounts', 'r') as f:
        if any(dev in s for s in [line.split()[0] for line in f.readlines()]):
            print("Check FAIL: %s is mounted. Exiting..." % dev)
            sys.exit(1)

    print('Check OK: %s is not mounted' % dev)


def check_and_set_mqdeadline_scheduler(dev):
    devname = dev.strip('/dev/')

    with open('/sys/block/%s/queue/scheduler' % devname, 'r') as f:
        res = f.readline()

    if "[mq-deadline]" in res:
        print("Check OK: %s is set with 'mq-deadline' scheduler" % dev)
        return

    if "[none]" in res:
        with open('/sys/block/%s/queue/scheduler' % devname, 'w') as f:
            f.write("mq-deadline")

    with open('/sys/block/%s/queue/scheduler' % devname, 'r') as f:
        res = f.readline()

    if "[mq-deadline]" not in res:
        print("Check FAIL: %s does not support mq-deadline scheduler" % dev)
        sys.exit(1)

    print("Check OK: %s has been configured to use the 'mq-deadline' scheduler" % dev)


def check_and_set_none_scheduler(dev):
    devname = dev.strip('/dev/')

    with open('/sys/block/%s/queue/scheduler' % devname, 'r') as f:
        res = f.readline()

    if "[none]" in res:
        print("Check OK: %s is set with 'none' scheduler" % dev)
        return

    if "[mq-deadline]" in res:
        with open('/sys/block/%s/queue/scheduler' % devname, 'w') as f:
            f.write("none")

    with open('/sys/block/%s/queue/scheduler'% devname, 'r') as f:
        res = f.readline()

    if "[none]" not in res:
        print("Check FAIL: %s does not support none scheduler" % dev)
        sys.exit(1)

    print("Check OK: %s has been configured to use the 'none' scheduler" % dev)


def check_dev_string(dev):
    m = re.search('^/dev/\w+$', dev)

    if m is None:
        print("Check Fail: Device must be named /dev/[a-zA-Z0-9]+ (e.g., /dev/nvme0n1)")
        sys.exit(1)

    print("Check OK: %s is valid" % dev)


def check_dev_zoned(dev):
    if is_dev_zoned(dev):
        print("Check OK: %s is a zoned block device" % dev)
    else:
        print("Check OK: %s is a conventional block device" % dev)

def check_missing_programs(container, benchmark):

    host_tools = {'blkzone'}
    container_tools = set()

    host_tools |= benchmark.required_host_tools()
    container_tools |= benchmark.required_container_tools()

    if "no" in container:
        host_tools |= container_tools
    else:
        host_tools.add('podman')

    print(f"Required host tools: {host_tools}")
    for tool in host_tools:
        if not distutils.spawn.find_executable(tool):
            print(f"Check FAIL: {tool} not available")
            sys.exit(1)

    if "no" not in container:
        print(f"Required containers: {container_tools}")
        for tool in container_tools:
            if tool == 'fio':
                exec_img = 'zfio'
            if tool == 'db_bench':
                exec_img = 'zrocksdb'
            if tool == 'zenfs':
                exec_img = 'zrocksdb'
            if tool == 'mkfs.f2fs':
                exec_img = 'zf2fs'
            if tool == 'mkfs.xfs':
                exec_img = 'zxfs'
            if tool == 'sysbench':
                exec_img = 'zsysbench'

        p = subprocess.run(f"podman image exists {exec_img}", shell=True)

        if p.returncode != 0:
            print(f"Container image not found: {exec_img}")
            print("See the README for how to install the required images or")
            print("run the command with \"-c no\" to use the existing system tools.")
            sys.exit(1)

    print("Check OK: All executables available")


def create_dirs(run_output):
    if os.path.isdir(run_output):
        print("Output directory (%s) already exists. Exiting..." % run_output)
        sys.exit(1)

    try:
        os.makedirs(run_output)
    except OSError:
        print("Not able to create output directory. Exiting...")
        sys.exit(1)

def gather_device_info(dev, run_output):
    subprocess.check_call(f"lsblk -b {dev} > {run_output}/lsblk-capacity.txt", shell=True)
    subprocess.check_call(f"udevadm info --query=all --name={dev} > {run_output}/udevadm-info.txt", shell=True)

    if is_dev_zoned(dev):
        subprocess.check_call(f"blkzone capacity {dev} > {run_output}/blkzone-capacity.txt", shell=True)
        subprocess.check_call(f"blkzone report {dev} > {run_output}/blkzone-report.txt", shell=True)

def gather_benchmark(run_output, benchmark):
    subprocess.check_call(f"echo {benchmark} > {run_output}/benchmark.txt", shell=True)

def gather_benchmark_call(run_output, benchmark_args):
    benchmark_call = " ".join(sys.argv)
    subprocess.check_call(f"echo {benchmark_call} > {run_output}/benchmark_call.txt", shell=True)
    subprocess.check_call(f"echo {benchmark_args} > {run_output}/benchmark_args.txt", shell=True)

def gather_system_meminfo(run_output):
    subprocess.check_call(f"free -h > {run_output}/system_meminfo.txt", shell=True)

def gather_system_cpuinfo(run_output):
    subprocess.check_call(f"lscpu > {run_output}/system_cpuinfo.txt", shell=True)

def gather_user_annotation(run_output, annotation):
    subprocess.check_call(f"echo {annotation} > {run_output}/user_annotation.txt", shell=True)

def gather_zbdbench_version(run_output):
    zbdbench_version = get_zbdbench_version()
    subprocess.check_call(f"echo {zbdbench_version} > {run_output}/zbdbench_version.txt", shell=True)

def list_benchs(benches):
    print("\nBenchmarks:")
    for b in benches:
        print("  " + b.id())

def collect_results_in_sqlite(output_path, results_dir):
    from data_collector import sqlite_data_collector
    db_connection = sqlite_data_collector.DatabaseConnection(os.path.join(output_path, "data-collection.sqlite3"))
    db_connection.collect_fio_results_from_directory(results_dir)
    print("Done collecting results.")

def check_and_set_scheduler_for_benchmark(dev, benchmark, scheduler_overwrite):
    if is_dev_zoned(dev):
        scheduler = benchmark.get_default_device_scheduler()
        if scheduler_overwrite:
            scheduler = scheduler_overwrite
        if scheduler == DeviceScheduler.MQ_DEADLINE:
            check_and_set_mqdeadline_scheduler(dev)
        else:
            check_and_set_none_scheduler(dev)

def run_benchmark(dev, container, benchmark, output_path, run_output, scheduler_overwrite, annotation, benchmark_args):
    if not dev:
        print('No device name provided for benchmark')
        print('ex. run.py /dev/nvmeXnY')
        sys.exit()

    # Verify that we're not about to destroy data unintended.
    check_dev_string(dev)
    check_dev_mounted(dev)
    check_dev_zoned(dev)
    check_missing_programs(container, benchmark)

    create_dirs(run_output)

    gather_benchmark(run_output, benchmark.id())
    gather_benchmark_call(run_output, benchmark_args)
    gather_device_info(dev, run_output)
    gather_system_meminfo(run_output)
    gather_system_cpuinfo(run_output)
    gather_user_annotation(run_output, annotation)
    gather_zbdbench_version(run_output)

    print("\nDev: %s" % dev)
    print("Env: %s" % container)
    print("Output: %s\n" % run_output)

    print(f"Executing benchmark: {benchmark.id()}")
    if len(benchmark_args) > 0:
        print(f"   With arguments: {benchmark_args}")
    check_and_set_scheduler_for_benchmark(dev, benchmark, scheduler_overwrite)
    benchmark.setup(dev, container, run_output, benchmark_args)
    benchmark.run(dev, container)
    benchmark.teardown(dev, container)
    csv_file = benchmark.report(run_output)
    benchmark.plot(csv_file)
    collect_results_in_sqlite(output_path, run_output)
    print(f"\nCompleted benchmark {benchmark.id()}")

def run_report(path, benchmark):
    print(f"Generating report for: {benchmark.id()}")
    csv_file = benchmark.report(path)
    benchmark.plot(csv_file)

def run_plot(csv_file, benchmark):
    print(f"Generating plot for: {benchmark.id()}, {csv_file}")
    benchmark.plot(csv_file)

def print_help():
    print('Benchmarking')
    print('  List available benchmarks')
    print('    run.py -l')
    print('  Run specific benchmark')
    print('    run.py -d /dev/nvmeXnY -b fio_zone_write')

    print('\nReporting')
    print('  Generate specific report')
    print('    run.py -r output_dir -b fio_zone_write')

    print('\nPloting')
    print('  Generate specific plot')
    print('    run.py -b fio_zone_write -p csv_file')

    print('\nExecution Environment')
    print('  Use system executables')
    print('    run.py -d /dev/nvmeXnY -b fio_zone_write -c no')
    print('  Use container executables (default)')
    print('    run.py -d /dev/nvmeXnY -b fio_zone_write')

    print('\nCollecting results')
    print('    run.py --collect-results result_dir')

def main(argv):
    parser = argparse.ArgumentParser(description = 'Zoned Block Device Benchmark Tool', add_help=False)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dev', '-d', type=str, help='Path to block device used for test')
    group.add_argument('--report', '-r', type=str, metavar='PATH', help='Generate reports')
    group.add_argument('--plot', '-p', type=str, nargs='+', help='Generate plots')
    group.add_argument('--list-benchmarks', '-l', action='store_true', help='List available benchmarks')
    group.add_argument('--help', '-h', action='store_true', help='Print help message and exit')
    group.add_argument('--collect-results', type=str, help='Collect benchmark results of the specified path within this argument in a MySQL database which is specified by the mysql.conf file.')
    parser.add_argument('--container', '-c', type=str, default='yes', choices=['yes', 'no'], help='Use containerized binaries or system binaries')
    parser.add_argument('--benchmark', '-b', type=str, metavar='NAME', help='Benchmark to run')
    parser.add_argument('--output', '-o', type=str, default=os.path.join(os.getcwd(), 'zbdbench_results'), help='Directory to place results. Will be created if it does not exist')
    parser.add_argument('--annotation', '-a', type=str, default=str(datetime.now().strftime("%Y-%m-%d-%H%M%S")), help='Annotation for easier manual benchmark run identification')
    parser.add_argument('--benchmark-args', '-x', type=str, nargs='+', default='', help='Additional benchmark specific arguments')
    parser.add_argument('--use-spdk', '-s', type=str, default='no', choices=['yes', 'no'], help='Use spdk plugin for fio(uses io_uring spdk bdev)')
    parser.add_argument('--spdk-path', type=str, help='Dir path for SPDK checkout and build. Needed only for host spdk(-c no -s yes) benchmarks')
    scheduler_group = parser.add_mutually_exclusive_group(required=False)
    scheduler_group.add_argument('--none-scheduler', action='store_true', help='Use none scheduler for the given drive.')
    scheduler_group.add_argument('--mq-deadline-scheduler', action='store_true', help='Use mq-deadline scheduler for the given drive.')
    args = parser.parse_args()

    annotation = args.annotation
    dev = ''
    container = args.container
    output_path = args.output
    selected_benchmark = args.benchmark
    benchmark = None
    benchmark_args = args.benchmark_args
    run = ''
    scheduler_overwrite = None
    use_spdk = args.use_spdk

    if args.help:
        parser.print_help()
        print()
        print_help()
        sys.exit()

    if args.none_scheduler:
        scheduler_overwrite = DeviceScheduler.NONE

    if args.mq_deadline_scheduler:
        scheduler_overwrite = DeviceScheduler.MQ_DEADLINE

    if args.collect_results != None:
        run = 'collect-results'
        results_dir = args.collect_results

    if args.plot != None:
        run = 'plot'
        csv_files = args.plot

    if args.report is not None:
        run = 'report'
        report_path = args.report

    if args.dev is not None:
        run = 'bench'
        dev = args.dev

    if args.list_benchmarks:
        list_benchs(base_benches)
        sys.exit()

    for x in base_benches:
        if x.id() == selected_benchmark:
            benchmark = x
    if benchmark == None:
        print(f"Invalid benchmark name: {selected_benchmark}")
        list_benchs(base_benches)
        sys.exit(1)

    if use_spdk == 'yes':
        if args.spdk_path is not None:
            if container == 'no':
                set_spdk_install_dir((args.spdk_path).rstrip('/'))
            else:
                print("Ignoring user provided spdk install dir for '-c yes' option.")
        else:
            if container != 'yes':
                print("SPDK install dir not provided!")
                sys.exit()
    else:
        set_spdk_install_dir('')

    if run == 'collect-results':
        collect_results_in_sqlite(output_path, results_dir)
    elif run == 'plot':
        run_plot(csv_files, benchmark)
    elif run == 'report':
        run_report(report_path, benchmark)
    elif run == 'bench':
        run_output_relative = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        run_output = "%s/%s" % (output_path, run_output_relative)
        print(f"Output directory: {run_output}")
        run_benchmark(dev, container, benchmark, output_path, run_output, scheduler_overwrite, annotation, benchmark_args)
    else:
        print_help()


if __name__ == "__main__":
    main(sys.argv[1:])

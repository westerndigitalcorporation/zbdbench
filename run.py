#!/usr/bin/env python3

import sys
import subprocess
import os
import re
import distutils.spawn
import argparse

from datetime import datetime
from benchs.base import base_benches, is_dev_zoned, DeviceScheduler
from benchs import *


def check_dev_mounted(dev):
    with open('/proc/mounts','r') as f:
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

    with open('/sys/block/%s/queue/scheduler'% devname, 'r') as f:
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
        print("Check OK: %s is a zoned block device" %dev)
    else:
        print("Check OK: %s is a conventional block device" % dev)

def check_missing_programs(container, benchmark):

    host_tools = {'blkzone'}
    container_tools = set()

    host_tools |= benchmark.required_host_tools()
    container_tools |= benchmark.required_container_tools()

    if "system" in container:
        host_tools |= container_tools
    else:
        host_tools.add('podman')

    print(f"Required host tools: {host_tools}")
    for tool in host_tools:
        if not distutils.spawn.find_executable(tool):
            print(f"Check FAIL: {tool} not available")
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

def collect_info(dev, run_output, benchmark_args):
    subprocess.check_call(f"lsblk -b {dev} > {run_output}/lsblk-capacity.txt", shell=True)
    subprocess.check_call(f"echo {benchmark_args} > {run_output}/benchmark_args.txt", shell=True)

    if is_dev_zoned(dev):
        subprocess.check_call(f"blkzone capacity {dev} > {run_output}/blkzone-capacity.txt", shell=True)
        subprocess.check_call(f"blkzone report {dev} > {run_output}/blkzone-report.txt", shell=True)

def list_benchs(benches):
    print("\nBenchmarks:")
    for b in benches:
        print("  " + b.id())

def check_and_set_scheduler_for_benchmark(dev, benchmark, scheduler_overwrite):
    scheduler = benchmark.get_default_device_scheduler()
    if scheduler_overwrite:
        scheduler = scheduler_overwrite
    if scheduler == DeviceScheduler.MQ_DEADLINE:
        check_and_set_mqdeadline_scheduler(dev)
    else:
        check_and_set_none_scheduler(dev)

def run_benchmark(dev, container, benchmark, run_output, scheduler_overwrite, benchmark_args):
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

    collect_info(dev, run_output, benchmark_args)

    print("\nDev: %s" % dev)
    print("Env: %s" % container)
    print("Output: %s\n" % run_output)

    print("Executing benchmark: %s" % benchmark.id())
    if len(benchmark_args) > 0:
        print("With arguments: %s" % benchmark_args)
    check_and_set_scheduler_for_benchmark(dev, benchmark, scheduler_overwrite)
    benchmark.setup(dev, container, run_output, benchmark_args)
    benchmark.run(dev, container)
    benchmark.teardown(dev, container)
    csv_file = benchmark.report(run_output)
    benchmark.plot(csv_file)

    print("\nCompleted benchmark %s" % benchmark.id())

def run_report(path, benchmark):
    print("Generating report for: %s" % benchmark.id())
    csv_file = benchmark.report(path)
    benchmark.plot(csv_file)

def run_plot(csv_file, benchmark):
    print("Generating plot for: %s, %s" % (benchmark.id(), csv_file))
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

def main(argv):
    parser = argparse.ArgumentParser(description = 'Zoned Block Device Benchmark Tool', add_help=False)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dev', '-d', type=str, help='Path to block device used for test')
    group.add_argument('--report', '-r', type=str, metavar='PATH', help='Generate reports')
    group.add_argument('--plot', '-p', type=str, metavar='OUTPUT_CSV', help='Generate plots')
    group.add_argument('--list-benchmarks', '-l', action='store_true', help='List available benchmarks')
    group.add_argument('--help', '-h', action='store_true', help='Print help message and exit')
    parser.add_argument('--container', '-c', type=str, default='yes', choices=['yes', 'no'], help='Use containerized binaries or system binaries')
    parser.add_argument('--benchmark', '-b', type=str, metavar='NAME', help='Benchmark to run')
    parser.add_argument('--output', '-o', type=str, default=os.path.join(os.getcwd(), 'zbdbench_results'), help='Directory to place results. Will be created if it does not exist')
    parser.add_argument('--benchmark-args', '-a', type=str, nargs='+', default='', help='Additional benchmark specific arguments')
    scheduler_group = parser.add_mutually_exclusive_group(required=False)
    scheduler_group.add_argument('--none-scheduler', action='store_true', help='Use none scheduler for the given drive.')
    scheduler_group.add_argument('--mq-deadline-scheduler', action='store_true', help='Use mq-deadline scheduler for the given drive.')
    args = parser.parse_args()

    dev = ''
    container = args.container
    output_path = args.output
    selected_benchmark = args.benchmark
    benchmark = None
    benchmark_args = args.benchmark_args
    run = ''
    scheduler_overwrite = None

    if args.help:
        parser.print_help()
        print()
        print_help()
        sys.exit()

    if args.none_scheduler:
        scheduler_overwrite = DeviceScheduler.NONE

    if args.mq_deadline_scheduler:
        scheduler_overwrite = DeviceScheduler.MQ_DEADLINE

    if args.plot != None:
        run = 'plot'
        csv_file = args.plot

    if args.report != None:
        run = 'report'
        report_path = args.report

    if args.dev != None:
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

    run_output_relative = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    run_output = "%s/%s" % (output_path, run_output_relative)

    print(f"Output directory: {run_output}")

    if run == 'plot':
        run_plot(csv_file, benchmark)
    elif run == 'report':
        run_report(report_path, benchmark)
    elif run == 'bench':
        run_benchmark(dev, container, benchmark, run_output, scheduler_overwrite, benchmark_args)
    else:
        print_help()

if __name__ == "__main__":
    main(sys.argv[1:])

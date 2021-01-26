#!/usr/bin/env python3

import sys, getopt
import subprocess
import os
import re
import distutils.spawn
from datetime import datetime
from benchs.base import base_benches, is_dev_zoned
from benchs import *

run_output_relative = "output/%s" % (datetime.now().strftime("%Y%m%d%H%M%S"))
run_output = "%s/%s" % (os.getcwd(), run_output_relative)

def check_dev_mounted(dev):
    with open('/proc/mounts','r') as f:
        if any(dev in s for s in [line.split()[0] for line in f.readlines()]):
            print("Check FAIL: %s is mounted. Exiting..." % dev)
            sys.exit(1)

    print('Check OK: %s is not mounted' % dev)

def check_and_set_scheduler(dev):
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

def check_missing_programs(container):
    if not distutils.spawn.find_executable("blkzone"):
        print("Check FAIL: blkzone not available")
        sys.exit(1)

    if not distutils.spawn.find_executable("blkdiscard"):
        print("Check FAIL: blkdiscard not available")
        sys.exit(1)

    if not distutils.spawn.find_executable("nvme"):
        print("Check FAIL: nvme not available")
        sys.exit(1)

    if "system" in container:
        if not distutils.spawn.find_executable("fio"):
            print("Check FAIL: fio not available")
            sys.exit(1)
    else:
        if not distutils.spawn.find_executable("docker"):
            print("Check FAIL: docker not available")
            sys.exit(1)

    print("Check OK: All executables available")

def create_dirs():
    if not os.path.isdir('output'):
        try:
            os.mkdir('output')
        except OSError:
            print("Not able to create output directory. Exiting...")
            sys.exit(1)

    if os.path.isdir(run_output):
        print("Output directory (%s) already exists. Exiting..." % run_output)
        sys.exit(1)

    try:
        os.mkdir(run_output)
    except OSError:
        print("Not able to create output directory. Exiting...")
        sys.exit(1)

def collect_info(dev):
    subprocess.call("nvme id-ctrl -H %s > %s/nvme_id-ctrl.txt" % (dev, run_output), shell=True)
    subprocess.call("nvme id-ns -H %s > %s/nvme_id-ns.txt" % (dev, run_output), shell=True)

    if is_dev_zoned(dev):
        subprocess.call("nvme zns id-ns -H %s > %s/nvme_zns_id-ns.txt" % (dev, run_output), shell=True)
        subprocess.call("nvme zns report-zones -H %s > %s/nvme_zns_report-zones.txt" % (dev, run_output), shell=True)

def list_benchs(benches):
    print("\nBenchmarks:")
    for b in benches:
        print("  " + b.id())

def run_benchmarks(dev, container, benches):
    if not dev:
        print('No device name provided for benchmark')
        print('ex. run.py /dev/nvmeXnY')
        sys.exit()

    # Verify that we're not about to destroy data unintended.
    check_dev_string(dev)
    check_dev_mounted(dev)
    check_and_set_scheduler(dev)
    check_dev_zoned(dev)
    check_missing_programs(container)

    list_benchs(benches)

    create_dirs()

    collect_info(dev)

    print("\nDev: %s" % dev)
    print("Env: %s" % container)
    print("Output: %s\n" % run_output)

    for b in benches:
        print("Executing: %s" % b.id())

        b.setup(dev, container, run_output)
        b.run(dev, container)
        b.teardown(dev, container)
        b.report(run_output)

    print("\nCompleted %s benchmark(s)" % len(benches))

def run_reports(path, benches):
    for b in benches:
        print("Generating report for: %s" % b.id())

        b.report(path)

def print_help():
    print('Benchmarking')
    print('  List available benchmarks')
    print('    run.py -l')
    print('  Run all benchmarks:')
    print('    run.py -d /dev/nvmeXnY')
    print('  Run specific benchmark')
    print('    run.py -d /dev/nvmeXnY -b fio_zone_write')

    print('\nReporting')
    print('  Generate all reports')
    print('    run.py -r output_dir')
    print('  Generate specific report')
    print('    run.py -r output_dir -b fio_zone_write')

    print('\nExecution Environment')
    print('  Use system executables')
    print('    run.py -d /dev/nvmeXnY -c system')
    print('  Use container executables (default)')
    print('    run.py -d /dev/nvmeXnY')

def main(argv):

    dev = ''
    container = 'docker'
    try:
        opts, args = getopt.getopt(argv, "hd:c:r:b:l", ["dev=", "container=", "report", "benchmark=", "list_benchmarks"])
    except getopt.GetoptError:
        print_help()
        sys.exit(2)

    run = ''
    benches = base_benches
    for opt, arg in opts:
        if opt in ('-r', "--report="):
                run = 'report'
                report_path = arg
        if opt in ("-d", "--dev"):
            run = 'bench'
            dev = arg

        if opt in ('-c', "--container"):
            if arg == 'system':
                container = arg

        if opt == '-h':
            print_help()
            sys.exit()

        if opt in ('-l', '--list_benchmarks'):
            list_benchs(base_benches)
            sys.exit()
        if opt in ('-b', '--benchmark'):
            benches = [next((x for x in benches if x.id() == arg), None)]

            if benches[0] is None:
                print("Benchmark not found: %s\n" % arg)
                list_benchs(base_benches)
                sys.exit(1)

    if run == 'report':
        run_reports(report_path, benches)
    elif run == 'bench':
        run_benchmarks(dev, container, benches)
    else:
        print_help()

if __name__ == "__main__":
    main(sys.argv[1:])

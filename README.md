# ZBDBench: Benchmark Suite for Zoned Block Devices

ZBDBench is a collection of benchmarks for zoned storage devices (Zoned Namespace (ZNS) SSDs and Shingled-Magnetic Recording (SMR) HDDs) that tests both the raw performance of the device, and runs standard benchmarks for applications such as RocksDB (dbbench) and MySQL (sysbench).

Community
---------
For help or questions about zbdbench usage (e.g. "how do I do X?") see [ZonedStorage.io](https://zonedstorage.io), our [Matrix](https://app.element.io/#/room/#zonedstorage-general:matrix.org) chat, or on [Slack](https://join.slack.com/t/zonedstorage/shared_invite/zt-uyfut5xe-nKajp9YRnEWqiD4X6RkTFw).


To report a bug, file a documentation issue, or submit a feature request, please open a GitHub issue.

For release announcements and other discussions, please subscribe to this repository or join us on Matrix.


Getting Started
---------------

The run.py script runs a set of predefined benchmarks on a block device. Required dependencies are described at the bottom.

The block device does not have to be zoned - the workloads will work
on both types of block devices.

The script performs a set of checks before running the benchmarks, such as
validating that it is about to write to a block device, not mounted, and ready.

After all benchmarks have run, their output is availble in:

    zbdbench_results/YYYYMMDDHHMMSS (date format is replaced with the current time)

Each benchmark has a report function, which creates a csv file with the
specific output. See the section below for the csv format for each benchmark.

To execute the benchmarks, run:

    sudo ./run.py -d /dev/nvmeXnY

If you have the latest fio installed, you may skip the container installation and
run the benchmarks using the system commands.

    sudo ./run.py -d /dev/nvmeXnY -c no

NOTE: If -c option is not provided, default is '-c yes'.
To list available benchmarks, run:

    ./run.py -l

To only run a specific benchmark, append -b <benchmark_name> to the command:

    sudo ./run.py -d /dev/nvmeXnY -b fio_zone_mixed

Command Options
---------------

List available benchmarks:

    ./run.py -l

Run specific benchmark:

    ./run.py -b benchmark -d /dev/nvmeXnY

Run all benchmarks:

    ./run.py -d /dev/nvmeXnY

Regenerate a report (and its plots)

    ./run.py -b fio_zone_mixed -r zbdbench_results/YYYYMMDDHHMMSS

Regenerate plots from existing csv report

    ./run.py -b fio_zone_throughput_avg_lat -p zbdbench_results/YYYYMMDDHHMMSS/fio_zone_throughput_avg_lat.csv

Overwrite benchmark run with the none device scheduler:

    ./run.py -b benchmark -d /dev/nvmeXnY --none-scheduler

Overwrite benchmark run with the mq-deadline device scheduler:

    ./run.py -b benchmark -d /dev/nvmeXnY --mq-deadline-scheduler

Benchmarks
----------

All fio benchmarks are setting the none scheduler by default.

fio_zone_write
  - executes a fio workload that writes sequential to 14 zones in parallel and
    while writing 6 times the capacity of the device.

  - generated csv output (fio_zone_write.csv)
    1. written_gb: gigabytes written (GB)
    2. write_avg_mbs: average throughput (MB/s)

fio_zone_mixed
  - executes a fio workload that first preconditions the block device to steady
    state. Then rate limited writes are issued, in which 4KB random reads
    are issued in parallel. The average latency for the 4KB random read is
    reported.

  - generated csv output (fio_zone_mixed.csv)
    1. write_avg_mbs_target: target write throughput (MB/s)
    2. read_lat_avg_us: avg 4KB random read latency (us)
    3. write_avg_mbs: write throughput (MB/s)
    4. read_lat_us_avg_measured: avg 4KB random read latency (us)
    5. clat_*_us: Latency percentiles

    ** Note that (2) is only reported if write_avg_mbs_target and write_avg_mbs
       are equal. When they are not equal, the reported average latency is
       misleading, as the write throughput requested has not been possible to
       achieve.

fio_zone_randr_seqw_seqr_rrsw
  - executes a fio workload that first preconditions the block device to steady
    state. Then it executes the following workloads:
    1. 4K_R_READ_256QD: Runs a random read workload with bs=4K, QD 256.
    2. 128K_S_READ_QD64: Runs a seq read workload with bs=128K, QD 64.
    3. 128K_70-30_R_READ_S_WRITE_QD64: Runs a rand read and seq write workload
                                       with QD 64.
    4. 128KB_S_WRITE_QD64: Runs a seq write workload with bs=128K, QD 64.

  - generated csv output file is fio_zone_randr_seqw_seqr_rrsw.csv
    1. read_avg_mbs: Avg read bw in mbs, 0 if no reads in the workload.
    2. read_lat_avg_us: Avg read latency in micro seconds.
    3. write_avg_mbs: Avg write bw in mbs, 0 if no writes in the workload.
    4. write_lat_avg_us: Avg write latency in micro seconds.
    5. read_iops: Read IOPS for a workload involving reads, else 0.
    6. write_iops: Write IOPS for a workload involving writes, else 0.
    7. clat_*_us: Latency percentiles

    *NOTE: For workload 3, the read and write percentiles are reported
           seperately in 2 lines in the csv.

fio_zone_throughput_avg_lat
  - Executes all combinations of the following workloads report the throughput
    and latency in the csv report (Note: 14 is a possible value for max_open_zones):
      - Sequential read, random read, sequential write
      - BS: 4K, 8K, 16K, 32K, 64K, 128K
      - Sequential write and sequential read specific:
        - Number of parallel jobs: 1, 2, 4, 8, 14, 16, 32, 64, 128 (skipping entries > max_open_zones)
        - QD: 1
        - ioengine: psync
      - Random read specific:
        - QD: 1, 2, 4, 8, 14, 16, 32, 64, 128
        - ioengine: io_uring

    For reads the drive is prepared with a write. The ZBD is reset before each
    run.

  - Generated csv output file is fio_zone_throughput_avg_lat.csv
    1. avg_lat_us: Average latency in µs for the specific run.
    2. throughput_MiBs: Throughput in MiBs for the specific run.
    3. clat_p1_us - clat_p100us: completion latency percentiles in µs.

  - Generates multiple graphs that plot the behavior of throughput and latency.

usenix_atc_2021_zns_eval
  Executes RocksDB's db_bench according to the RocksDB evaluation section
  (5.2 RocksDB) of the paper '[ZNS: Avoiding the Block Interface Tax for
  Flash-based SSDs](https://www.pdl.cmu.edu/PDL-FTP/Storage/USENIX_ATC_2021_ZNS.pdf)'.

  Depending on if the specified drive to benchmark is a ZNS or Conventional
  device different benchmarks are run.
  - For conventional devices the db_bench workload is run on the following
    filesystems:
        - xfs
        - f2fs
  - For ZNS devices the db_bench workload is run on the f2fs filesystem and
    with the ZenFS RocksDB plugin without an additional filesystem.

  Note: the tests are designed to run on 2TB devices.

Dependencies
------------

The benchmark tool requires Python 3.4+. In addition to a working python
environment, the script requires the following installed:

 - Linux kernel 5.9 or newer
   - Check your loaded kernel version using:
     uname -a

 - nvme-cli (apt-get install nvme-cli)
   - Ubuntu: sudo apt-get install nvme-cli
   - Fedora: sudo dnf -y install nvme-cli

 - blkzone (available through util-linux)
   - Ubuntu: sudo apt-get install util-linux
   - Fedora: sudo dnf -y install util-linux-ng
   - CentOS: sudo yum -y install util-linux-ng

 - a valid container (podman) environment
   - If you do not have a container environment installed, please see [this
     link](https://podman.io/getting-started/installation)

 - installed containers:
   - zfio - contains latest fio compiled with zone capacity support
   - zrocksdb - contains rocksdb with zenfs built-in
   - zzenfs - contains the zenfs tool to inspect the zenfs file-system

   The container can be installed with:
     cd recipes/docker; sudo ./build.sh

   The container installation can be verified by listing the image:
     sudo podman images zfio
     sudo podman images zrocksdb
     sudo podman images zzenfs

  - matplotlib (e.g. through pip3)
      https://matplotlib.org/stable/users/installing.html

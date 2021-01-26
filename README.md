# zbdbench: benchmark zoned block devices

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

 - a valid docker environment
   - If you do not have a docker environment installed, please see:
     - Ubuntu: https://docs.docker.com/engine/install/ubuntu/
     - Fedora: https://docs.docker.com/engine/install/fedora/
     - Centos: https://docs.docker.com/engine/install/centos/

 - installed docker containers:
   - zfio - contains latest fio compiled with zone capacity support
   - zrocksdb - contains rocksdb with zenfs built-in
   - zzenfs - contains the zenfs tool to inspect the zenfs file-system

   The container can be installed with:
     cd recipes/docker; sudo ./build.sh

   The container installation can be verified by listing the docker image:
     sudo docker images zfio
     sudo docker images zrocksdb
     sudo docker images zzenfs

Getting Started
---------------

The run.py script runs a set of predefined benchmarks on a block device.

The block device does not have to be zoned, although the workloads will work
on both types of block devices.

The script performs a set of checks before running the benchmarks, such as
validating that it is about to write to a block device, not mounted, and ready.

After all benchmarks have run, their output is availble in:

    output/YYYYMMDDHHMMSS (date format is replaced with the current time)

Each benchmark has a report function, which creates a csv file with the
specific output. See the section below for the csv format for each benchmark.

To execute the benchmarks, run:

    sudo ./run.py -d /dev/nvmeXnY

If you have the latest fio installed, you may skip the docker installation and
run the benchmarks using the system commands.

    sudo ./run.py -d /dev/nvmeXnY -c system

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

Regenerate a report

    ./run.py -b fio_zone_mixed -r output/YYYYMMDDHHMMSS

Benchmarks
----------

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


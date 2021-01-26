import subprocess
import re
import sys

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

    # Helpers
    def docker_sys_cmd(self, dev):
        return "docker run -v \"%s:%s\" -v \"%s:/output\" --privileged=true" % (dev, dev, self.output)

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

# Helper functions shared by scripts
def is_dev_zoned(dev):
    devname = dev.strip('/dev/')

    with open('/sys/block/%s/queue/zoned' % devname, 'r') as f:
        res = f.readline()

    return ("host-managed" in res)

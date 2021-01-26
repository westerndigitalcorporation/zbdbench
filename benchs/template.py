from base import base_benches, Bench

class Run(Bench):

    def __init__(self):
        pass

    def id(self):
        return "template"

    def setup(self, dev, container, output):
        super(Run, self).setup(output)

        self.discard_dev(dev)

    def run(self, dev, container):
        bdev = self.sys_container_dev(dev, container)
        fio_params = "fio_params"
        self.run_cmd(dev, container, 'fio', fio_param)

    def teardown(self, dev, container):
        pass

    def report(self):
        pass

# Uncomment to enable benchmark
#base_benches.append(Run())

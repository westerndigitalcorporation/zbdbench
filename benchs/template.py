from base import base_benches, Bench, Plot

class BenchPlot(Plot):

    def __init__(self, csv_file):
        super().__init__(csv_file)

    def myplot(self):
        pass

class Run(Bench):

    def __init__(self):
        pass

    def id(self):
        return "template"

    def setup(self, dev, container, output, arguments):
        super(Run, self).setup(container, output, arguments)

        self.discard_dev(dev)

    def required_host_tools(self):
        return super().required_host_tools() |  {'some_tool'}

    def required_container_tools(self):
        return super().required_container_tools() |  {'some_tool'}

    def run(self, dev, container):
        bdev = self.sys_container_dev(dev, container)

        ## SPDK FIO plugin support template - start
        if self.spdk_path:
            #spdk specific args
            extra = extra + f" --ioengine={self.spdk_path}/spdk/build/fio/spdk_bdev --spdk_json_conf={self.spdk_path}/spdk/bdev_zoned_uring.json --thread=1 "
            # For non container env:
            # 1. Provide --spdk-path cmdline arg
            # 2. Update --ioengine, --spdk_json_conf & --thread
            # 3. Replace nvme dev with json bdev
            if container == 'no':
                # Invoe script to checkout & build SPDK for Host system
                spdk_build("spdk/uring", self.spdk_path, dev)

                # Replace the nvme physical dev with spdk bdev.
                # For '-c yes' case, we pass the nvme dev as-is and further
                dev = spdk_bdev
        else:
            # Non SPDK case (use required fio ioengine, e.g. libaio etc. )
            extra = extra + ' --ioengine=libaio '
        ## SPDK FIO plugin support template - end

        fio_params = "fio_params" + extra
        self.run_cmd(dev, container, 'fio', fio_param)

    def teardown(self, dev, container):
        pass

    def report(self):
        # return csv_file
        pass

    def plot(self, csv_files):
        from plotter import matplotlib_plotter
        plot = matplotlib_plotter.Plot(self.output, csv_files)
        #Implement plotting in plot.gen_TEMPLATE
        plot.gen_TEMPLATE()

# Uncomment to enable benchmark
#base_benches.append(Run())

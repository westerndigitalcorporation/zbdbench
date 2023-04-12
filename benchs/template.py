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

    def setup(self, dev, container, output):
        super(Run, self).setup(container, output)

        self.discard_dev(dev)

    def required_host_tools(self):
        return super().required_host_tools() |  {'some_tool'}

    def required_container_tools(self):
        return super().required_container_tools() |  {'some_tool'}

    def run(self, dev, container):
        bdev = self.sys_container_dev(dev, container)
        fio_params = "fio_params"
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

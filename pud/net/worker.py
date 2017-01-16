import sys
import logbook.queues
import optparse
import gevent
import zerorpc
import platform
from . import discovery
from ..interface import Device, available_protocols, load_protocol


class WorkerService:
    def __init__(self):
        self._devices = {}

    @staticmethod
    def available_protocols():
        return available_protocols

    def load_protocol(self, *protocols):
        load_protocol(*protocols)
        self.scan_devices()
        return list(d for p in protocols for d in self.devices(p))

    def devices(self, protocol=None):
        def gen():
            for path, dev in self._devices.items():
                yield path, dev.protocol
        return list(gen())

    def scan_devices(self):
        for dev in Device.instances():
            self._devices[dev.path] = dev
        return self.devices()

    def open(self, path):
        self._devices[path].open()

    def close(self, path):
        self._devices[path].close()

    def info(self, path):
        dev = self._devices[path]
        return dict(
            path=dev.path,
            vendor=dev.raw_vendor,
            model=dev.raw_model,
            revision=dev.raw_revision,
            serial=dev.raw_serial,
            capacity=dev.capacity,
            sector_size=dev.sector_size,
            command_fields=list(f for f in dev.command_fields if f[0] != '_'),
        )

    def send(self, path, cmd):
        dev = self._devices[path]
        with dev:
            cmd_ = dev.create_command(**cmd)
            dev.send(cmd_)

            return dict(
                    (k, getattr(cmd_, k, None))
                    for k in dev.command_fields)


def main():
    parser = optparse.OptionParser()
    parser.add_option("-s", "--xsub", dest="xsub", help="Master's subscriber endpoint", action="append")
    parser.add_option("-e", "--endpoint", dest="endpoint", help="Worker rpc endpoint", action="append")
    parser.add_option("-p", "--protocol", dest="protocol", help="Specifying pre-loading protocol", action="append")
    parser.add_option("-l", "--available-protocols", dest="available", help="List all available protocols", action="store_true")
    parser.add_option("-q", "--quite", dest="quite", help="Turn off stdout log output", action="store_true")
    parser.add_option("-z", "--zeromq-log", dest="zmqlog", help="Specifying ZeroMQ log subscriber", action="append")

    options, args = parser.parse_args()
    if options.available:
        w = WorkerService()
        for protocol in w.available_protocols():
            print(protocol)
        exit(0)
    if options.xsub is None or options.endpoint is None:
        parser.print_help()
        exit(2)
    if options.protocol is None:
        options.protocol = []
    if not options.quite:
        logbook.StreamHandler(sys.stdout, bubble=True).push_application()
    if options.zmqlog:
        logbook.Processor(lambda r: r.extra.__setitem__('from', platform.node())).push_application()
        for ep in options.zmqlog:
            logbook.queues.ZeroMQHandler(ep, multi=True, bubble=True).push_application()

    d = discovery.DiscoveryService()
    d.add_subs(*options.xsub)
    disc_job = gevent.spawn(d.run)

    w = WorkerService()
    w.load_protocol(*options.protocol)
    s = zerorpc.Server(w)
    for ep in options.endpoint:
        s.bind(ep)
    d.add_tags("pud-worker")
    d.add_endpoints(*options.endpoint)
    gevent.joinall([
        disc_job,
        gevent.spawn(s.run)
        ])

if __name__ == "__main__":
    main()

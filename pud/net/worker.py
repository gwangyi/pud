import optparse
import gevent
import zerorpc
from . import discovery
from ..interface import Device, available_protocols, load_protocol


class WorkerService:
    def __init__(self):
        self._devices = {}

    def available_protocols(self):
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
        for dev in Device.instances:
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

    options, args = parser.parse_args()
    if options.xsub is None or len(args) == 0:
        parser.print_help()
        exit(2)

    d = discovery.DiscoveryService()
    d.add_subs(*options.xsub)
    disc_job = gevent.spawn(d.run)

    s = zerorpc.Server(WorkerService())
    for ep in args:
        s.bind(ep)
    d.add_tags("pud-worker")
    d.add_endpoints(*args)
    gevent.joinall([
        disc_job,
        gevent.spawn(s.run)
        ])

if __name__ == "__main__":
    main()

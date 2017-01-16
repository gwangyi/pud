from . import Device, Command
import random


class DummyDevice(Device):
    command_fields = ['result']

    def __init__(self, path):
        super().__init__(path,
                         b'DUMMY', b'1.00', b'DUMMYDISK',  # vendor, revision, model
                         "{:010x}".format(id(self)).encode('ascii'),  # serial
                         2048576, 512)  # capacity, sector_size

    def _open(self):
        print("open {}".format(self.path))

    def _close(self):
        print("close {}".format(self.path))

    def create_command(self, **kwargs):
        return DummyCommand(**kwargs)

    def send(self, command):
        print(command.__dict__)
        command.result = True


class DummyCommand(Command):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


@Device.register_enumerator
def dummy_devices():
    for dev in range(random.randint(1, 10)):
        dev_path = "/dev/dummy/" + bytes((dev + 97,)).decode('ascii')
        yield DummyDevice(dev_path)


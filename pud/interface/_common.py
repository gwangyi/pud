import weakref
import importlib
import pkgutil
import typing

from ..util import ContextType, EnumerableType, ContextObject, Enumerable


def _sanitize(v: bytes) -> str:
    return bytes(ch if 32 <= ch < 127 else 46 for ch in v).decode('ascii')


def _human(n: int) -> str:
    if n is None:
        return None
    postfixes = "kMGTPE"
    idx = -1
    if n < 1000:
        return "{:.2f} B".format(n)
    while n >= 1000:
        idx += 1
        n /= 1000
    return "{:.2f} {}B".format(n, postfixes[idx])


class DeviceType(EnumerableType, ContextType):
    def __new__(mcs, what, bases, members):
        if 'protocol' not in members:
            _, members['protocol'] = members['__module__'].rsplit('.', 1)
        return super().__new__(mcs, what, bases, members)


class Device(Enumerable, ContextObject, metaclass=DeviceType):
    _base_ = True
    _weakrefs = weakref.WeakValueDictionary()

    protocol = ''
    command_fields = []

    def __init__(self, path: str,
            vendor: bytes, model: bytes, revision: bytes,
            serial: bytes, capacity: int, sector_size: int):
        self.path = path
        self.raw_vendor = vendor
        self.raw_model = model
        self.raw_revision = revision
        self.raw_serial = serial
        self.capacity = capacity
        self.sector_size = sector_size

        self.vendor = _sanitize(vendor)
        self.model = _sanitize(model)
        self.revision = _sanitize(revision)
        self.serial = _sanitize(serial)

        self._open_depth = 0

        self._weakrefs[id(self)] = self

    def __del__(self):
        self.close()

    def __repr__(self):
        fmt = "<{}: {path} vendor={vendor} revision={revision}, mode={model}, serial={serial}, " \
                "capacity={capacity}, sector_size={sector_size}>"
        if hasattr(self, '__qualname__'):
            name = type(self).__qualname__
        else:
            name = type(self).__name__

        return fmt.format(name,
                path=self.path,
                vendor=self.vendor,
                revision=self.revision,
                model=self.model,
                serial=self.serial,
                capacity=_human(self.capacity * self.sector_size),
                sector_size=self.sector_size)

    def open(self):
        if self._open_depth > 0:
            self._open_depth += 1
            return self

        self._open()
        self._open_depth = 1
        return self

    def close(self):
        if self._open_depth > 1:
            self._open_depth -= 1
        elif self._open_depth == 1:
            self._close()
            self._open_depth = 0
        else:
            self._open_depth = 0
        return self

    def __enter__(self):
        self.open()
        super().__enter__()

    def __exit__(self, exc_type, value, tb):
        super().__exit__(exc_type, value, tb)
        self.close()
            
    def _open(self):
        raise NotImplementedError

    def _close(self):
        raise NotImplementedError

    def create_command(self, **kwargs) -> 'Command':
        raise NotImplementedError

    def send(self, command: 'Command'):
        raise NotImplementedError


class Command:
    def send(self, target: typing.Optional[Device]=None):
        if target is None:
            target = Device.current
            if target is None:
                raise RuntimeError("Device context is not specified")

        return target.send(self)


def command(target: typing.Optional[Device]=None, **kwargs) -> Command:
    if target is None:
        target = Device.current
        if target is None:
            raise RuntimeError("Device context is not specified")
    return Device.current.create_command(**kwargs)


def load_protocol(*protocols):
    for protocol in protocols:
        importlib.import_module('..' + protocol, __name__)


def available_protocols():
    interface = importlib.import_module('..', __name__)
    for _, mod, _ in pkgutil.walk_packages(interface.__path__):
        if mod[0:1] != '_':
            yield mod

available_protocols = list(available_protocols())  # type: typing.List[str]


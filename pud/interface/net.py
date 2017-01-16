from . import Device, Command
from ..net import discovery
import zerorpc
import gevent
import urllib.parse


class NetDevice(Device):
    def __init__(self, path):
        url = urllib.parse.urlparse(path)
        ep = urllib.parse.urlunparse(url[0:2] + ('', '', '', ''))
        self._client = zerorpc.Client()
        self._client.connect(ep)
        info = self._client.info(url.path)
        self._remote_path = url.path
        self.command_fields = info['command_fields']
        
        super().__init__(path,
                         info['vendor'], info['model'], info['revision'],
                         info['serial'], info['capacity'], info['sector_size'])

    def _open(self):
        self._client('open', self._remote_path)

    def _close(self):
        self._client('close', self._remote_path)

    def create_command(self, **kwargs):
        return NetCommand(**kwargs)

    def send(self, command):
        ret = self._client.send(self._remote_path, command.__dict__)
        command.__dict__.update(ret)


class NetCommand(Command):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


_discovery_service = discovery.DiscoveryService()
gevent.spawn(_discovery_service.run)


def add_pubs(*eps):
    _discovery_service.add_pubs(*eps)


@Device.register_enumerator
def net_devices():
    for ep, tags in _discovery_service.query('pud-worker'):
        c = zerorpc.Client()
        c.connect(ep)
        url = urllib.parse.urlparse(ep)
        for dev, protocol in c.devices():
            yield NetDevice(urllib.parse.urlunparse(url[0:2] + (dev, '', '', '')))

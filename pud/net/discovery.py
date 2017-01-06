import zerorpc
import gevent
import time
import typing


class DiscoveryService:
    timeout = 15

    def __init__(self):
        self._discovered = {}
        self._endpoints = set()
        self._tags = []
        self._pub = zerorpc.Publisher()
        self._sub = zerorpc.Subscriber(DiscoveryRPC(self))

        def reg():
            while True:
                for ep in self._endpoints:
                    self._pub.register(ep, self._tags)
                gevent.sleep(self.timeout)

        gevent.spawn(reg)

    def add_pubs(self, *pubs):
        for pub in pubs:
            self._sub.connect(pub)

    def add_subs(self, *subs):
        for sub in subs:
            self._pub.connect(sub)

    def add_endpoints(self, *eps: typing.List[str]):
        for ep in eps:
            self._endpoints.add(ep)
            self._pub.register(ep, self._tags)

    def add_tags(self, *tags: typing.List[str]):
        self._tags.extend(tags)
        for ep in self._endpoints:
            self._pub.register(ep, self._tags)

    def register(self, ep, tags):
        if isinstance(tags, (list, tuple)):
            tags = set(tags)
        else:
            tags = set((tags,))
        self._discovered[ep] = (tags, time.time())

    def query(self, tag=None):
        def gen():
            expired = set()
            for ep, info in self._discovered.items():
                tags, stamp = info
                if stamp + self.timeout < time.time():
                    expired.add(ep)
                elif tag is None or tag in tags:
                    yield ep, tags
            for ep in expired:
                del self._discovered[ep]
        return list(gen())

    def run(self):
        self._sub.run()


class DiscoveryRPC:
    def __init__(self, service):
        self._service = service

    def register(self, ep, tags):
        self._service.register(ep, tags)


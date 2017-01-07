class ContextType(type):
    def __init__(cls, what, bases, members):
        base = members.get('_base_', False)

        super().__init__(what, bases, members)

        if base:
            cls._base_ = cls
            cls._context_stack = [None]

    @property
    def current(cls):
        return cls._context_stack[-1]


class EnumerableType(type):
    def __init__(cls, what, bases, members):
        base = members.get('_base_', False)

        super().__init__(what, bases, members)

        if base:
            cls._base_ = cls
            cls._enumerators = dict()

    def register_enumerator(cls, key, f=None):
        if f is None and hasattr(key, '__call__'):
            f = key
            _, protocol = f.__module__.rsplit('.', 1)

        def decorator(func):
            cls._enumerators[protocol] = func
            return func

        if f is None:
            return decorator
        else:
            return decorator(f)

    def query_instances(cls, *keys, **kwargs):
        if len(keys) == 0:
            enumerators = cls._enumerators.values()
        else:
            enumerators = (v for k, v in cls._enumerators.items() if k in keys)

        def generator():
            for instances in enumerators:
                for instance in instances():
                    if False not in (getattr(instance, k, None) == v for k, v in kwargs.items()):
                        yield instance
        return list(generator())

    @property
    def instances(cls):
        return cls.query_instances()


class Enumerable(metaclass=EnumerableType):
    _base_ = True


class ContextObject(metaclass=ContextType):
    _base_ = True

    def __enter__(self):
        self._context_stack.append(self)

    def __exit__(self, exc_type, value, tb):
        if self is not type(self).current:
            raise ValueError("Invalid context state")
        self._context_stack.pop()


import ctypes
import typing


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


class Buffer:
    def __init__(self, size_or_bytes: typing.Union[int, bytes]):
        if isinstance(size_or_bytes, int):
            self._buffer = ctypes.create_string_buffer(size_or_bytes)
            self._as_parameter_ = self._buffer
        else:
            self._buffer = ctypes.create_string_buffer(len(size_or_bytes))
            self._as_parameter_ = self._buffer
            ctypes.memmove(self._buffer, size_or_bytes, len(Size_or_bytes))

    def resize(self, size):
        if ctypes.sizeof(self._buffer) < size:
            ctypes.resize(self._buffer, size)
        self._as_parameter_ = (ctypes.c_char * size).from_buffer(self._buffer)

    @property
    def raw(self):
        return self._as_parameter_.raw

    @raw.setter
    def raw(self, val):
        self._as_parameter_.raw = val

    @property
    def value(self):
        return self._as_parameter_.value

    @value.setter
    def value(self, val):
        self._as_parameter_.value = val

    def __len__(self):
        return len(self._as_parameter_)

    def __getitem__(self, item):
        return self._as_parameter_[item]

    def __setitem__(self, item, val):
        self._as_parameter_[item] = val

    def __bytes__(self):
        return bytes(self._as_parameter_)


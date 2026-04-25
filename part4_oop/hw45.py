from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from part4_oop.interfaces import Cache, HasCache, Policy, Storage

K = TypeVar("K")
V = TypeVar("V")


@dataclass
class DictStorage(Storage[K, V]):
    _data: dict[K, V] = field(default_factory=dict, init=False)

    def set(self, key: K, value: V) -> None:
        self._data[key] = value

    def get(self, key: K) -> V | None:
        return self._data.get(key)

    def exists(self, key: K) -> bool:
        return key in self._data

    def remove(self, key: K) -> None:
        self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()


@dataclass
class FIFOPolicy(Policy[K]):
    capacity: int = 5
    _order: list[K] = field(default_factory=list, init=False)

    def register_access(self, key: K) -> None:
        if key not in self._order:
            self._order.append(key)

    def get_key_to_evict(self) -> K | None:
        if len(self._order) > self.capacity:
            return self._order[0]
        return None

    def remove_key(self, key: K) -> None:
        if key in self._order:
            self._order.remove(key)

    def clear(self) -> None:
        self._order.clear()

    @property
    def has_keys(self) -> bool:
        return len(self._order) > 0


@dataclass
class LRUPolicy(Policy[K]):
    capacity: int = 5
    _order: list[K] = field(default_factory=list, init=False)

    def register_access(self, key: K) -> None:
        if key in self._order:
            self._order.remove(key)
        self._order.append(key)

    def get_key_to_evict(self) -> K | None:
        if len(self._order) > self.capacity:
            return self._order[0]
        return None

    def remove_key(self, key: K) -> None:
        if key in self._order:
            self._order.remove(key)

    def clear(self) -> None:
        self._order.clear()

    @property
    def has_keys(self) -> bool:
        return len(self._order) > 0


@dataclass
class LFUPolicy(Policy[K]):
    capacity: int = 5
    _key_counter: dict[K, int] = field(default_factory=dict, init=False)
    _last_key: K | None = field(default=None, init=False)

    @property
    def has_keys(self) -> bool:
        return bool(self._key_counter)

    def register_access(self, key: K) -> None:
        count = self._key_counter.get(key, 0)
        self._key_counter[key] = count + 1
        if count == 0:
            self._last_key = key

    def get_key_to_evict(self) -> K | None:
        if len(self._key_counter) <= self.capacity:
            return None

        min_freq = min(self._key_counter.values())
        min_keys = [k for k, v in self._key_counter.items() if v == min_freq]

        if len(min_keys) == 1 and min_keys[0] == self._last_key:
            second = self._second_min_freq(self._last_key)
            for k, v in self._key_counter.items():
                if k != self._last_key and v == second:
                    return k
        return min_keys[0]

    def remove_key(self, key: K) -> None:
        self._key_counter.pop(key, None)
        if self._last_key == key:
            self._last_key = None

    def clear(self) -> None:
        self._key_counter.clear()
        self._last_key = None

    def _second_min_freq(self, exclude: K) -> int | None:
        second = None
        for k, v in self._key_counter.items():
            if k == exclude:
                continue
            if second is None or v < second:
                second = v
        return second


class MIPTCache(Cache[K, V]):
    def __init__(self, storage: Storage[K, V], policy: Policy[K]) -> None:
        self.storage = storage
        self.policy = policy

    def set(self, key: K, value: V) -> None:
        self.policy.register_access(key)

        if self.storage.exists(key):
            self.storage.set(key, value)
            return

        evict = self.policy.get_key_to_evict()
        if evict is not None:
            self.storage.remove(evict)
            self.policy.remove_key(evict)

        self.storage.set(key, value)

    def get(self, key: K) -> V | None:
        value = self.storage.get(key)
        if value is not None:
            self.policy.register_access(key)
        return value

    def exists(self, key: K) -> bool:
        return self.storage.exists(key)

    def remove(self, key: K) -> None:
        self.storage.remove(key)
        self.policy.remove_key(key)

    def clear(self) -> None:
        self.storage.clear()
        self.policy.clear()


class CachedProperty:
    def __init__(self, func: Callable[..., Any]) -> None:
        self.func = func
        self.attr_name: str | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        self.attr_name = name

    def __get__(self, instance: HasCache[Any, Any] | None, owner: type) -> Any:
        if instance is None:
            return self
        cache = instance.cache
        key = self.attr_name
        if cache.exists(key):
            return cache.get(key)
        value = self.func(instance)
        cache.set(key, value)
        return value

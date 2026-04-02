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
        if len(self._order) >= self.capacity:
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
        if len(self._order) >= self.capacity:
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
    _order: list[K] = field(default_factory=list, init=False)

    @property
    def has_keys(self) -> bool:
        return len(self._key_counter) > 0

    def register_access(self, key: K) -> None:
        current = self._key_counter.get(key, 0)
        self._key_counter[key] = current + 1
        if current == 0:
            self._order.append(key)

    def get_key_to_evict(self) -> K | None:
        if len(self._key_counter) < self.capacity:
            return None

        min_keys = self._get_keys_with_min_freq()
        is_over = len(self._key_counter) > self.capacity
        only_one = len(min_keys) == 1
        is_last = only_one and min_keys[0] == self._order[-1]
        if is_over and is_last:
            return self._get_second_min_key(min_keys[0])
        return min_keys[0]

    def remove_key(self, key: K) -> None:
        if key in self._key_counter:
            self._key_counter.pop(key, None)
            self._order.remove(key)

    def clear(self) -> None:
        self._key_counter.clear()
        self._order.clear()

    def _get_keys_with_min_freq(self) -> list[K]:
        min_count = min(self._key_counter.values())
        return [k for k in self._order if self._key_counter[k] == min_count]

    def _get_second_min_key(self, excluded_key: K) -> K | None:
        best_key = None
        best_freq = None
        for key in self._order:
            if key == excluded_key:
                continue
            freq = self._key_counter[key]
            if best_freq is None or freq < best_freq:
                best_freq = freq
                best_key = key
        return best_key


class MIPTCache(Cache[K, V]):
    def __init__(self, storage: Storage[K, V], policy: Policy[K]) -> None:
        self.storage = storage
        self.policy = policy

    def set(self, key: K, value: V) -> None:
        if self.storage.exists(key):
            self.policy.register_access(key)
            self.storage.set(key, value)
            return

        evict = self.policy.get_key_to_evict()
        if evict is not None:
            self.storage.remove(evict)
            self.policy.remove_key(evict)

        self.policy.register_access(key)
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
        cached = cache.get(key)
        if cached is not None:
            return cached
        value = self.func(instance)
        cache.set(key, value)
        return value

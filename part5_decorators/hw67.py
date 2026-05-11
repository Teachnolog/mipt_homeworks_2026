import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Any, ParamSpec, Protocol, TypeVar
from urllib.request import urlopen

INVALID_CRITICAL_COUNT = "Breaker count must be positive integer!"
INVALID_RECOVERY_TIME = "Breaker recovery time must be positive integer!"
VALIDATIONS_FAILED = "Invalid decorator args."
TOO_MUCH = "Too much requests, just wait."
INTERNAL_ERROR_MSG = "Internal circuit breaker error"


P = ParamSpec("P")
R_co = TypeVar("R_co", covariant=True)


class CallableWithMeta(Protocol[P, R_co]):
    __name__: str
    __module__: str

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R_co: ...


class BreakerError(Exception):
    def __init__(self, func_name: str, block_time: datetime) -> None:
        super().__init__(TOO_MUCH)
        self.func_name = func_name
        self.block_time = block_time


@dataclass
class _State:
    failures: int = 0
    block_start: datetime | None = None
    block_until: datetime | None = None


class CircuitBreaker:
    def __init__(
        self,
        critical_count: int = 5,
        time_to_recover: int = 30,
        triggers_on: type[Exception] = Exception,
    ) -> None:
        errors = []
        if not isinstance(critical_count, int) or critical_count <= 0:
            errors.append(ValueError(INVALID_CRITICAL_COUNT))
        if not isinstance(time_to_recover, int) or time_to_recover <= 0:
            errors.append(ValueError(INVALID_RECOVERY_TIME))
        if errors:
            raise ExceptionGroup(VALIDATIONS_FAILED, errors)
        self.critical_count = critical_count
        self.time_to_recover = time_to_recover
        self.triggers_on = triggers_on

    def __call__(self, func: CallableWithMeta[P, R_co]) -> CallableWithMeta[P, R_co]:
        state = _State()

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R_co:
            self.__check_blocked_state(state, func)
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                self.__handle_exception(state, e, func)
                raise
            else:
                state.failures = 0
                return result

        return wrapper

    def __check_blocked_state(self, state: _State, func: Any) -> None:
        if state.block_until is None:
            return

        now = datetime.now(UTC)
        if now < state.block_until:
            if state.block_start is None:
                raise RuntimeError(INTERNAL_ERROR_MSG)
            raise BreakerError(
                func_name=f"{func.__module__}.{func.__name__}",
                block_time=state.block_start,
            )
        state.block_until = None
        state.block_start = None
        state.failures = 0

    def __handle_exception(self, state: _State, exception: Exception, func: Any) -> None:
        if not isinstance(exception, self.triggers_on):
            return
        state.failures += 1
        if state.failures >= self.critical_count:
            block_start = datetime.now(UTC)
            state.block_start = block_start
            state.block_until = block_start + timedelta(seconds=self.time_to_recover)
            raise BreakerError(
                func_name=f"{func.__module__}.{func.__name__}",
                block_time=block_start,
            ) from exception


circuit_breaker = CircuitBreaker(5, 30, Exception)


def get_comments(post_id: int) -> Any:
    """
    Получает комментарии к посту

    Args:
        post_id (int): Идентификатор поста

    Returns:
        list[dict[int | str]]: Список комментариев
    """
    response = urlopen(f"https://jsonplaceholder.typicode.com/comments?postId={post_id}")
    return json.loads(response.read())


if __name__ == "__main__":
    comments = get_comments(1)

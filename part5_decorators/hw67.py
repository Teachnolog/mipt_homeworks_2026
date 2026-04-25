import json
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Any, NoReturn, ParamSpec, Protocol, TypeVar
from urllib.request import urlopen

INVALID_CRITICAL_COUNT = "Breaker count must be positive integer!"
INVALID_RECOVERY_TIME = "Breaker recovery time must be positive integer!"
VALIDATIONS_FAILED = "Invalid decorator args."
TOO_MUCH = "Too much requests, just wait."
INTERNAL_ERROR_MSG = "Internal circuit breaker error"

KEY_FAILURES = "failures"
KEY_BLOCK_START = "block_start"
KEY_BLOCK_UNTIL = "block_until"


P = ParamSpec("P")
R_co = TypeVar("R_co", covariant=True)


class CallableWithMeta(Protocol[P, R_co]):
    __name__: str
    __module__: str

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R_co: ...


class BreakerError(Exception):
    def __init__(self, func_name: str, block_time: datetime, cause: Exception | None = None) -> None:
        super().__init__(TOO_MUCH)
        self.func_name = func_name
        self.block_time = block_time
        if cause is not None:
            self.__cause__ = cause


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
        state: dict[str, Any] = {
            KEY_FAILURES: 0,
            KEY_BLOCK_START: None,
            KEY_BLOCK_UNTIL: None,
        }

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R_co:
            self.check_blocked_state(state, func)
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                self.handle_exception(state, e, func)
                raise
            else:
                state[KEY_FAILURES] = 0
                return result

        return wrapper

    def check_blocked_state(self, state: dict[str, Any], func: Any) -> None:
        block_until = state[KEY_BLOCK_UNTIL]
        if block_until is None:
            return

        now = datetime.now(UTC)
        if now < block_until:
            block_start = state[KEY_BLOCK_START]
            if block_start is None:
                raise RuntimeError(INTERNAL_ERROR_MSG)
            raise BreakerError(
                func_name=f"{func.__module__}.{func.__name__}",
                block_time=block_start,
                cause=None,
            )
        state[KEY_BLOCK_UNTIL] = None
        state[KEY_BLOCK_START] = None
        state[KEY_FAILURES] = 0

    def handle_exception(
        self,
        state: dict[str, Any],
        exception: Exception,
        func: Any,
    ) -> NoReturn:
        if not isinstance(exception, self.triggers_on):
            raise exception

        state[KEY_FAILURES] += 1
        if state[KEY_FAILURES] >= self.critical_count:
            block_start = datetime.now(UTC)
            state[KEY_BLOCK_START] = block_start
            state[KEY_BLOCK_UNTIL] = block_start + timedelta(seconds=self.time_to_recover)
            raise BreakerError(
                func_name=f"{func.__module__}.{func.__name__}",
                block_time=block_start,
                cause=exception,
            ) from exception
        raise exception


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

from typing import Optional, TypeVar

T = TypeVar("T")


def unwrap(value: Optional[T]) -> T:
    assert value is not None

    return value

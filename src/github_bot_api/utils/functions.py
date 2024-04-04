from typing import Optional, TypeVar, overload

T = TypeVar("T")


@overload
def coalesce(value: Optional[T], fallback: T) -> T: ...


@overload
def coalesce(value: Optional[T], *values: Optional[T]) -> Optional[T]: ...


@overload
def coalesce(value: Optional[T], *values: Optional[T], fallback: T) -> T: ...


def coalesce(value: Optional[T], *values: Optional[T], fallback: Optional[T] = None) -> Optional[T]:
    """
    Returns the first value that is not `None`. If a not-None fallback is specified, the function is guaranteed
    to return a not-Non value.
    """

    if value is not None:
        return value
    value = next((x for x in values if x is not None), None)
    if value is not None:
        return value
    return fallback

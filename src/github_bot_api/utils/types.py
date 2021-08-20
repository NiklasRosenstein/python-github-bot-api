
import typing as t

T_co = t.TypeVar('T_co', covariant=True)


class Supplier(t.Protocol[T_co]):
  def __call__(self) -> T_co:
    pass

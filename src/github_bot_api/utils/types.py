
import typing as t

T_co = t.TypeVar('T_co', covariant=True)


class Supplier(t.Protocol[T_co]):
  """
  Protocol for value suppliers.
  """

  def __call__(self) -> T_co:
    " Return the value provided by the supplier. "

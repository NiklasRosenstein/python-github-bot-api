
import logging
import fnmatch
import typing as t
from dataclasses import dataclass, field
from .event import Event

T = t.TypeVar('T')
logger = logging.getLogger(__name__)


@dataclass
class EventHandler:
  event: str  #: An event name or #fnmatch pattern.
  func: t.Callable[[Event], bool]


@dataclass
class Webhook:
  """
  Represents a GitHub webhook that listens on an HTTP endpoint for events. Event handlers can be
  registered using the #@on() decorator or #register() method.
  """

  #: The webhook secret, if also configured on GitHub. When specified, the payload signature
  #: is checked before an event is accepted by the underlying HTTP framework.
  secret: t.Optional[str]

  handlers: t.List[EventHandler] = field(default_factory=list)

  @t.overload
  def listen(self, event: str) -> t.Callable[[T], T]:
    """
    Decorator to register an event handler function for the specified *event*. The event name
    can be an fnmatch pattern.
    """

  @t.overload
  def listen(self, event: str, func: t.Callable[[Event], bool]) -> None:
    """
    Directly register an event handler function.
    """

  def listen(self, event, func=None):
    if func is None:
      def wrapper(func):
        assert func is not None
        self.listen(event, func)
        return func
      return wrapper
    else:
      self.handlers.append(EventHandler(event, func))

  def dispatch(self, event: Event) -> bool:
    """
    Dispatch an event on the first handler that matches it.

    Returns #True only if the event was handled by a handler.
    """

    matched = False

    for handler in self.handlers:
      if fnmatch.fnmatch(event.name, handler.event):
        matched = True
        if handler.func(event):
          return True
    else:
      logger.info(f'Event %r (id: %r) goes {"unhandled" if matched else "unmatched"}.',
        event.name, event.delivery_id)

    return matched


"""
Registry for GitHub event handlers.
"""

import datetime
import fnmatch
import logging
import requests
import typing as t
from dataclasses import dataclass, field
from .event import Event
from .token import RefreshingTokenSupplier, TokenInfo

logger = logging.getLogger(__name__)
T = t.TypeVar('T')

if t.TYPE_CHECKING:
  import github


@dataclass
class Webhook:
  """
  Represents a GitHub webhook that listens on an HTTP endpoint for events. Event handlers can be
  registered using the #@on() decorator or #register() method.
  """

  @dataclass
  class Handler:
    event: str  #: An event name or #fnmatch pattern.
    func: t.Callable[[Event], bool]

  #: The webhook secret, if also configured on GitHub. When specified, the payload signature
  #: is checked before an event is accepted by the underlying HTTP framework.
  secret: t.Optional[str]

  handlers: t.List[Handler] = field(default_factory=list)

  def register(self, event: str, func: t.Callable[[Event], bool]) -> None:
    """
    Register an event handler function. The *event* must be the name of an event or an #fnmatch
    pattern that matches an event.
    """

    self.handlers.append(self.Handler(event, func))

  def on(self, event: str) -> t.Callable[[T], T]:
    """
    Decorator to register an event handler function. The *event* must be the name of an event or
    an #fnmatch pattern that matches an event name.
    """

    def wrapper(func):
      self.register(event, func)
      return func

    return wrapper

  def dispatch(self, event: Event) -> bool:
    """
    Dispatch an event on the first handler that matches it.

    Returns #True only if the event was handled by a handler.
    """

    matched = False

    for handler in self.handlers:
      if fnmatch.fnmatch(event.name, handler.event):
        matched = True
        if handler.func(event):  # type: ignore
          return True
    else:
      logger.info(f'Event %r (id: %r) goes {"unhandled" if matched else "unmatched"}.',
        event.name, event.delivery_id)


class App:
  """
  Represents a GitHub application that has access to the GitHub API via a JWT that is signed
  with the application's private key.
  """

  PUBLIC_GITHUB_V3_API_URL = 'https://api.github.com'
  PUBLIC_GITHUB_GRAPHQL_URL = 'https://api.github.com/graphql'

  def __init__(
    self,
    app_id: str,
    private_key: str,
    v3_api_url: t.Optional[str] = None,
    graphql_url: t.Optional[str] = None,
  ) -> None:

    self.app_id = app_id
    self.private_key = private_key
    self.token_supplier = RefreshingTokenSupplier(app_id, private_key)
    self.v3_api_url = v3_api_url
    self.graphql_url = graphql_url

  def refreshing_token(self, prefix: str = '') -> str:
    from nr.proxy import proxy
    return proxy[str](lambda: prefix + self.token_supplier().value)

  def _app_request(self, method, url, **args):
    if url.startswith('/'):
      url = (self.v3_api_url or self.PUBLIC_GITHUB_V3_API_URL) + url
    headers = {'Authorization': str(self.refreshing_token('Bearer '))}
    response = requests.request(method, url, headers=headers)
    response.raise_for_status()
    return response

  def get_installations(self) -> t.Dict[str, t.Any]:
    return self._app_request('GET', '/app/installations').json()

  def get_installation_access_token(self, installation_id: int) -> TokenInfo:
    data = self._app_request('POST', f'/app/installations/{installation_id}/access_tokens').json()
    issued_at = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    expires_at = datetime.datetime.strptime(data['expires_at'], '%Y-%m-%dT%H:%M:%S%z')
    return TokenInfo(issued_at, expires_at, 'token', data['token'])

  def get_installation_client(self, installation_id: int) -> 'github.Github':
    from github import Github
    token = self.get_installation_access_token(installation_id)
    return Github(token.value, base_url=self.v3_api_url or self.PUBLIC_GITHUB_V3_API_URL)

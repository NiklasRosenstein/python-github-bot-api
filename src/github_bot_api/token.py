
"""
Generate a JWT from a GitHub application private key.

Reference: https://docs.github.com/en/free-pro-team@latest/developers/apps/setting-up-your-development-environment-to-create-a-github-app
"""

import abc
import datetime
import logging
import threading
import time
import typing as t
from dataclasses import dataclass
import jwt
from .utils.types import Supplier

logger = logging.getLogger(__name__)


@dataclass
class TokenInfo:
  """
  Represents a token including it's expiration time, type and token string value.
  """

  #: The timestamp after which the token expires. This is in local client time.
  exp: int

  #: The type of the token. This is usually `Bearer` when using #create_jwt().
  type: str

  #: The token value, without the #type prefix.
  value: str

  @property
  def auth_header(self) -> str:
    " Return the full value to pass into an HTTP `Authorization` header for this token. "

    return f'{self.type} {self.value}'


def create_jwt(app_id: int, expires_in: int, private_key: str) -> TokenInfo:
  """
  Generate a JWT for a GitHub App.

  # Arguments
  app_id: The GitHub application ID.
  expires_in: The time until the token expires in seconds. GitHub does not allow
    an expiration time higher than 10 minutes (the token may be accepted but isn't valid
    for as long as you might expected).
  private_key: The RSA private key that was issued for the GitHub bot.

  # Returns
  The JWT as a #TokenInfo object.
  """

  now = int(time.time())
  exp = now + expires_in
  payload = {'iss': int(app_id), 'iat': now, 'exp': exp}
  token = jwt.encode(payload, private_key, algorithm='RS256')
  return TokenInfo(exp, 'Bearer', token)


class RefreshableTokenSupplier(Supplier[TokenInfo], metaclass=abc.ABCMeta):
  """
  Base class for token suppliers.
  """

  def __post_init__(self):
    self._cached_token: t.Optional[TokenInfo] = None
    self._lock: threading.Lock = threading.Lock()

  @abc.abstractmethod
  def _is_expired(self, token: TokenInfo) -> bool:
    pass

  @abc.abstractmethod
  def _new_token(self) -> TokenInfo:
    pass

  def __call__(self) -> TokenInfo:
    with self._lock:
      if self._cached_token is not None and not self._is_expired(self._cached_token):
        return self._cached_token
      self._cached_token = self._new_token()
      assert isinstance(self._cached_token, TokenInfo), type(self)
      return self._cached_token


@dataclass
class JwtSupplier(RefreshableTokenSupplier):
  """
  Supplies a JWT Bearer token, refreshing it shortly before it expires.
  """

  #: The ID of the GitHub application.
  app_id: int

  #: The RSA private key to sign the JWT with.
  private_key: str

  #: The expiration time for the token in seconds. Defaults to 10 minutes (the maximum allowed).
  expires_in: int = 600

  #: If the token is close to expire within this threshold (in seconds), it is renewed.
  threshold: int = 30

  # RefreshableTokenSupplier Overrides

  def _is_expired(self, token: TokenInfo) -> bool:
    return (token.exp - time.time()) <= self.threshold

  def _new_token(self) -> TokenInfo:
    logger.info('Refreshing JWT for app_id %r.', self.app_id)
    return create_jwt(self.app_id, self.expires_in, self.private_key)


@dataclass
class InstallationTokenSupplier(RefreshableTokenSupplier):
  """
  Supplies a token for the given installation ID.
  """

  #: The JWT token supplier.
  app_jwt: Supplier[TokenInfo]

  #: The installation id.
  installation_id: int

  #: The function performing a POST request, accepting as arguments the `Authorization` header
  #: and the installation id, returning the JSON payload.
  requestor: t.Callable[[str, int], t.Dict[str, str]]

  #: If the token is close to expire within this threshold (in seconds), it is renewed.
  threshold: int = 30

  # RefreshableTokenSupplier Overrides

  def _is_expired(self, token: TokenInfo) -> bool:
    return (token.exp - time.time()) <= self.threshold

  def _new_token(self) -> TokenInfo:
    logger.info('Fetching token for installation %s', self.installation_id)
    data = self.requestor(self.app_jwt().auth_header, self.installation_id)
    expires_at = datetime.datetime.strptime(data['expires_at'], '%Y-%m-%dT%H:%M:%S%z')
    return TokenInfo(int(expires_at.timestamp()), 'token', data['token'])

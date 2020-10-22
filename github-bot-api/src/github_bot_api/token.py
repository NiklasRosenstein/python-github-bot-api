
"""
Generate a JWT from a GitHub application private key.

Reference: https://docs.github.com/en/free-pro-team@latest/developers/apps/setting-up-your-development-environment-to-create-a-github-app
"""

import datetime
import logging
import jwt
import threading
import typing as t
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TokenInfo:
  issued_at: datetime.datetime
  expires_at: datetime.datetime
  type: str
  value: str

  @property
  def auth_header(self) -> str:
    return f'{self.type} {self.value}'


def generate_token(app_id: int, expires_in: int, private_key: str) -> TokenInfo:
  """
  Generate a JWT for a GitHub App.

  :param app_id: The GitHub application ID.
  :param expires_in: The time until the token expires in seconds. GitHub does not allow
    an expiration time higher than 10 minutes (the token may be accepted but isn't valid
    for as long as you might expected).
  :param private_key: The RSA private key that was issued for the GitHub bot.
  :return: The JWT.
  """

  # TODO(nrosenstein): You would expect that you need to use utcnow(), but GitHub doesn't
  #   accept it.
  now = datetime.datetime.now()
  exp = now + datetime.timedelta(seconds=expires_in)

  payload = {
    'iss': app_id,
    'iat': int(now.timestamp()),
    'exp': int(exp.timestamp()),
  }

  token = jwt.encode(payload, private_key, algorithm='RS256').decode('ascii')
  return TokenInfo(now, exp, 'Bearer', token)


@dataclass
class RefreshingTokenSupplier:
  """
  Supplier for a JWT token that automatically generates a new one if the last is close to expiry.
  """

  app_id: int
  private_key: str
  expires_in: int = 600
  refresh_after: int = 570
  _cached_token: t.Optional[TokenInfo] = None
  _lock: threading.Lock = field(default_factory=threading.Lock)

  def needs_refresh(self) -> bool:
    info = self._cached_token
    if info is None:
      return True
    max_time = info.issued_at + datetime.timedelta(seconds=self.refresh_after)
    return datetime.datetime.utcnow() >= max_time

  def __call__(self) -> TokenInfo:
    with self._lock:
      if self.needs_refresh():
        logger.info('Refreshing JWT for app_id %r.', self.app_id)
        self._cached_token = generate_token(self.app_id, self.expires_in, self.private_key)
      assert self._cached_token is not None
      return self._cached_token

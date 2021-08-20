
"""
Registry for GitHub event handlers.
"""

import logging
import sys
import threading
import typing as t
from dataclasses import dataclass
import requests
from . import __version__
from .token import InstallationTokenSupplier, JwtSupplier, TokenInfo

T = t.TypeVar('T')
logger = logging.getLogger(__name__)
user_agent = f'python/{sys.version.split()[0]} github-bot-api/{__version__}'

if t.TYPE_CHECKING:
  import github


@dataclass
class GithubApp:
  """
  Represents a GitHub application and all the required details.

  # Example

  ```py
  import os
  from github_bot_api import GithubApp

  with open(os.environ['PRIVATE_KEY_FILE']) as fp:
    private_key = fp.read()

  app = GithubApp(
    user_agent='my-bot/0.0.0',
    app_id=int(os.environ['APP_ID']),
    private_key=private_key)

  print(app.client.get_app().owner)
  ```
  """

  PUBLIC_GITHUB_V3_API_URL = 'https://api.github.com'

  #: User agent of the application. This will be respected in #get_user_agent().
  user_agent: str

  #: GitHub Application ID.
  app_id: int

  #: RSA private key to sign the JWT with.
  private_key: str

  #: GitHub API base URL. Defaults to the public GitHub API.
  v3_api_url: str = PUBLIC_GITHUB_V3_API_URL

  def __post_init__(self):
    self._jwt_supplier = JwtSupplier(self.app_id, self.private_key)
    self._lock = threading.Lock()
    self._installation_tokens: t.Dict[int, InstallationTokenSupplier] = {}

  def get_user_agent(self, installation_id: t.Optional[int] = None) -> str:
    """
    Create a user agent string for the PyGithub client, including the installation if specified.
    """

    user_agent = f'{self.user_agent} PyGithub/python (app_id={self.app_id}'
    if installation_id:
      user_agent += f', installation_id={installation_id})'
    return user_agent

  @property
  def jwt(self) -> TokenInfo:
    """
    Returns the JWT for your GitHub application. The JWT is the token to use with GitHub application APIs.
    """

    return self._jwt_supplier()

  @property
  def jwt_supplier(self) -> JwtSupplier:
    """
    Returns a new #JwtSupplier that is used for generating JWT tokens for your GitHub application.
    """

    return JwtSupplier(self.app_id, self.private_key)

  @property
  def client(self) -> 'github.Github':
    """
    Returns a PyGithub client for your GitHub application.

    Note that the client's token will expire after 10 minutes and you will have to create a new client or update the
    client's token with the value returned by #jwt. It is recommended that you create a new client for each atomic
    operation you perform.

    This requires you to install `PyGithub`.
    """

    import github
    return github.Github(
      jwt=self.jwt.value,
      base_url=self.v3_api_url,
      user_agent=self.get_user_agent())

  def __requestor(self, auth_header: str, installation_id: int) -> t.Dict[str, str]:
    return requests.post(
      self.v3_api_url.rstrip('/') + f'/app/installations/{installation_id}/access_tokens',
      headers={'Authorization': auth_header, 'User-Agent': user_agent},
    ).json()

  def get_installation_token_supplier(self, installation_id: int) -> InstallationTokenSupplier:
    """
    Create an #InstallationTokenSupplier for your GitHub application to act within the scope of the given
    *installation_id*.
    """

    with self._lock:
      return self._installation_tokens.setdefault(
        installation_id,
        InstallationTokenSupplier(
          self._jwt_supplier,
          installation_id,
          self.__requestor,
        )
      )

  def installation_token(self, installation_id: int) -> TokenInfo:
    """
    A short-hand to retrieve a new installation token for the given *installation_id*.
    """

    return self.get_installation_token_supplier(installation_id)()

  def installation_client(self, installation_id: int) -> 'github.Github':
    """
    Returns a PyGithub client for your GitHub application to act in the scope of the given *installation_id*.

    Note that the client's token will expire after 10 minutes and you will have to create a new client or update the
    client's token with the value returned by #jwt. It is recommended that you create a new client for each atomic
    operation you perform.

    This requires you to install `PyGithub`.
    """

    import github
    return github.Github(
      login_or_token=self.installation_token(installation_id).value,
      base_url=self.v3_api_url,
      user_agent=self.get_user_agent(installation_id))

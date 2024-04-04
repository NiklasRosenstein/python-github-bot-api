"""
Registry for GitHub event handlers.
"""

import dataclasses
import logging
import sys
import threading
import typing as t

import requests
import urllib3

from . import __version__
from .token import InstallationTokenSupplier, JwtSupplier, TokenInfo
from .utils.functions import coalesce

T = t.TypeVar("T")
logger = logging.getLogger(__name__)
user_agent = f"python/{sys.version.split()[0]} github-bot-api/{__version__}"

if t.TYPE_CHECKING:
    import github


@dataclasses.dataclass
class GithubClientSettings:
    """
    Settings for constructing a #github.Github client object.
    """

    base_url: t.Optional[str] = None
    user_agent: t.Optional[str] = None
    timeout: t.Optional[int] = None
    per_page: t.Optional[int] = None
    verify: t.Optional[bool] = None
    retry: t.Optional[urllib3.Retry] = None

    def update(self, other: "GithubClientSettings") -> "GithubClientSettings":
        result = GithubClientSettings()
        for field in dataclasses.fields(self):
            value = getattr(other, field.name)
            if value is None:
                value = getattr(self, field.name)
            setattr(result, field.name, value)
        return result

    def make_client(self, login_or_token: t.Optional[str] = None, jwt: t.Optional[str] = None) -> "github.Github":
        import github
        import github.Consts

        return github.Github(
            login_or_token=login_or_token,
            jwt=jwt,
            base_url=self.base_url or github.Consts.DEFAULT_BASE_URL,
            user_agent=self.user_agent or "PyGithub/Python",
            timeout=coalesce(self.timeout, github.Consts.DEFAULT_TIMEOUT),
            per_page=coalesce(self.per_page, github.Consts.DEFAULT_PER_PAGE),
            verify=coalesce(self.verify, True),
            retry=self.retry,
        )


@dataclasses.dataclass
class GithubApp:
    """
    Represents a GitHub application and all the required details.
    """

    PUBLIC_GITHUB_V3_API_URL = "https://api.github.com"

    user_agent: str
    """User agent of the application. This will be respected in #get_user_agent()."""

    app_id: int
    """GitHub Application ID."""

    private_key: str
    """RSA private key to sign the JWT with."""

    v3_api_url: str = PUBLIC_GITHUB_V3_API_URL
    """GitHub API base URL. Defaults to the public GitHub API."""

    def __post_init__(self):
        self._jwt_supplier = JwtSupplier(self.app_id, self.private_key)
        self._lock = threading.Lock()
        self._installation_tokens: t.Dict[int, InstallationTokenSupplier] = {}

    def _get_base_github_client_settings(self) -> GithubClientSettings:
        return GithubClientSettings(self.v3_api_url, self.get_user_agent())

    def get_user_agent(self, installation_id: t.Optional[int] = None) -> str:
        """
        Create a user agent string for the PyGithub client, including the installation if specified.
        """

        user_agent = f"{self.user_agent} PyGithub/python (app_id={self.app_id}"
        if installation_id:
            user_agent += f", installation_id={installation_id})"
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

    def app_client(self, settings: t.Union[GithubClientSettings, t.Dict[str, t.Any], None] = None) -> "github.Github":
        """
        Returns a PyGithub client for your GitHub application.

        Note that the client's token will expire after 10 minutes and you will have to create a new client or update the
        client's token with the value returned by #jwt. It is recommended that you create a new client for each atomic
        operation you perform.

        This requires you to install `PyGithub>=1.58`.
        """

        if isinstance(settings, dict):
            settings = GithubClientSettings(**settings)
        elif settings is None:
            settings = GithubClientSettings()

        settings = self._get_base_github_client_settings().update(settings)
        return settings.make_client(jwt=self.jwt.value)

    def __requestor(self, auth_header: str, installation_id: int) -> t.Dict[str, str]:
        return requests.post(
            self.v3_api_url.rstrip("/") + f"/app/installations/{installation_id}/access_tokens",
            headers={"Authorization": auth_header, "User-Agent": user_agent},
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
                ),
            )

    def installation_token(self, installation_id: int) -> TokenInfo:
        """
        A short-hand to retrieve a new installation token for the given *installation_id*.
        """

        return self.get_installation_token_supplier(installation_id)()

    def installation_client(
        self,
        installation_id: int,
        settings: t.Union[GithubClientSettings, t.Dict[str, t.Any], None] = None,
    ) -> "github.Github":
        """
        Returns a PyGithub client for your GitHub application to act in the scope of the given *installation_id*.

        Note that the client's token will expire after 10 minutes and you will have to create a new client or update the
        client's token with the value returned by #jwt. It is recommended that you create a new client for each atomic
        operation you perform.

        This requires you to install `PyGithub>=1.58`.
        """

        if isinstance(settings, dict):
            settings = GithubClientSettings(**settings)
        elif settings is None:
            settings = GithubClientSettings()

        token = self.installation_token(installation_id).value
        settings = self._get_base_github_client_settings().update(settings)
        return settings.make_client(login_or_token=token)

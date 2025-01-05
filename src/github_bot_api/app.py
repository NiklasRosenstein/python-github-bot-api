"""
Registry for GitHub event handlers.
"""

import dataclasses
import logging
import sys
import threading
import time
import typing as t
from urllib.parse import parse_qs, urlencode

import deprecated
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

    private_key: str = dataclasses.field(repr=False)
    """RSA private key to sign the JWT with."""

    client_id: t.Optional[str] = None
    """The GitHub App's OAuth client ID. This is required for OAuth2 authorization URL generation. Can be omitted
    if the app does not use OAuth2."""

    client_secret: t.Optional[str] = dataclasses.field(default=None, repr=False)
    """The GitHub App's OAuth client secret. This is required for OAuth2 authorization URL generation. Can be omitted
    if the app does not use OAuth2. Note that this must be specified if #client_id is specified."""

    redirect_uri: t.Optional[str] = None
    """The GitHub App's OAuth redirect URI. This is required for OAuth2 authorization URL generation. Can be omitted
    if the app does not use OAuth2. This field is optional, but required for the web authorization flow with
    #oauth2_web_application_flow_url()."""

    v3_api_url: str = PUBLIC_GITHUB_V3_API_URL
    """GitHub API base URL. Defaults to the public GitHub API."""

    def __post_init__(self):
        self._jwt_supplier = JwtSupplier(self.app_id, self.private_key)
        self._lock = threading.Lock()
        self._installation_tokens: t.Dict[int, InstallationTokenSupplier] = {}

        if self.client_id is not None:
            if self.client_secret is None:
                raise ValueError("client_secret must be specified if client_id is specified.")
        if self.redirect_uri is not None:
            if self.client_id is None:
                raise ValueError("redirect_uri does not make sense without client_id.")

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

    @deprecated.deprecated(reason="Use .installation_token_supplier() instead.", version="0.8.0")
    def get_installation_token_supplier(self, installation_id: int) -> InstallationTokenSupplier:
        return self.installation_token_supplier(installation_id)

    def installation_token_supplier(self, installation_id: int) -> InstallationTokenSupplier:
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

    def oauth2_web_application_flow_url(self, state: t.Optional[str] = None) -> str:
        """
        Returns the URL for a user to begin the OAuth2 web authorization flow.

        Preconditions:
        - You must have provided a `client_id` when constructing the #GithubApp instance.

        Documentation: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app#using-the-web-application-flow-to-generate-a-user-access-token
        """

        if self.client_id is None:
            raise ValueError("client_id must be specified to generate OAuth2 authorization URL.")
        if self.client_secret is None:
            raise ValueError("client_secret must be specified to generate OAuth2 authorization URL.")
        if not self.redirect_uri:
            raise ValueError("redirect_uri must be specified to generate OAuth2 authorization URL.")

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
        }
        if state is not None:
            params["state"] = state

        url = self.v3_api_url.replace("api.", "").replace("/api/v3", "").rstrip("/")
        return f"{url}/login/oauth/authorize?" + urlencode(params)

    def oauth2_device_flow(self) -> "OAuth2DeviceCodeFlow":
        """
        Makes a request to GitHub to request a device code for the OAuth2 device flow.

        Prerequisites:

        - "Enable Device Flow" must be checked in your GitHub app's settings.
        - You must have provided a `client_id` when constructing the #GithubApp instance.

        Documentation: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app#using-the-device-flow-to-generate-a-user-access-token
        """

        params = {"client_id": self.client_id}
        url = self.v3_api_url.replace("api.", "").replace("/api/v3", "").rstrip("/")
        response = requests.post(f"{url}/login/device/code", params=params)
        response.raise_for_status()
        payload = {k: v[0] for k, v in parse_qs(response.text).items()}
        return OAuth2DeviceCodeFlow(
            device_code=payload["device_code"],
            user_code=payload["user_code"],
            verification_uri=payload["verification_uri"],
            expires_in=int(payload["expires_in"]),
            interval=int(payload["interval"]),
            app=self,
        )

    def oauth2_access_token(
        self, *, code: t.Optional[str] = None, device_code: t.Optional[str] = None
    ) -> t.Optional["OAuth2TokenInfo"]:
        """
        Makes a request to GitHub to exchange an OAuth2 code for an access token.

        Important: You must provide the correct `code` or `device_code` parameter, but not both.

        Documentation: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app#generating-a-user-access-token-when-a-user-installs-your-app

        Returns None if the token is not yet available (in the case of the device flow). Otherwise, returns a
        #TokenInfo object. If an error occurs, an #AccessTokenError is raised.
        """

        params = {"client_id": self.client_id, "client_secret": self.client_secret}
        if code is not None:
            params["code"] = code
        elif device_code is not None:
            params["device_code"] = device_code
            params["grant_type"] = "urn:ietf:params:oauth:grant-type:device_code"
        else:
            raise ValueError("You must provide either a code or a device_code.")

        url = self.v3_api_url.replace("api.", "").replace("/api/v3", "").rstrip("/")
        response = requests.post(f"{url}/login/oauth/access_token", params=params)
        payload = {k: v[0] for k, v in parse_qs(response.text).items()}

        if (error := payload.get("error")) == "authorization_pending":
            return None
        elif error is not None:
            return OAuth2TokenInfo(
                access_token=payload["access_token"],
                expires_in=int(payload["expires_in"]),
                scope=payload.get("scope"),
                token_type=payload["token_type"],
                refresh_token=payload.get("refresh_token"),
                refresh_token_expires_in=int(payload["refresh_token_expires_in"])
                if "refresh_token_expires_in" in payload
                else None,
            )
        else:
            raise AccessTokenError(error)  # type: ignore[arg-type]


@dataclasses.dataclass
class OAuth2DeviceCodeFlow:
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int

    # If you want to use this object to poll for the token, you need the GitHub App.
    app: t.Optional[GithubApp] = None

    def wait_for_token(
        self, aborted: t.Optional[threading.Event] = None, max_duration: t.Optional[float] = None
    ) -> "OAuth2TokenInfo":
        """
        Polls GitHub for the access token until it is available.

        If you pass in a threading.Event object, it will be used to abort the polling when the
        event is set. If *max_duration* is specified, the polling will stop after that many seconds and
        raise a #TimeoutError if the token is not available by then.
        """

        assert self.app is not None, "You must set the 'app' attribute to use this method."

        tstart = time.perf_counter()

        while True:
            if max_duration is not None and time.perf_counter() - tstart > max_duration:
                raise TimeoutError("Timed out waiting for token.")
            if aborted and aborted.is_set():
                raise RuntimeError("Polling for token was aborted.")
            try:
                if token := self.app.oauth2_access_token(device_code=self.device_code):
                    return token
            except AccessTokenError as e:
                if e.error == "slow_down":
                    time.sleep(5)
                else:
                    raise
            time.sleep(self.interval)


@dataclasses.dataclass
class OAuth2TokenInfo:
    access_token: str
    expires_in: int
    token_type: str
    scope: t.Optional[str] = None
    refresh_token: t.Optional[str] = None
    refresh_token_expires_in: t.Optional[int] = None

    @property
    def auth_header(self) -> str:
        return f"{self.token_type} {self.access_token}"


@dataclasses.dataclass
class AccessTokenError(Exception):
    error: t.Literal[
        "slow_down",
        "expired_token",
        "unsupported_grant_type",
        "incorrect_client_credentials",
        "incorrect_device_code",
        "access_denied",
        "device_flow_disabled",
    ]

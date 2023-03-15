from unittest.mock import patch

from github_bot_api.app import GithubApp
from github_bot_api.token import TokenInfo


def test_simple_app():
    """
    Regression test for PyGithub 1.58+ where such code failed on:

        AttributeError: module 'github.MainClass' has no attribute 'DEFAULT_TIMEOUT'
    """
    token = TokenInfo(1, "Bearer", "token")
    with patch("github_bot_api.token.InstallationTokenSupplier._new_token", return_value=token):
        app = GithubApp("UA/0.0.0", 42, "private_key")
        app.installation_client(1)

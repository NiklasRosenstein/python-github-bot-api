<h1 align="center">python-github-bot-api</h1>
<p align="center">
<a href="https://pypi.org/project/github-bot-api"><img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/github-bot-api"></a></p>

  [PyGithub]: https://pypi.org/project/PyGithub/

A thin Python library for creating GitHub bots and webhooks in Python with [PyGithub].

## Quickstart

```python
from github_bot_api import GithubApp
from pathlib import Path

app = GithubApp(
    user_agent='my-bot/0.0.0',
    app_id="12345",
    private_key=Path("app-private.key").read_text(),
)
```

Create a PyGithub client for the app itself:

```python
from github import Github
client: Github = app.app_client()
```

Create a PyGithub client for an app's installation scope:

```python
from github import Github
client: Github = app.installation_client(45678)
```

For more examples, check out the [documentation](https://niklasrosenstein.github.io/python-github-bot-api/).

<p align="center"><img src="https://i.imgur.com/5SiDsz8.png"></p>
<h1 align="center">python-github-bot-api</h1>
<p align="center">
<a href="https://pypi.org/project/github-bot-api"><img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/github-bot-api"></a></p>

  [PyGithub]: https://pypi.org/project/PyGithub/

A thin Python library for creating GitHub bots and webhooks in Python with [PyGithub].

```python
from github import Github
from github_bot_api import GithubApp
from pathlib import Path

app = GithubApp(
    user_agent='my-bot/0.0.0',
    app_id="67890",
    private_key=Path("app-private.key").read_text(),
)

client: Github = app.installation_client(12345)
```

For more examples, check out the [documentation](https://niklasrosenstein.github.io/python-github-bot-api/).

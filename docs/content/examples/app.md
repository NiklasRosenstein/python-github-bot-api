# Simple GitHub App

## Prerequisites

1. Create a GitHub App
2. Create a private key for your app

## Example

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

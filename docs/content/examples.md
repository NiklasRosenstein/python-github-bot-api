# Examples

## App

__Prerequisites__

1. Create a GitHub App
2. Create a private key for your app

__Example__

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

## Webhooks

__Prerequisites__

1. Smee channel (<https://smee.io>) or Ngrok (<https://ngrok.com>) for local development
2. Flask as a dependency (optional, dispatching events can be done manually)

__Example__

```python
from github_bot_api import Event, Webhook
from github_bot_api.flask import create_flask_app

def on_any_event(event: Event) -> bool:
  print(event)
  return True

webhook = Webhook(secret=None)
webhook.listen('*', on_any_event)

import os; os.environ['FLASK_ENV'] = 'development'
create_flask_app(__name__, webhook).run()
```

## App and Webhook

This is a small example that shows how to combine a webhook with a GitHub app.

```python
from github import Github
from github_bot_api import GithubApp, Webhook, Event

app = GithubApp(...)
webhook = Webhook()

@webhook.listen('pull_request')
def on_pull_request(event: Event) -> bool:
  client: Github = app.installation_client(event.payload['installation']['id'])
  repo = client.get_repo(event['repository']['full_name'])
  pr = repo.get_pull(event['pull_request']['number'])
  pr.create_issue_comment('Hello from my own bot!')
  return True
```

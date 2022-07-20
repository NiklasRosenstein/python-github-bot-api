# github-bot-api

API for creating GitHub bots and webhooks in Python.

> Note: If you want to make use of `GithubApp.app_client()` or `GithubApp.installation_client()`, you
> need to install `PyGithub`.

## Quickstart (Webhook)

1. Create a new Smee channel on https://smee.io
2. Install `smee-client` (e.g. `yarn global add smee-client`)
3. Run `smee -u <SMEE_CHANNEL_URL> -P /event-handler -p 5000`
4. Create a Python script with the below contents and run it

```python
from github_bot_api import Event, Webhook
from github_bot_api.flask import create_flask_app

def on_any_event(event: Event) -> bool:
  print(event)
  return True

webhook = Webhook(secret=None)
webhook.listen('*', on_any_event)

import os; os.environ['FLASK_ENV'] = 'development'
flask_app = create_flask_app(__name__, webhook)
flask_app.run()
```

## Quickstart (Application)

1. Create a GitHub App, including a private key
2. Set the `APP_ID` and `PRIVATE_KEY_FILE` environment variables
3. Run the following Python script

```python
import os
from github_bot_api import GithubApp

with open(os.environ['PRIVATE_KEY_FILE']) as fp:
  private_key = fp.read()

app = GithubApp(
  user_agent='my-bot/0.0.0',
  app_id=int(os.environ['APP_ID']),
  private_key=private_key)

print(app.app_client().get_app().owner)
```

## Combined Example

```python
# ...

app = GithubApp(...)
webhook = Webhook()

@webhook.listen('pull_request')
def on_pull_request(event: Event) -> bool:
  client = app.installation_client(event.payload['installation']['id'])
  repo = client.get_repo(event['repository']['full_name'])
  pr = repo.get_pull(event['pull_request']['number'])
  pr.create_issue_comment('Hello from my own bot!')
  return True

# ...
```

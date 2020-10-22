# github-bot-api

API for creating GitHub bots and webhooks in Python.

## Quickstart

```python
from github_bot_api import Event, Webhook
from github_bot_api.flask import create_flask_app

webhook = Webhook(secret=None)

@webhook.on('*')
def on_any_event(event: Event) -> bool:
  print(event)
  return True

create_flask_app(__name__, webhook).run(debug=True)
```

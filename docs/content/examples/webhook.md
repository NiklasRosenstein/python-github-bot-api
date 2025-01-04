# Simple Webhook

## Prerequisites

1. Smee channel (<https://smee.io>) or Ngrok (<https://ngrok.com>) for local development
2. Flask as a dependency (optional, dispatching events can be done manually)

## Example

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

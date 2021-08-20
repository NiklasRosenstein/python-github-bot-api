
"""
Flask binding for handling GitHub webhook events.

Note that you need to install the `flask` module separately.

# Example

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
"""

import flask
import typing as t
from .event import accept_event
from .webhook import Webhook


def create_event_handler(webhook: Webhook) -> t.Callable[[], t.Tuple[t.Text, int, t.Dict[str, str]]]:
  """
  Creates an event handler flask view that interprets the received HTTP request as a GitHub application
  event and dispatches it via #webhook.dispatch().
  """

  def event_handler():
    event = accept_event(
      t.cast(t.Mapping[str, str], flask.request.headers),
      flask.request.get_data(),
      webhook.secret)
    webhook.dispatch(event)
    return '', 202, {}
  return event_handler


def create_flask_app(
  name: str,
  webhook: Webhook,
  path: str = '/event-handler',
) -> flask.Flask:
  """
  Creates a new #flask.Flask application with a `POST` event handler under the given *path* (defaulting
  to `/event-handler`). This is a useful shorthand to attach your #Webhook to an HTTP server.
  """

  flask_app = flask.Flask(name)
  flask_app.route(path, methods=['POST'])(create_event_handler(webhook))
  return flask_app

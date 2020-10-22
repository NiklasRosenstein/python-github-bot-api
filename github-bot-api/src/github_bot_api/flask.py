
"""
Flask binding for handling GitHub webhook events.
"""

import flask
import typing as t
from .app import Webhook
from .event import accept_event


def create_event_handler(webhook: Webhook) -> t.Callable[[], t.Tuple[t.Text, int, t.Dict[str, str]]]:
  def event_handler():
    event = accept_event(
      flask.request.headers,
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
  flask_app = flask.Flask(name)
  flask_app.route(path, methods=['POST'])(create_event_handler(webhook))
  return flask_app

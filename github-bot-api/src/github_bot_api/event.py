
"""
Abstraction of a GitHub Webhook event.

Reference: https://docs.github.com/en/free-pro-team@latest/developers/webhooks-and-events/webhook-events-and-payloads
"""

import logging
import json
import typing as t
from dataclasses import dataclass
from .signature import check_signature
from .utils import get_mime_components

logger = logging.getLogger(__name__)


@dataclass
class Event:
  name: str
  delivery_id: str
  signature: t.Optional[str]
  user_agent: str
  payload: t.Dict[str, t.Any]


def accept_event(
  headers: t.Mapping[str, str],
  raw_body: bytes,
  webhook_secret: t.Optional[str] = None,
) -> Event:
  """
  Converts thee HTTP *headers* and the *raw_body* to an #Event object.
  """

  event_name = headers.get('X-GitHub-Event')
  delivery_id = headers.get('X-GitHub-Delivery')
  signature = headers.get('X-Hub-Signature-256')
  user_agent = headers.get('User-Agent')
  content_type = headers.get('Content-Type')

  if not event_name or not delivery_id or not user_agent or not content_type:
    raise InvalidRequest('missing required headers')
  if webhook_secret is not None and not signature:
    raise InvalidRequest('missing signature header')

  mime_type, parameters = get_mime_components(content_type)
  if mime_type != 'application/json':
    raise InvalidRequest(f'expected Content-Type: application/json, got {content_type}')
  encoding = dict(parameters).get('encoding', 'ascii')

  if webhook_secret is not None:
    assert signature is not None
    check_signature(signature, raw_body, webhook_secret.encode('ascii'))

  return Event(
    event_name,
    delivery_id,
    signature,
    user_agent,
    json.loads(raw_body.decode(encoding)),
  )


class InvalidRequest(Exception):
  pass

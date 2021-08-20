
"""
Abstraction of a GitHub Webhook event.

Reference: https://docs.github.com/en/free-pro-team@latest/developers/webhooks-and-events/webhook-events-and-payloads
"""

import logging
import json
import typing as t
from dataclasses import dataclass
from .signature import check_signature
from .utils.mime import get_mime_components

logger = logging.getLogger(__name__)


@dataclass
class Event:
  """
  Represents a GitHub webhook event.
  """

  #: The name of the event. Could be `pull_request`, for example.
  name: str

  #: The delivery ID of the event.
  delivery_id: str

  #: The signature of the event. Will only be set if a Webhook-secret is configured on the
  #: client side (e.g. in #Webhook.secret / if the *webhook_secret* parameter is passed to
  #: #accept_event()).
  signature: t.Optional[str]

  #: The user agent invoking the webhook.
  user_agent: str

  #: The event payload.
  payload: t.Dict[str, t.Any]


def accept_event(
  headers: t.Mapping[str, str],
  raw_body: bytes,
  webhook_secret: t.Optional[str] = None,
) -> Event:
  """
  Converts thee HTTP *headers* and the *raw_body* to an #Event object.

  # Arguments
  headers: The HTTP headers. Must have `X-Github-Event`, `X-Github-Delivery`, `User-Agent`, `Content-Type`.
    May have `X-Hub-Signature` or `X-Hub-Signature-256`.
  raw_body: The raw request body for the event. This is converted into a JSON payload.
  webhook_secret: If specified, the `X-Hub-Signature` or `X-Hub-Signature-256` headers are used to verify
    the signature of the payload. If not specified, the client does not validate the signature.
  """

  event_name = headers.get('X-GitHub-Event')
  delivery_id = headers.get('X-GitHub-Delivery')
  signature_1 = headers.get('X-Hub-Signature')
  signature_256 = headers.get('X-Hub-Signature-256')
  user_agent = headers.get('User-Agent')
  content_type = headers.get('Content-Type')

  if not event_name or not delivery_id or not user_agent or not content_type:
    raise InvalidRequest('missing required headers')
  if webhook_secret is not None and not (signature_1 or signature_256):
    raise InvalidRequest('webhook secret is configured but no signature header was received')

  mime_type, parameters = get_mime_components(content_type)
  if mime_type != 'application/json':
    raise InvalidRequest(f'expected Content-Type: application/json, got {content_type}')
  encoding = dict(parameters).get('encoding', 'UTF-8')

  if webhook_secret is not None:
    if signature_256:
      check_signature(signature_256, raw_body, webhook_secret.encode('ascii'), algo='sha256')
    elif signature_1:
      check_signature(signature_1, raw_body, webhook_secret.encode('ascii'), algo='sha1')
    else:
      raise RuntimeError

  return Event(
    event_name,
    delivery_id,
    signature_256 or signature_1,
    user_agent,
    json.loads(raw_body.decode(encoding)),
  )


class InvalidRequest(Exception):
  """
  Raised when an invalid request is passed to #accept_event().
  """

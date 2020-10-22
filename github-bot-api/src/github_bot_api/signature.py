
"""
Helper to check the signature of a GitHub event request.
"""

import hmac


def compute_signature(payload: bytes, secret: bytes) -> str:
  return 'sha256=' + hmac.new(secret, payload, 'sha256').hexdigest()


def check_signature(sig: str, payload: bytes, secret: bytes) -> None:
  """
  Compares the porivided signature *sig* with the computed signature of the *payload* and
  raises a #SignatureMismatchException if they do not match. This function uses constant-time
  string comparison to prevent timing analysis.
  """

  computed = compute_signature(payload, secret)
  if not hmac.compare_digest(sig, computed):
    raise SignatureMismatchException(sig, computed)


class SignatureMismatchException(Exception):

  _MSG = 'The provided signature does not match the computed signature of the payload.'

  def __init__(self, provided: str, computed: str) -> None:
    self.provided = provided
    self.computed = computed

  def __str__(self) -> str:
    return f'{self._MSG}\n  provided: {self.provided}\n  computed: {self.computed}'


"""
Helper to check the signature of a GitHub event request.
"""

import hmac


def compute_signature(payload: bytes, secret: bytes, algo: str = 'sha256') -> str:
  """
  Computes the HMAC signature of *payload* given the specified *secret* and the given hashing *algo*.

  # Parmeters
  payload: The payload for which the signature should be computed.
  secret: The secret string that is used in conjunction to generate the signature.
  algo: The hash algorithm to use, must be `sha1` or `sha256`.
  """

  if algo not in ('sha1', 'sha256'):
    raise ValueError(f'algo must be {{sha1, sha256}}, got {algo!r}')
  return f'{algo}=' + hmac.new(secret, payload, algo).hexdigest()


def check_signature(sig: str, payload: bytes, secret: bytes, algo: str = 'sha256') -> None:
  """
  Compares the porivided signature *sig* with the computed signature of the *payload* and
  raises a #SignatureMismatchException if they do not match. This function uses constant-time
  string comparison to prevent timing analysis.
  """

  computed = compute_signature(payload, secret, algo)
  if not hmac.compare_digest(sig, computed):
    raise SignatureMismatchException(sig, computed)


class SignatureMismatchException(Exception):
  """
  Raised if a signature can not be verified with #check_signatuer().
  """

  _MSG = 'The provided signature does not match the computed signature of the payload.'

  def __init__(self, provided: str, computed: str) -> None:
    self.provided = provided
    self.computed = computed

  def __str__(self) -> str:
    return f'{self._MSG}\n  provided: {self.provided}\n  computed: {self.computed}'

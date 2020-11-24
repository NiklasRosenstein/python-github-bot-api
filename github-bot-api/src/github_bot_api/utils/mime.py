
import typing as t


def get_mime_components(mime: str) -> t.Tuple[str, t.List[t.Tuple[str, str]]]:
  """
  Parses a mime type into it's components, returning the name of the mimetype and a list of
  it's `key=value` parameters.
  """

  # TODO(nrosenstein): Support escaped special characters in parameters
  #   (e.g. a ";" as part of a value).

  parts = mime.split(';')
  if not parts or not parts[0].strip():
    raise ValueError(f'bad mimetype: {mime!r}')

  parameters: t.List[t.Tuple[str, str]] = []
  for part in parts[1:]:
    if '=' not in part:
      parameters.append((part, ''))
    else:
      parameters.append(part.partition('=')[::2])

  return parts[0].strip(), parameters

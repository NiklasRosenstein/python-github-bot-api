# App and Webhook

This is a small example that shows how to combine a webhook with a GitHub app.

```python
from github import Github
from github_bot_api import GithubApp, Webhook, Event

app = GithubApp(...)
webhook = Webhook()

@webhook.listen('pull_request')
def on_pull_request(event: Event) -> bool:
  client: Github = app.installation_client(event.payload['installation']['id'])
  repo = client.get_repo(event['repository']['full_name'])
  pr = repo.get_pull(event['pull_request']['number'])
  pr.create_issue_comment('Hello from my own bot!')
  return True
```

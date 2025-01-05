# OAuth2

### Web Application Flow

This example demonstrates how to redirect a user through the GitHub OAuth2 flow.

```python
from github_bot_api import GithubApp
from pathlib import Path

app = GithubApp(
    user_agent='my-bot/0.0.0',
    app_id="12345",
    private_key=Path("app-private.key").read_text(),
    client_id="your-client-id",
    client_secret="your-client-secret",
    redirect_uri="http://localhost:8000/auth/callback"
)

# Redirect the user to this URL to start the OAuth2 flow.
authorize_url = app.oauth2_web_application_flow_url()
```

## Device Flow

```python
from github_bot_api import GithubApp
from pathlib import Path

app = GithubApp(
    user_agent='my-bot/0.0.0',
    app_id="12345",
    private_key=Path("app-private.key").read_text(),
    client_id="your-client-id",
    client_secret="your-client-secret"
)

flow = app.oauth2_device_flow()
print(f"Please authorize this device on {flow.verification_uri} and enter the code '{flow.user_code}'.")
token = flow.wait_for_token()
```

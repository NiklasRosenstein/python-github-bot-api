# github-bot-api

API for creating GitHub bots and webhooks in Python.

## Quickstart

1. Create a new Smee channel on https://smee.io
2. Install `smee-client` (e.g. `yarn global add smee-client`)
3. Run `smee -u <SMEE_CHANNEL_URL> -P /event-handler -p 5000`
4. Create a Python script with the below contents and run it

    ```python
    from github_bot_api import Event, Webhook
    from github_bot_api.flask import create_flask_app

    webhook = Webhook(secret=None)

    @webhook.on('*')
    def on_any_event(event: Event) -> bool:
      print(event)
      return True

    create_flask_app(__name__, webhook).run(debug=True)
    ```

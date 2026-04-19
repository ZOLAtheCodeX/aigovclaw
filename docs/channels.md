# Channel access for the AIGovClaw agent

AIGovClaw is a Hermes Agent runtime configuration. It inherits every channel adapter that Hermes Agent ships with `gateway/platforms/`. You do not need to build channel bridges; you configure them.

## Supported channels (built into Hermes Agent)

| Channel | Built-in adapter |
|---|---|
| Slack | `gateway/platforms/slack.py` |
| Discord | `gateway/platforms/discord.py` |
| Telegram | `gateway/platforms/telegram.py` + `gateway/platforms/telegram_network.py` |
| Signal | `gateway/platforms/signal.py` |
| Email | `gateway/platforms/email.py` |
| Matrix | `gateway/platforms/matrix.py` |
| Mattermost | `gateway/platforms/mattermost.py` |
| WhatsApp | `gateway/platforms/whatsapp.py` |
| SMS | `gateway/platforms/sms.py` |
| Webhook (custom endpoints) | `gateway/platforms/webhook.py` |
| Home Assistant | `gateway/platforms/homeassistant.py` |
| REST API server | `gateway/platforms/api_server.py` |
| Feishu / Lark | `gateway/platforms/feishu*.py` |
| WeCom (WeChat Work) | `gateway/platforms/wecom*.py` |
| Weixin (WeChat) | `gateway/platforms/weixin.py` |
| DingTalk | `gateway/platforms/dingtalk.py` |
| QQBot | `gateway/platforms/qqbot/` |
| BlueBubbles | `gateway/platforms/bluebubbles.py` |

## Configuration

Each channel has its own environment variables or config block in your Hermes Agent installation. Consult the upstream Hermes Agent documentation at [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) for channel-specific setup.

Example for Slack:

```bash
export HERMES_SLACK_BOT_TOKEN="xoxb-..."
export HERMES_SLACK_SIGNING_SECRET="..."
```

Example for Telegram:

```bash
export HERMES_TELEGRAM_BOT_TOKEN="..."
```

Example for Discord:

```bash
export HERMES_DISCORD_BOT_TOKEN="..."
```

## How AIGovClaw uses these channels

Once Hermes Agent is running with channels configured:

1. A practitioner sends a message to the agent via Slack / Discord / Telegram / email / etc.
2. Hermes Agent routes the message through its `gateway/delivery.py` into the agent reasoning loop.
3. The agent can invoke any AIGovOps plugin registered in the Hermes tool registry.
4. Plugin outputs stream back to the originating channel.
5. Action requests (file updates, MCP pushes, commits, etc.) route through the action-executor; ask-permission actions surface as channel messages the practitioner can approve with a reply.

## Command Centre chat as an additional channel

The Command Centre (`hub/v2/` running via `python3 -m hub.v2.cli serve`) has its own in-browser chat surface. Under the hood, the Command Centre chat is another channel adapter — it writes to the same approval queue and audit log as Slack / Telegram / Discord channels. Practitioners who prefer a single browser tab over separate chat apps can use the Command Centre; both paths reach the same agent.

## What we did NOT build

We did NOT build our own Slack/Discord/Telegram bots, webhook servers, or messaging infrastructure. All of that is upstream in Hermes Agent. AIGovClaw's role is strictly:

- Plugin catalogue registration (`tools/aigovops_tools.py`)
- Action-executor notification handler's stubbed channel arms — these currently raise `NotImplementedError` because the concrete delivery is Hermes Agent's responsibility. To wire them end-to-end, the notification handler should call the Hermes gateway's `deliver()` API rather than re-implementing delivery.

## Notification handler routing (now wired)

`aigovclaw/action_executor/handlers/notification.py` routes `slack`, `telegram`, `discord`, `email`, `desktop` channels through Hermes Agent's gateway. Two routes, tried in order:

1. **In-process** — if `hermes.gateway.delivery.deliver` is importable in the same Python environment (AIGovClaw running inside a Hermes Agent install), the handler calls it directly with `(channel, message, severity, source_plugin, request_id)`. Hermes then dispatches to the configured platform adapter (`gateway/platforms/slack.py`, etc.).

2. **Out-of-process** — if env var `HERMES_API_URL` is set (pointing at Hermes's `api_server` gateway platform, e.g. `http://127.0.0.1:8765`), the handler POSTs to `{HERMES_API_URL}/gateway/deliver` with a JSON body. Optional `HERMES_API_TOKEN` env var for Bearer auth. 5-second timeout.

3. **Unavailable** — if neither route is configured, the handler raises `NotImplementedError` with an actionable message pointing at docs/channels.md and suggesting the `local-file` or `stdout` fallback for local development.

No silent fallback on Hermes channels. The operator explicitly chooses Hermes (via install or HERMES_API_URL) or explicitly uses a local channel.

Dry-run mode reports which route would be used without attempting delivery (`result["delivery_route"]` in `{"hermes-inprocess", "hermes-http", "unavailable", "local"}`).

## Security note

Channel credentials (bot tokens, signing secrets) are held in Hermes Agent's config, never in AIGovClaw's code or evidence store. The action-executor's audit log records channel delivery attempts but never logs the content of credentials.

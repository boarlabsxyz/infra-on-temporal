"""Shared non-blocking Slack client for the approval activities.

The activities are `async def`, so they run on the worker's event loop. The sync
`WebClient` blocks that loop for every HTTP call, stalling workflow tasks,
heartbeats and the Telegram connection that share it. `AsyncWebClient` doesn't.
"""

import os

from dotenv import load_dotenv
from slack_sdk.http_retry.builtin_async_handlers import AsyncRateLimitErrorRetryHandler
from slack_sdk.web.async_client import AsyncWebClient

load_dotenv()

SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN") or SLACK_TOKEN

client = AsyncWebClient(token=SLACK_TOKEN, timeout=30)
# Wait out one `ratelimited` response (honouring Retry-After) before failing the attempt.
client.retry_handlers.append(AsyncRateLimitErrorRetryHandler(max_retry_count=1))

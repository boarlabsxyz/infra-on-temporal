from slack_sdk import WebClient
from typing import List
from temporalio import activity
import os

from dotenv import load_dotenv
load_dotenv()

client = WebClient(token=os.getenv("SLACK_TOKEN"))

@activity.defn
async def get_messages(channel_id: str) -> List[str]:
    res = client.conversations_history(
        channel=channel_id,
        limit=50
    )
    print(res)

    # extract timestamps
    timestamps = [msg["ts"] for msg in res["messages"]]

    # Slack returns newest first → reverse if needed
    return list(reversed(timestamps))

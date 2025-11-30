from slack_sdk import WebClient
from temporalio import activity
import os

from dotenv import load_dotenv
load_dotenv()

client = WebClient(token=os.getenv("SLACK_TOKEN"))

@activity.defn
async def check_reactions(info):
    ts, channel_id = info[0], info[1]

    msg_res = client.conversations_history(
        channel=channel_id,
        latest=ts,
        oldest=ts,
        inclusive=True,
        limit=1,
    )

    if not msg_res["messages"]:
        return {"ts": ts, "error": "message_not_found"}

    react_res = client.reactions_get(
        channel=channel_id,
        timestamp=ts,
    )

    msg_with_reactions = react_res.get("message", {})

    return {
        "ts": ts,
        "text": msg_with_reactions.get("text", ""),
        "user": msg_with_reactions.get("user", None),
        "reactions": msg_with_reactions.get("reactions", []),
    }

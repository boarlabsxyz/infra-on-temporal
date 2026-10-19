from temporalio import activity
import base64

import aiohttp
from slack_sdk.errors import SlackApiError

from activities.image_store import put as image_store_put
from activities.slack_approval_activities.slack_client import SLACK_BOT_TOKEN, client

APPROVE_REACTION = "white_check_mark"


@activity.defn
async def check_reactions(info):
    """Fetch reactions and image data for a Slack message by timestamp."""
    ts, channel_id = info[0], info[1]

    try:
        react_res = await client.reactions_get(
            channel=channel_id,
            timestamp=ts,
            full=True,
        )
    except SlackApiError as e:
        if e.response.get("error") == "message_not_found":
            return {"ts": ts, "error": "message_not_found"}
        activity.logger.error(f"Slack API error checking reactions on {ts}: {e.response.get('error')}")
        raise

    msg_with_reactions = dict(react_res.get("message", {}))

    # conversations.history is the scarce call (Slack rate-limits it hard), so only
    # use it to fill in files on an approved message that reactions.get left out.
    is_approved = any(
        r.get("name") == APPROVE_REACTION for r in msg_with_reactions.get("reactions", [])
    )
    if is_approved and "files" not in msg_with_reactions:
        msg_res = await client.conversations_history(
            channel=channel_id,
            latest=ts,
            oldest=ts,
            inclusive=True,
            limit=1,
        )
        if msg_res["messages"] and "files" in msg_res["messages"][0]:
            msg_with_reactions["files"] = msg_res["messages"][0]["files"]

    # Extract text - handle both plain text and Block Kit messages
    message_text = msg_with_reactions.get("text", "")

    # If text is empty or looks like a fallback, try to extract from blocks
    if not message_text or message_text.startswith("New message from"):
        blocks = msg_with_reactions.get("blocks", [])
        for block in blocks:
            if block.get("type") == "section":
                text_obj = block.get("text", {})
                if text_obj.get("type") in ["mrkdwn", "plain_text"]:
                    extracted_text = text_obj.get("text", "")
                    if extracted_text and not extracted_text.startswith("New message from"):
                        message_text = extracted_text
                        break

    # Check for files/images in the message
    files = msg_with_reactions.get("files", [])
    has_image = False
    image_data = None

    if files:
        for file in files:
            # Check if it's an image
            if file.get("mimetype", "").startswith("image/"):
                has_image = True
                image_url = file.get("url_private_download") or file.get("url_private")

                # Download the image if we have a URL
                if image_url:
                    try:
                        async with aiohttp.ClientSession(
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as session:
                            async with session.get(
                                image_url,
                                headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
                            ) as response:
                                response.raise_for_status()
                                image_bytes = await response.read()
                        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                        image_data = image_store_put(image_base64)
                        activity.logger.info(f"Downloaded image from message {ts}")
                    except Exception as e:
                        activity.logger.error(f"Failed to download image: {e}")
                break  # Only handle the first image

    return {
        "ts": ts,
        "text": message_text,
        "user": msg_with_reactions.get("user", None),
        "reactions": msg_with_reactions.get("reactions", []),
        "has_image": has_image,
        "image_data": image_data,
    }

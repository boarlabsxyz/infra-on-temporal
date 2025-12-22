from slack_sdk import WebClient
from temporalio import activity
import os
import aiohttp
import base64

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
    image_url = None
    
    if files:
        for file in files:
            # Check if it's an image
            if file.get("mimetype", "").startswith("image/"):
                has_image = True
                image_url = file.get("url_private")
                
                # Download the image if we have a URL
                if image_url:
                    try:
                        async with aiohttp.ClientSession() as session:
                            headers = {"Authorization": f"Bearer {os.getenv('SLACK_TOKEN')}"}
                            async with session.get(image_url, headers=headers) as resp:
                                if resp.status == 200:
                                    image_bytes = await resp.read()
                                    image_data = base64.b64encode(image_bytes).decode('utf-8')
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

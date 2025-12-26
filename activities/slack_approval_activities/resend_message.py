from temporalio import activity
import os
import base64

from dotenv import load_dotenv
load_dotenv()

SLACK_WEBHOOK_URL2 = os.getenv("SLACK_WEBHOOK_URL_NEWS")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID_NEWS = os.getenv("SLACK_CHANNEL_ID_NEWS")

@activity.defn
async def resend_message(info):
    import aiohttp

    # Handle both old format (string) and new format (dict with image data)
    if isinstance(info, str):
        message = info
        has_image = False
        image_data = None
    else:
        message = info.get("text", "")
        has_image = info.get("has_image", False)
        image_data = info.get("image_data")

    # If there's an image and we have bot token and channel ID, use files.upload API
    if has_image and image_data and SLACK_BOT_TOKEN and SLACK_CHANNEL_ID_NEWS:
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            
            # Format the message nicely
            formatted_message = f"✅ *Approved Message*\n\n{message}"
            
            # Use Slack Web API to upload the file
            form_data = aiohttp.FormData()
            form_data.add_field('channels', SLACK_CHANNEL_ID_NEWS)
            form_data.add_field('initial_comment', formatted_message)
            form_data.add_field('file', 
                              image_bytes,
                              filename='approved_image.jpg',
                              content_type='image/jpeg')
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://slack.com/api/files.upload',
                    data=form_data,
                    headers={'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
                ) as resp:
                    result = await resp.json()
                    if not result.get('ok'):
                        raise RuntimeError(f"File upload failed: {result.get('error')}")
                    
                    activity.logger.info(f"Successfully uploaded approved message with image to Slack")
                    return result
        except Exception as e:
            activity.logger.error(f"Failed to upload image, falling back to text only: {e}")
            # Fall back to webhook if image upload fails

    # Standard webhook for text-only messages or fallback
    # Using blocks for better formatting
    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            },
        ],
        "text": f"New message: {message[:50]}..."  # Fallback text for notifications
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            SLACK_WEBHOOK_URL2,
            json=payload,
            headers={"Content-type": "application/json"}
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"Webhook request failed: {resp.status}, {body}")
            return await resp.text()

from temporalio import activity
import os
import re
import base64

from dotenv import load_dotenv
load_dotenv()

SLACK_WEBHOOK_URL2 = os.getenv("SLACK_WEBHOOK_URL_NEWS")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID_NEWS = os.getenv("SLACK_CHANNEL_ID_NEWS")


def extract_content_only(text: str) -> str:
    """Extract only the message content, removing metadata lines."""
    if not text:
        return text

    lines = text.split('\n')
    content_lines = []
    skip_next_empty = False

    for line in lines:
        stripped = line.strip()

        # Skip "Telegram Channel:" line (with or without emoji, any channel name)
        if re.search(r'Telegram Channel:', stripped, re.IGNORECASE):
            skip_next_empty = True
            continue
        # Skip "View original" link line (including Slack link format <url|text>)
        if re.search(r'View original', stripped, re.IGNORECASE):
            skip_next_empty = True
            continue
        # Skip "Approved Message" line
        if re.search(r'Approved Message', stripped, re.IGNORECASE):
            skip_next_empty = True
            continue
        # Skip empty lines right after metadata
        if skip_next_empty and stripped == '':
            skip_next_empty = False
            continue
        skip_next_empty = False
        content_lines.append(line)

    # Remove leading/trailing empty lines
    while content_lines and content_lines[0].strip() == '':
        content_lines.pop(0)
    while content_lines and content_lines[-1].strip() == '':
        content_lines.pop()

    return '\n'.join(content_lines)


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

    # Extract only the content, removing metadata lines
    message = extract_content_only(message)

    # If there's an image and we have bot token and channel ID, use Slack files API
    if has_image and image_data and SLACK_BOT_TOKEN and SLACK_CHANNEL_ID_NEWS:
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)

            async with aiohttp.ClientSession() as session:
                # Step 1: Get upload URL from Slack
                upload_url_resp = await session.get(
                    'https://slack.com/api/files.getUploadURLExternal',
                    params={
                        'filename': 'image.jpg',
                        'length': len(image_bytes)
                    },
                    headers={'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
                )
                upload_url_result = await upload_url_resp.json()

                if not upload_url_result.get('ok'):
                    raise RuntimeError(f"Failed to get upload URL: {upload_url_result.get('error')}")

                upload_url = upload_url_result['upload_url']
                file_id = upload_url_result['file_id']

                activity.logger.info(f"Got upload URL for file_id: {file_id}")

                # Step 2: Upload the file to the provided URL
                async with session.post(
                    upload_url,
                    data=image_bytes,
                    headers={'Content-Type': 'application/octet-stream'}
                ) as upload_resp:
                    if upload_resp.status != 200:
                        raise RuntimeError(f"File upload failed with status: {upload_resp.status}")

                activity.logger.info(f"Uploaded file to Slack storage")

                # Step 3: Complete the upload and share to channel
                complete_resp = await session.post(
                    'https://slack.com/api/files.completeUploadExternal',
                    json={
                        'files': [{'id': file_id, 'title': 'Image'}],
                        'channel_id': SLACK_CHANNEL_ID_NEWS,
                        'initial_comment': message
                    },
                    headers={
                        'Authorization': f'Bearer {SLACK_BOT_TOKEN}',
                        'Content-Type': 'application/json'
                    }
                )
                complete_result = await complete_resp.json()

                if not complete_result.get('ok'):
                    raise RuntimeError(f"Failed to complete upload: {complete_result.get('error')}")

                activity.logger.info(f"Successfully uploaded message with image to Slack")
                return complete_result
        except Exception as e:
            activity.logger.error(f"Failed to upload image, falling back to text only: {e}")
            # Fall back to webhook if image upload fails

    # Send text-only via webhook (fallback or no image)
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

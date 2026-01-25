from temporalio import activity
import asyncio
import os
import re
import base64
from dotenv import load_dotenv
from .claude_translate import format_telegram_to_slack
load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN") or os.getenv("SLACK_TOKEN")  # Support both variable names
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")


def escape_slack_mrkdwn(text: str, max_length: int = 2900) -> str:
    """Escape special characters for Slack mrkdwn and truncate if needed."""
    if not text:
        return text

    # Extract existing Slack-style links to protect them during escaping
    links = []
    def save_link(match):
        links.append(match.group(0))
        return f'\x00LINK{len(links)-1}\x00'

    text = re.sub(r'<https?://[^|>]+\|[^>]+>', save_link, text)
    text = re.sub(r'<https?://[^>]+>', save_link, text)

    # Escape special characters for Slack mrkdwn
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')

    # Restore links
    for i, link in enumerate(links):
        text = text.replace(f'\x00LINK{i}\x00', link)

    # Truncate to stay under Slack's 3000 char limit for section blocks
    if len(text) > max_length:
        text = text[:max_length] + '... [truncated]'

    return text


@activity.defn
async def send_message_to_slack(info):
    import aiohttp

    message, channel, has_image, image_data, msg_id, original_text = info[0], info[1], info[2], info[3], info[4], info[5]

    # Escape message and original_text for Slack mrkdwn
    message = escape_slack_mrkdwn(message)
    original_text = format_telegram_to_slack(original_text) if original_text else original_text
    
    # Create Telegram link (remove @ if present)
    channel_clean = channel.lstrip('@')
    telegram_link = f"https://t.me/{channel_clean}/{msg_id}"

    # If there's an image and we have bot token and channel ID, use new Slack files API
    if has_image and image_data and SLACK_BOT_TOKEN and SLACK_CHANNEL_ID:
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)

            # Format the message nicely with link
            formatted_message = f"📱 *Telegram Channel:* `{channel}`\n<{telegram_link}|View original on Telegram>\n\n{message}"

            async with aiohttp.ClientSession() as session:
                # Step 1: Get upload URL from Slack
                upload_url_resp = await session.get(
                    'https://slack.com/api/files.getUploadURLExternal',
                    params={
                        'filename': 'telegram_image.jpg',
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
                        'files': [{'id': file_id, 'title': 'Telegram Image'}],
                        'channel_id': SLACK_CHANNEL_ID,
                        'initial_comment': formatted_message
                    },
                    headers={
                        'Authorization': f'Bearer {SLACK_BOT_TOKEN}',
                        'Content-Type': 'application/json'
                    }
                )
                complete_result = await complete_resp.json()

                if not complete_result.get('ok'):
                    raise RuntimeError(f"Failed to complete upload: {complete_result.get('error')}")

                activity.logger.info(f"Successfully uploaded image to Slack")
                activity.logger.info(f"Complete upload response: {complete_result}")

                # Post original message in thread for comparison
                activity.logger.info(f"original_text is: {bool(original_text)}, length: {len(original_text) if original_text else 0}")
                if original_text:
                    uploaded_file_id = complete_result['files'][0].get('id')
                    activity.logger.info(f"Uploaded file_id: {uploaded_file_id}")

                    # Use files.info API with retries to get message_ts from shares
                    message_ts = None
                    for attempt in range(5):
                        await asyncio.sleep(1)
                        async with session.get(
                            'https://slack.com/api/files.info',
                            params={'file': uploaded_file_id},
                            headers={'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
                        ) as file_info_resp:
                            file_info_result = await file_info_resp.json()
                            activity.logger.info(f"files.info attempt {attempt + 1}: {file_info_result}")

                            if file_info_result.get('ok') and file_info_result.get('file'):
                                shares = file_info_result['file'].get('shares', {})
                                activity.logger.info(f"Shares: {shares}")

                                # Try to find message_ts in public or private shares
                                for share_type in ['public', 'private']:
                                    if share_type in shares:
                                        for channel_id, share_list in shares[share_type].items():
                                            if share_list and share_list[0].get('ts'):
                                                message_ts = share_list[0]['ts']
                                                activity.logger.info(f"Found ts {message_ts} in {share_type}/{channel_id}")
                                                break
                                    if message_ts:
                                        break

                            if message_ts:
                                break

                        activity.logger.info(f"Attempt {attempt + 1}: shares not ready yet")

                    if not message_ts:
                        activity.logger.warning(f"Could not get message_ts from files.info after 5 attempts")

                    if message_ts:
                        activity.logger.info(f"Posting thread reply with message_ts: {message_ts}")
                        thread_payload = {
                            "channel": SLACK_CHANNEL_ID,
                            "thread_ts": message_ts,
                            "text": f"📝 *Original message:*\n\n{original_text}",
                            "blocks": [
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"📝 *Original message:*\n\n{original_text}"
                                    }
                                }
                            ]
                        }

                        async with session.post(
                            'https://slack.com/api/chat.postMessage',
                            json=thread_payload,
                            headers={'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
                        ) as thread_resp:
                            thread_result = await thread_resp.json()
                            if not thread_result.get('ok'):
                                activity.logger.error(f"Thread post failed: {thread_result.get('error')}")
                            else:
                                activity.logger.info(f"Successfully posted original message in thread")

                return complete_result
        except Exception as e:
            activity.logger.error(f"Failed to upload image, falling back to text only: {e}")
            # Fall back to webhook if image upload fails

    # Use Slack API if bot token is available, for threaded replies and links
    if SLACK_BOT_TOKEN and SLACK_CHANNEL_ID:
        try:
            # Post main message with link
            payload = {
                "channel": SLACK_CHANNEL_ID,
                "unfurl_links": False,  # Disable automatic link previews
                "unfurl_media": False,  # Disable automatic media previews
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"📱 {channel}",
                            "emoji": True
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"<{telegram_link}|View original message on Telegram>"
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": message
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"🔄 _Translated from Telegram_"
                            }
                        ]
                    }
                ],
                "text": f"New message from {channel}"
            }
            
            async with aiohttp.ClientSession() as session:
                # Post main message
                async with session.post(
                    'https://slack.com/api/chat.postMessage',
                    json=payload,
                    headers={'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
                ) as resp:
                    result = await resp.json()
                    if not result.get('ok'):
                        raise RuntimeError(f"Message post failed: {result.get('error')}")
                    
                    message_ts = result.get('ts')
                    activity.logger.info(f"Successfully posted message to Slack")
                    
                    # Post original message in thread for comparison
                    if original_text and message_ts:
                        thread_payload = {
                            "channel": SLACK_CHANNEL_ID,
                            "thread_ts": message_ts,
                            "text": f"📝 *Original message:*\n\n{original_text}",
                            "blocks": [
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"📝 *Original message:*\n\n{original_text}"
                                    }
                                }
                            ]
                        }
                        
                        async with session.post(
                            'https://slack.com/api/chat.postMessage',
                            json=thread_payload,
                            headers={'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
                        ) as thread_resp:
                            thread_result = await thread_resp.json()
                            if not thread_result.get('ok'):
                                activity.logger.error(f"Thread post failed: {thread_result.get('error')}")
                            else:
                                activity.logger.info(f"Successfully posted original message in thread")
                    
                    return result
        except Exception as e:
            activity.logger.error(f"Failed to use Slack API, falling back to webhook: {e}")
            # Fall through to webhook fallback

    # Fallback to webhook if Slack API is not available or fails
    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📱 {channel}",
                    "emoji": True
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"<{telegram_link}|View original message on Telegram>"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"🔄 _Translated from Telegram_"
                    }
                ]
            }
        ],
        "text": f"New message from {channel}"  # Fallback text for notifications
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            SLACK_WEBHOOK_URL,
            json=payload,
            headers={"Content-type": "application/json"}
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"Webhook request failed: {resp.status}, {body}")
            return await resp.text()

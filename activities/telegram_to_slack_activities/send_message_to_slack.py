from temporalio import activity
import os
import base64
from dotenv import load_dotenv
load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN") or os.getenv("SLACK_TOKEN")  # Support both variable names
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

@activity.defn
async def send_message_to_slack(info):
    import aiohttp

    message, channel, has_image, image_data, msg_id, original_text = info[0], info[1], info[2], info[3], info[4], info[5]
    
    # Create Telegram link (remove @ if present)
    channel_clean = channel.lstrip('@')
    telegram_link = f"https://t.me/{channel_clean}/{msg_id}"

    # If there's an image and we have bot token and channel ID, use files.upload API
    if has_image and image_data and SLACK_BOT_TOKEN and SLACK_CHANNEL_ID:
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            
            # Format the message nicely with link
            formatted_message = f"📱 *Telegram Channel:* `{channel}`\n<{telegram_link}|View original on Telegram>\n\n{message}"
            
            # Use Slack Web API to upload the file
            form_data = aiohttp.FormData()
            form_data.add_field('channels', SLACK_CHANNEL_ID)
            form_data.add_field('initial_comment', formatted_message)
            form_data.add_field('file', 
                              image_bytes,
                              filename='telegram_image.jpg',
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
                    
                    activity.logger.info(f"Successfully uploaded image to Slack")
                    
                    # Post original message in thread for comparison
                    if original_text and result.get('file', {}).get('shares'):
                        # Get the message timestamp from the file share
                        shares = result['file']['shares']
                        if 'private' in shares and SLACK_CHANNEL_ID in shares['private']:
                            message_ts = shares['private'][SLACK_CHANNEL_ID][0]['ts']
                        elif 'public' in shares and SLACK_CHANNEL_ID in shares['public']:
                            message_ts = shares['public'][SLACK_CHANNEL_ID][0]['ts']
                        else:
                            message_ts = None
                        
                        if message_ts:
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
            activity.logger.error(f"Failed to upload image, falling back to text only: {e}")
            # Fall back to webhook if image upload fails

    # Use Slack API if bot token is available, for threaded replies and links
    if SLACK_BOT_TOKEN and SLACK_CHANNEL_ID:
        try:
            # Post main message with link
            payload = {
                "channel": SLACK_CHANNEL_ID,
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

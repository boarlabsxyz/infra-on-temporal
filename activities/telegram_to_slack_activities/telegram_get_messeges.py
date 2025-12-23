from telethon import TelegramClient
from telethon.errors import RPCError
from temporalio import activity
from typing import List, Dict, Any
import os
import base64
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")


@activity.defn
async def fetch_last_message(channel_username: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetches the last few messages from a Telegram channel and returns them
    in chronological order (oldest to newest).
    
    Args:
        channel_username: The Telegram channel username or ID to fetch messages from
        limit: Maximum number of messages to fetch (default: 10)
    
    Returns:
        List of message dictionaries ordered from oldest to newest
    """
    client = None
    
    try:
        client = TelegramClient("tg_session", API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            activity.logger.error("Telegram client is not authorized")
            raise Exception("Telegram client is not authorized")

        entity = await client.get_entity(channel_username)
        activity.logger.info(f"Fetching last {limit} messages from {channel_username}")
        
        messages = []
        
        # iter_messages returns messages in reverse chronological order (newest first)
        async for msg in client.iter_messages(entity, limit=limit):
            message_data = {
                "id": msg.id,
                "date": msg.date.isoformat(),
                "text": msg.text or "",
                "has_image": False,
                "image_data": None,
            }
            
            # Check if the message has a photo
            if msg.photo:
                try:
                    # Download the photo to a BytesIO buffer
                    photo_bytes = BytesIO()
                    await client.download_media(msg.photo, photo_bytes)
                    photo_bytes.seek(0)
                    
                    # Convert to base64 for transmission
                    image_base64 = base64.b64encode(photo_bytes.read()).decode('utf-8')
                    
                    message_data["has_image"] = True
                    message_data["image_data"] = image_base64
                    
                    activity.logger.info(f"Downloaded image from message {msg.id}")
                except Exception as e:
                    activity.logger.error(f"Failed to download image from message {msg.id}: {e}")
            
            messages.append(message_data)
        
        if not messages:
            activity.logger.warning(f"No messages found in channel {channel_username}")
            return []
        
        # Reverse to get chronological order (oldest to newest)
        # This ensures messages are processed from old to new
        messages_oldest_first = list(reversed(messages))
        
        activity.logger.info(f"Returning {len(messages_oldest_first)} messages in chronological order")
        return messages_oldest_first
        
    except RPCError as e:
        activity.logger.error(f"Telegram API error: {str(e)}")
        raise
    except Exception as e:
        activity.logger.error(f"Unexpected error fetching Telegram messages: {str(e)}")
        raise
    finally:
        if client:
            await client.disconnect()

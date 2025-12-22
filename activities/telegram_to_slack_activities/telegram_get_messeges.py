from telethon import TelegramClient
from temporalio import activity
import os
import base64
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")


@activity.defn
async def fetch_last_message(channel_username):

    client = TelegramClient("tg_session", API_ID, API_HASH)
    await client.connect()

    entity = await client.get_entity(channel_username)

    async for msg in client.iter_messages(entity, limit=1):
        last_msg = {
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
                
                last_msg["has_image"] = True
                last_msg["image_data"] = image_base64
                
                activity.logger.info(f"Downloaded image from message {msg.id}")
            except Exception as e:
                activity.logger.error(f"Failed to download image: {e}")
        
        break

    await client.disconnect()
    return last_msg

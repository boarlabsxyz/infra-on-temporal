from telethon import TelegramClient
from temporalio import activity
import os
from dotenv import load_dotenv
load_dotenv()

API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")

@activity.defn
async def fetch_channel_messages(params: list):
    channel_username, last_message_id = params

    async with TelegramClient("tg_session", API_ID, API_HASH) as client:
        entity = await client.get_entity(channel_username)

        new_messages = []

        async for msg in client.iter_messages(entity, limit=5):
            if msg.id <= last_message_id:
                break

            new_messages.append({
                "id": msg.id,
                "date": msg.date.isoformat(),
                "text": msg.text or "",
            })

        # возвращаем сообщения в хронологическом порядке
        new_messages.reverse()

        return new_messages

from telethon import TelegramClient
from temporalio import activity
import os
from dotenv import load_dotenv
load_dotenv()

API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")


@activity.defn
async def fetch_channel_messages(parametrs: list):
    channel_username = parametrs[0]
    last_message_id = parametrs[1]


    client = TelegramClient("tg_session", API_ID, API_HASH)
    await client.connect()

    entity = await client.get_entity(channel_username)
    messages = []

    async for msg in client.iter_messages(entity, limit=1):
        if msg.id <= last_message_id:
            break
        messages.append({
            "id": msg.id,
            "date": msg.date.isoformat(),
            "text": msg.text or "",
        })

    await client.disconnect()
    return messages
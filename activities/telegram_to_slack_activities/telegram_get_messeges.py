from telethon import TelegramClient
from temporalio import activity
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")


@activity.defn
async def fetch_last_message(parameters: list):
    channel_username = parameters[0]

    client = TelegramClient("tg_session", API_ID, API_HASH)
    await client.connect()

    entity = await client.get_entity(channel_username)

    async for msg in client.iter_messages(entity, limit=1):
        last_msg = {
            "id": msg.id,
            "date": msg.date.isoformat(),
            "text": msg.text or "",
        }
        break

    await client.disconnect()
    return last_msg


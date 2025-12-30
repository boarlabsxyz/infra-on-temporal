# save_session.py
import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

api_id = int(os.environ["TG_API_ID"])
api_hash = os.environ["TG_API_HASH"]

async def main():
    async with TelegramClient(
        StringSession(),
        api_id,
        api_hash,
    ) as client:
        print("\n✅ Your session string:\n")
        print(client.session.save())

if __name__ == "__main__":
    asyncio.run(main())

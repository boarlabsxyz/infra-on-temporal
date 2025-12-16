# save_session.py
from telethon import TelegramClient
import os
from dotenv import load_dotenv
load_dotenv()

api_id = os.getenv("TG_API_ID")
api_hash = os.getenv("TG_API_HASH")

client = TelegramClient("tg_session", api_id, api_hash)

async def main():
    await client.start()
    print("Session saved!")

client.loop.run_until_complete(main())

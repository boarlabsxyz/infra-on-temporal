import asyncio
import base64
import os
from io import BytesIO
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import RPCError
from telethon.sessions import StringSession
from temporalio import activity

from activities.image_store import put as image_store_put

load_dotenv()

API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
TG_SESSION_STRING = os.getenv("TG_SESSION_SRING", "")


_client: Optional[TelegramClient] = None
_client_lock = asyncio.Lock()


async def get_client() -> TelegramClient:
    """Return a process-wide TelegramClient, creating and connecting it on first use.

    Reusing one client across activities keeps auth keys and exported senders cached,
    which avoids the `Step 3 invalid new nonce hash` race that happens when many
    activities each spin up their own MTProto handshake to the media DC.
    """
    global _client
    if _client is not None and _client.is_connected():
        return _client

    async with _client_lock:
        if _client is not None and _client.is_connected():
            return _client

        client = TelegramClient(
            StringSession(TG_SESSION_STRING),
            API_ID,
            API_HASH,
            connection_retries=-1,
            retry_delay=2,
            auto_reconnect=True,
            request_retries=5,
            flood_sleep_threshold=60,
        )
        await client.connect()

        if not await client.is_user_authorized():
            await client.disconnect()
            raise RuntimeError("Telegram client is not authorized")

        _client = client
        return _client


async def shutdown_client() -> None:
    """Disconnect the shared client, awaiting background tasks so they don't leak."""
    global _client
    if _client is None:
        return
    try:
        await _client.disconnect()
    finally:
        _client = None


@activity.defn
async def fetch_last_message(channel_username: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch the last few messages from a Telegram channel, oldest to newest."""
    try:
        client = await get_client()

        entity = await client.get_entity(channel_username)
        activity.logger.info(f"Fetching last {limit} messages from {channel_username}")

        def heartbeat_progress(received: int, total: int) -> None:
            try:
                activity.heartbeat({"received": received, "total": total})
            except Exception:
                pass

        messages: List[Dict[str, Any]] = []

        async for msg in client.iter_messages(entity, limit=limit):
            activity.heartbeat({"phase": "iter", "msg_id": msg.id})

            message_data: Dict[str, Any] = {
                "id": msg.id,
                "date": msg.date.isoformat(),
                "text": msg.text or "",
                "has_image": False,
                "image_data": None,
            }

            if msg.photo:
                try:
                    photo_bytes = BytesIO()
                    await client.download_media(
                        msg.photo,
                        photo_bytes,
                        progress_callback=heartbeat_progress,
                    )
                    photo_bytes.seek(0)

                    image_base64 = base64.b64encode(photo_bytes.read()).decode("utf-8")

                    message_data["has_image"] = True
                    message_data["image_data"] = image_store_put(image_base64)

                    activity.logger.info(f"Downloaded image from message {msg.id}")
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    activity.logger.error(
                        f"Failed to download image from message {msg.id}: {e}"
                    )

            messages.append(message_data)

        if not messages:
            activity.logger.warning(f"No messages found in channel {channel_username}")
            return []

        messages_oldest_first = list(reversed(messages))

        activity.logger.info(
            f"Returning {len(messages_oldest_first)} messages in chronological order"
        )
        return messages_oldest_first

    except RPCError as e:
        activity.logger.error(f"Telegram API error: {str(e)}")
        raise
    except asyncio.CancelledError:
        activity.logger.warning(
            f"fetch_last_message for {channel_username} was cancelled"
        )
        raise
    except Exception as e:
        activity.logger.error(f"Unexpected error fetching Telegram messages: {str(e)}")
        raise

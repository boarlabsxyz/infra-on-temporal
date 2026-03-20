"""
Manual test script to verify Slack image download works.
Run with: python3 tests/test_image_download.py
"""
import os
import asyncio
import aiohttp
from dotenv import load_dotenv
from slack_sdk import WebClient

load_dotenv()

SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN") or SLACK_TOKEN
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")


async def test_url(session, url, name, token):
    """Test downloading an image from a given Slack URL and report success."""
    print(f"\n--- Testing {name} ---")
    print(f"URL: {url}")
    headers = {"Authorization": f"Bearer {token}"}
    async with session.get(url, headers=headers) as resp:
        print(f"Status: {resp.status}")
        print(f"Content-Type: {resp.headers.get('Content-Type')}")
        data = await resp.read()
        is_html = data[:15].lower().startswith(b'<!doctype html') or data[:5].lower() == b'<html'
        print(f"Got HTML: {is_html}")
        print(f"Data size: {len(data)} bytes")
        return not is_html


async def test_image_download():
    """Find a recent Slack message with an image and test downloading it via various URLs."""
    print(f"SLACK_TOKEN set: {bool(SLACK_TOKEN)}")
    print(f"SLACK_BOT_TOKEN set: {bool(SLACK_BOT_TOKEN)}")
    print()

    client = WebClient(token=SLACK_TOKEN)

    # Get recent messages
    result = client.conversations_history(
        channel=SLACK_CHANNEL_ID,
        limit=20
    )

    # Find a message with an image
    for msg in result["messages"]:
        files = msg.get("files", [])
        for file in files:
            if file.get("mimetype", "").startswith("image/"):
                print(f"Found image in message {msg['ts']}")
                print(f"Mimetype: {file.get('mimetype')}")

                async with aiohttp.ClientSession() as session:
                    # Test different URLs
                    urls_to_test = [
                        ("url_private_download", file.get("url_private_download")),
                        ("url_private", file.get("url_private")),
                        ("thumb_720", file.get("thumb_720")),
                        ("thumb_480", file.get("thumb_480")),
                        ("thumb_360", file.get("thumb_360")),
                        ("permalink_public", file.get("permalink_public")),
                    ]

                    for name, url in urls_to_test:
                        if url:
                            success = await test_url(session, url, name, SLACK_BOT_TOKEN)
                            if success:
                                print(f"\n*** SUCCESS: {name} works! ***")

                return

    print("No messages with images found in recent history")


if __name__ == "__main__":
    asyncio.run(test_image_download())

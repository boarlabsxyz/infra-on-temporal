from temporalio import activity
import os
from dotenv import load_dotenv
load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

@activity.defn
async def send_message_to_slack(info):
    import aiohttp

    message, channel = info[0], info[1]

    payload = {
        "text": f"*-----------   '{channel}'   -----------*\n\n{message}"
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




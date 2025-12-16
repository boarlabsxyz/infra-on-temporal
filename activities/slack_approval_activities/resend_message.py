from temporalio import activity
import os

from dotenv import load_dotenv
load_dotenv()

SLACK_WEBHOOK_URL2 = os.getenv("SLACK_WEBHOOK_URL_NEWS")

@activity.defn
async def resend_message(message: str):
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.post(
            SLACK_WEBHOOK_URL2,
            json={"text": message},
            headers={"Content-type": "application/json"}
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"Webhook request failed: {resp.status}, {body}")
            return await resp.text()




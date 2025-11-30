# Example in Python using the 'requests' library
from temporalio import activity
import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")

@activity.defn
async def get_claude_answer_activity(context: str) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    instructions = 'Translate the following message to English. Do not change the links. If message is already in English, just return it as is.'

    message = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1000,
    messages=[
        {"role": "user", "content": f"{instructions}\n\n{context}"}
    ]
    )
    return message.content[0].text


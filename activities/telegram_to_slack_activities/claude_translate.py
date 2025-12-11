from temporalio import activity
import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")

@activity.defn
async def get_claude_answer_activity(context: str) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)

    instructions = """
You are a text formatting assistant.

Your task is to convert Telegram message text into Slack-compatible formatting and translate it to English if it is not already in English. Follow these rules:

1. Preserve all the content and meaning.
2. Do not change any links. Keep URLs exactly as they are.
3. Convert Telegram formatting to Slack formatting:
   - Bold (Telegram **text**) → Slack bold (*text* or **text**)
   - Italic (Telegram _text_ or __text__) → Slack italic (_text_)
   - Strikethrough (Telegram ~text~) → Slack strikethrough (~text~)
   - Inline code (Telegram `code`) → Slack inline code (`code`)
   - Code blocks (Telegram ```code```) → Slack code blocks (```code```)
   - Links (Telegram [label](url)) → Slack link format (<url|label>)
4. Translate the text to English if it is in another language. If it is already in English, return it as is.
5. Preserve emojis and line breaks.
6. Remove any unsupported Telegram-specific formatting.
7. Output only the Slack-formatted and English-translated text. Do not include explanations.
"""

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": f"{instructions}\n\n{context}"}
        ]
    )

    return message.content[0].text

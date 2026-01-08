from temporalio import activity
import os
import re
from dotenv import load_dotenv
load_dotenv()


def format_telegram_to_slack(text: str) -> str:
    """Convert Telegram formatting to Slack formatting using regex."""
    # Remove hashtags
    text = re.sub(r'#\w+', '', text)

    # Convert Telegram bold **text** to Slack bold *text*
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)

    # Convert Telegram links [label](url) to Slack <url|label>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<\2|\1>', text)

    # Italic, strikethrough, code blocks are the same in both formats
    # (no conversion needed)

    return text.strip()

api_key = os.getenv("ANTHROPIC_API_KEY")

@activity.defn
async def get_claude_answer_activity(context: str) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)

    # Apply regex formatting before Claude processing
    formatted_context = format_telegram_to_slack(context)

    # First, check if the message is appropriate and relevant
    validation_instructions = """
You are a content validator for a news and AI technology aggregation system.

Analyze the provided message and determine:
1. Is this message about news, current events, technology, AI, or related professional topics?
2. Is the content appropriate (no spam, harassment, explicit content, advertisements, or off-topic messages)?

Respond with ONLY one word:
- "VALID" if the message is news/AI/tech-related and appropriate
- "INVALID" if the message is inappropriate, spam, off-topic, or not relevant

Be strict: only allow messages that are clearly about news, AI, technology, science, current events, or related professional topics.
"""

    validation_message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=10,
        messages=[
            {"role": "user", "content": f"{validation_instructions}\n\nMessage to validate:\n{formatted_context}"}
        ]
    )

    validation_result = validation_message.content[0].text.strip().upper()

    # If message is invalid, return empty string to signal filtering
    if validation_result != "VALID":
        activity.logger.info(f"Message filtered out as invalid: {validation_result}")
        return ""

    # If valid, proceed with translation
    instructions = """
You are a translation assistant.

Translate the provided text to English if it is not already in English. Follow these rules:

1. Preserve all the content and meaning.
2. Do not change any links or formatting. Keep URLs and formatting exactly as they are.
3. Preserve emojis and line breaks.
4. If the text is already in English, return it as is.
5. Output only the translated text. Do not include explanations.
"""

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": f"{instructions}\n\n{formatted_context}"}
        ]
    )

    return message.content[0].text

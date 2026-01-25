from temporalio import activity
import os
import re
from dotenv import load_dotenv
load_dotenv()


def cleanup_markdown(text: str) -> str:
    """Clean up malformed markdown formatting."""
    if not text:
        return text

    # First, convert valid **text** to *text* for Slack bold
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)

    # Remove orphaned ** that don't have matching pairs
    while True:
        matches = list(re.finditer(r'\*\*', text))
        if len(matches) % 2 == 0:
            break
        if matches:
            last_match = matches[-1]
            text = text[:last_match.start()] + text[last_match.end():]
        else:
            break

    # Handle single asterisks per line
    # Valid bold: *text* where text starts and ends with non-whitespace
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Check if line has valid *text* patterns only
        # Valid: *word* or *multiple words* (no space after * or before *)
        test_line = line
        # Remove all valid *text* patterns
        test_line = re.sub(r'\*\S[^*]*\S\*', '', test_line)
        test_line = re.sub(r'\*\S\*', '', test_line)  # Single char like *a*

        # If there are still asterisks, the line has invalid formatting
        if '*' in test_line:
            # Remove all asterisks from the original line
            line = line.replace('*', '')

        cleaned_lines.append(line)

    text = '\n'.join(cleaned_lines)
    return text


def format_telegram_to_slack(text: str) -> str:
    """Convert Telegram formatting to Slack formatting using regex."""
    # Remove hashtags
    text = re.sub(r'#\w+', '', text)

    # Convert Telegram bold **text** to Slack bold *text*
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)

    # Convert Telegram strikethrough ~~text~~ to Slack strikethrough ~text~
    text = re.sub(r'~~(.+?)~~', r'~\1~', text)

    # Extract and temporarily replace Telegram links to protect them during escaping
    links = []
    def save_link(match):
        label = match.group(1)
        url = match.group(2)
        # Escape pipe characters in labels (would break Slack link format)
        label = label.replace('|', '-')
        links.append((url, label))
        return f'\x00LINK{len(links)-1}\x00'

    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', save_link, text)

    # Escape special characters for Slack mrkdwn (must happen after link extraction)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')

    # Restore links in Slack format
    for i, (url, label) in enumerate(links):
        text = text.replace(f'\x00LINK{i}\x00', f'<{url}|{label}>')

    # Italic and code blocks are the same in both formats (no conversion needed)

    text = text.strip()

    # Truncate to stay under Slack's 3000 char limit for section blocks (with buffer)
    if len(text) > 2900:
        text = text[:2900] + '... [truncated]'

    return text

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

    # Clean up any malformed markdown from translation
    return cleanup_markdown(message.content[0].text)

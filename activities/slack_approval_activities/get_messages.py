from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from typing import List
from temporalio import activity
import os

from dotenv import load_dotenv
load_dotenv()

client = WebClient(token=os.getenv("SLACK_TOKEN"))

@activity.defn
async def get_messages(channel_id: str, limit: int = 15) -> List[str]:
    """
    Fetches the last few messages from a Slack channel and returns their timestamps
    in chronological order (oldest to newest).
    
    Args:
        channel_id: The Slack channel ID to fetch messages from
        limit: Maximum number of messages to fetch (default: 10)
    
    Returns:
        List of message timestamps ordered from oldest to newest
    """
    try:
        # Fetch conversation history from Slack
        # Note: Slack API returns messages in reverse chronological order (newest first)
        res = client.conversations_history(
            channel=channel_id,
            limit=limit
        )
        
        activity.logger.info(f"Fetched {len(res.get('messages', []))} messages from channel {channel_id}")
        
        # Check if messages exist
        messages = res.get("messages", [])
        if not messages:
            activity.logger.warning(f"No messages found in channel {channel_id}")
            return []
        
        # Extract timestamps from messages
        timestamps = [msg["ts"] for msg in messages if "ts" in msg]
        
        # Reverse to get chronological order (oldest to newest)
        # This ensures messages are processed from old to new
        timestamps_oldest_first = list(reversed(timestamps))
        
        activity.logger.info(f"Returning {len(timestamps_oldest_first)} message timestamps in chronological order")
        return timestamps_oldest_first
        
    except SlackApiError as e:
        activity.logger.error(f"Slack API error: {e.response['error']}")
        raise
    except Exception as e:
        activity.logger.error(f"Unexpected error fetching messages: {str(e)}")
        raise

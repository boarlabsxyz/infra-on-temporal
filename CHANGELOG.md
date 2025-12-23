# Changelog - Message Processing Updates

## Summary
Updated both Slack and Telegram message fetching activities to retrieve the last N messages and process them in chronological order (oldest to newest).

## Changes Made

### 1. Slack Activity: `activities/slack_approval_activities/get_messages.py`
- Added `limit` parameter (default: 10) to control number of messages fetched
- Enhanced error handling with SlackApiError
- Improved logging using activity.logger
- Added validation for empty messages
- Returns messages in chronological order (oldest to newest)
- Added comprehensive docstring

### 2. Telegram Activity: `activities/telegram_to_slack_activities/telegram_get_messeges.py`
- **Breaking Change**: Changed return type from single dict to List[Dict[str, Any]]
- Added `limit` parameter (default: 10) to control number of messages fetched
- Fixed import error: Changed from `TelegramError` to `RPCError` (correct telethon exception)
- Added authorization check before fetching messages
- Enhanced error handling with try/finally for proper cleanup
- Improved logging using activity.logger throughout
- Returns messages in chronological order (oldest to newest)
- Added comprehensive docstring
- Added type hints

### 3. Telegram Workflow: `workflows/telegram_to_slack_workflow.py`
- Updated to handle list of messages returned by fetch_last_message activity
- Added loop to process each message in chronological order
- Added check to skip already-processed messages (msg_id <= last_saved_id)
- Updates last_ids after processing each message
- Added better logging for tracking message processing

### 4. Worker: `worker.py`
- No changes needed - already correctly imports and registers all activities

### 5. Workflow Runners: `run_workflows/tg_to_slack.py`
- No changes needed - workflow initialization remains the same

## Backward Compatibility

### Slack Workflow
✅ **Fully backward compatible** - The `get_messages` activity maintains backward compatibility with its optional `limit` parameter (default: 10).

### Telegram Workflow
⚠️ **Breaking change** - The `fetch_last_message` activity now returns a list instead of a single message. Existing workflow instances will need to be terminated and restarted.

## Testing Recommendations

1. **Stop existing workflows** - Terminate any running instances of TelegramMonitorWorkflow
2. **Restart worker** - Ensure the worker picks up the new code
3. **Start fresh workflows** - Launch new workflow instances with the updated code
4. **Monitor logs** - Check that messages are being processed in chronological order

## Benefits

1. **Batch Processing**: Can now fetch multiple messages at once, reducing API calls
2. **Chronological Order**: Messages are always processed from oldest to newest
3. **Better Error Handling**: Comprehensive error handling prevents workflow failures
4. **Improved Logging**: Detailed logs help with debugging and monitoring
5. **Configurable**: The `limit` parameter allows adjusting how many messages to fetch

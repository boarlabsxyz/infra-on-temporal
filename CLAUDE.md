# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Message routing and approval workflow system that monitors Telegram channels for messages, translates/filters them using Claude AI, and forwards to Slack. Also monitors Slack for approval reactions and resends approved messages to a news channel.

**Stack:** Python 3.11, Temporal (workflow orchestration), Telethon (Telegram), Slack SDK, Anthropic Claude, PostgreSQL, Docker

## Commands

```bash
# Local development (starts PostgreSQL, Temporal server, Temporal UI on port 8080)
docker-compose up

# Run worker (requires Temporal server running)
python worker.py

# Run tests
pytest tests/

# Generate Telegram session string
python save_session.py

# Manually trigger workflows
python run_workflows/tg_to_slack.py
python run_workflows/slack_approval.py
```

## Architecture

### Two Main Workflows

1. **TelegramMonitorWorkflow** (`workflows/telegram_to_slack_workflow.py`):
   - Polls Telegram channels every 3 minutes
   - Validates content with Claude (spam/inappropriate detection)
   - Translates valid messages with Claude
   - Forwards to Slack with image support
   - Uses "Continue as New" pattern every 30 minutes to prevent history bloat

2. **PollSlackForReactionWorkflow** (`workflows/slack_approval_workflow.py`):
   - Polls Slack channel every 5 minutes
   - Checks for "white_check_mark" reactions (approval indicator)
   - Downloads images from approved messages
   - Resends approved messages to news channel
   - Uses "Continue as New" pattern every 60 minutes

### Activities Pattern

Activities are in `activities/` and are called by workflows:
- `telegram_to_slack_activities/`: fetch messages, Claude processing, Slack sending
- `slack_approval_activities/`: get messages, check reactions, resend messages

All activities use `RetryPolicy(maximum_attempts=5)` with timeouts ranging 30-180 seconds.

### Message Processing Pipeline

```
Telegram Fetch → Claude Validation → Claude Translation → Slack Send
                      ↓
                 [INVALID] → skip (returns empty string)
                 [VALID]   → format & translate → send with optional images
```

### Slack Fallback Chain

1. Slack API with images (preferred, supports threads)
2. Slack API text-only
3. Webhook with Block Kit (last resort)

## Key Implementation Details

- **Message ordering:** Workflows reverse API responses to process oldest→newest
- **State management:** "Continue as New" prevents gRPC message size limits
- **Idempotency:** Workflows track processed message IDs to avoid duplicates
- **Image handling:** Binary → base64 for transmission between activities

## Environment Variables

Required in `.env`:
- `SLACK_TOKEN`, `SLACK_BOT_TOKEN`, `SLACK_WEBHOOK_URL`, `SLACK_WEBHOOK_URL_NEWS`
- `SLACK_CHANNEL_ID`, `SLACK_CHANNEL_ID_NEWS`
- `TG_API_ID`, `TG_API_HASH`, `TG_SESSION_SRING` (note: typo is intentional, matches code)
- `ANTHROPIC_API_KEY`
- `TEMPORAL_ADDRESS` (default: localhost:7233)

## Deployment

Railway.app deployment configured via `railway.json`. GitHub Actions workflow in `.github/workflows/deploy.yml` deploys on push to `main` branch.

## Known Gotchas

- `TG_SESSION_SRING` environment variable has a typo (missing 'T') - this is intentional, matches the code
- Claude prompts are in the activity files (`claude_translate.py`) - modify carefully as they affect validation and translation quality
- Temporal UI at port 8080 for debugging workflow state and history

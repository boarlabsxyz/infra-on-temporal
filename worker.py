# run_worker.py
import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from workflows.telegram_to_slack_workflow import TelegramMonitorWorkflow
from activities.telegram_to_slack_activities.telegram_get_messeges import (
    fetch_last_message,
    get_client as get_telegram_client,
    shutdown_client as shutdown_telegram_client,
)
from activities.telegram_to_slack_activities.claude_translate import get_claude_answer_activity
from activities.telegram_to_slack_activities.send_message_to_slack import send_message_to_slack

from workflows.slack_approval_workflow import PollSlackForReactionWorkflow
from activities.slack_approval_activities.get_messages import get_messages
from activities.slack_approval_activities.get_reactions import check_reactions
from activities.slack_approval_activities.resend_message import resend_message


async def main():
    """Connect to Temporal server and run the worker with all registered workflows and activities."""
    client = await Client.connect(os.getenv("TEMPORAL_ADDRESS", "localhost:7233"))

    # Pre-warm the shared Telegram client so the first activity invocation doesn't
    # pay the auth-key + DC discovery cost on a tight Temporal timeout.
    try:
        await get_telegram_client()
        print("Telegram client connected")
    except Exception as e:
        # Non-fatal: the activity will retry. Log and keep going so the worker still serves
        # other workflows (slack approval) even if Telegram auth is misconfigured.
        print(f"Telegram client pre-warm failed (will retry on first use): {e}")

    worker = Worker(
        client,
        task_queue="multi-task-queue",
        workflows=[TelegramMonitorWorkflow, PollSlackForReactionWorkflow],
        activities=[fetch_last_message, get_claude_answer_activity, send_message_to_slack, get_messages, check_reactions, resend_message],
    )

    print("Worker started")
    try:
        await worker.run()
    finally:
        await shutdown_telegram_client()
        print("Telegram client disconnected")

if __name__ == "__main__":
    asyncio.run(main())

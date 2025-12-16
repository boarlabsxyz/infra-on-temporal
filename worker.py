# run_worker.py
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from workflows.telegram_to_slack_workflow import TelegramMonitorWorkflow
from activities.telegram_to_slack_activities.telegram_get_messeges import fetch_last_message
from activities.telegram_to_slack_activities.claude_translate import get_claude_answer_activity
from activities.telegram_to_slack_activities.send_message_to_slack import send_message_to_slack

from workflows.slack_approval_workflow import PollSlackForReactionWorkflow
from activities.slack_approval_activities.get_messages import get_messages
from activities.slack_approval_activities.get_reactions import check_reactions
from activities.slack_approval_activities.resend_message import resend_message

import os


async def main():
    client = await Client.connect(os.getenv("TEMPORAL_ADDRESS", "localhost:7233"))

    worker = Worker(
        client,
        task_queue="multi-task-queue",
        workflows=[TelegramMonitorWorkflow, PollSlackForReactionWorkflow],
        activities=[fetch_last_message, get_claude_answer_activity, send_message_to_slack, get_messages, check_reactions, resend_message],
    )

    print("Worker started")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())

# run_worker.py
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from workflows.telegram_to_slack_workflow import TelegramMonitorWorkflow
from activities.telegram_to_slack_activities.telegram_get_messeges import fetch_channel_messages
from activities.telegram_to_slack_activities.claude_translate import get_claude_answer_activity
from activities.telegram_to_slack_activities.send_message_to_slack import send_message_to_slack


async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="telegram-monitor",
        workflows=[TelegramMonitorWorkflow],
        activities=[fetch_channel_messages, get_claude_answer_activity, send_message_to_slack],
    )

    print("Worker started")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())

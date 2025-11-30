import asyncio

from temporalio.worker import Worker
from temporalio.client import Client

from workflows.slack_approval_workflow import PollSlackForReactionWorkflow
from activities.slack_approval_activities.get_messages import get_messages
from activities.slack_approval_activities.get_reactions import check_reactions
from activities.slack_approval_activities.resend_message import resend_message


async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="translator-task-queue",
        workflows=[PollSlackForReactionWorkflow],
        activities=[get_messages, check_reactions, resend_message],
    )

    print("Worker started...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

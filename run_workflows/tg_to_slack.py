# run_workflow.py
import asyncio
from temporalio.client import Client


async def main():
    client = await Client.connect("localhost:7233")

    result = await client.start_workflow(
        "TelegramMonitorWorkflow",
        ["dmytrogorin", "automation_remarks_ua", "xpinjection_channel"],               # channel list
        id="tg-monitor-1",
        task_queue="multi-task-queue",
    )

    print("Workflow started:", result)

if __name__ == "__main__":
    asyncio.run(main())

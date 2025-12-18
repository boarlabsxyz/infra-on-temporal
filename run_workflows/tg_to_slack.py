# run_workflow.py
import asyncio
from temporalio.client import Client
import time

async def main():
    client = await Client.connect("localhost:7233")

    result = await client.start_workflow(
        "TelegramMonitorWorkflow",
        [["dmytrogorin", "automation_remarks_ua", "xpinjection_channel"], {}, time.time()],               # channel list "dmytrogorin", "automation_remarks_ua", "xpinjection_channel"
        id="tg-monitor-1",
        task_queue="multi-task-queue",
    )

    print("Workflow started:", result)

if __name__ == "__main__":
    asyncio.run(main())

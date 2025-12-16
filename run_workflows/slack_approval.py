# run_workflow.py
import asyncio
from temporalio.client import Client


async def main():
    client = await Client.connect("localhost:7233")


    result = await client.start_workflow(
        "PollSlackForReactionWorkflow",
        "C09R8GCL2K1", 
        id="slack-monitor-1",
        task_queue="multi-task-queue",
    )

    print("Workflow started:", result)


if __name__ == "__main__":
    asyncio.run(main())

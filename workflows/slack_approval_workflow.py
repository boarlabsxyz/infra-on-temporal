from temporalio import workflow
from datetime import timedelta
from activities.slack_approval_activities.get_messages import get_messages
from activities.slack_approval_activities.get_reactions import check_reactions
from activities.slack_approval_activities.resend_message import resend_message


@workflow.defn
class PollSlackForReactionWorkflow:
    def __init__(self):
        self.processed = set()     # ✅ store processed message timestamps

    @workflow.run
    async def run(self, channel_id: str):

        while True:
            timestamps = await workflow.execute_activity(
                get_messages,
                channel_id,
                schedule_to_close_timeout=timedelta(seconds=10),
            )

            for ts in timestamps:

                # ✅ Skip duplicates
                if ts in self.processed:
                    continue

                info = await workflow.execute_activity(
                    check_reactions,
                    [ts, channel_id],
                    schedule_to_close_timeout=timedelta(seconds=10),
                )

                # ✅ Immediately mark as processed
                self.processed.add(ts)

                if info.get("reactions"):
                    if any(r.get("name") == "white_check_mark" for r in info["reactions"]):
                        await workflow.execute_activity(
                            resend_message,
                            info["text"],
                            schedule_to_close_timeout=timedelta(seconds=10),
                        )

                workflow.logger.info(f"Checked message {ts}: {info}")

            workflow.logger.info(f"Got {len(timestamps)} timestamps")
            await workflow.sleep(timedelta(minutes=1))

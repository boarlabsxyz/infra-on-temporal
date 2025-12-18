from temporalio import workflow
from datetime import timedelta
from typing import List, Optional

from activities.slack_approval_activities.get_messages import get_messages
from activities.slack_approval_activities.get_reactions import check_reactions
from activities.slack_approval_activities.resend_message import resend_message


@workflow.defn
class PollSlackForReactionWorkflow:

    @workflow.run
    async def run(self, pollstate):
        channel_id = pollstate[0]
        resent = pollstate[1]
        started_at = pollstate[2]

        while True:
            timestamps = await workflow.execute_activity(
                get_messages,
                channel_id,
                schedule_to_close_timeout=timedelta(seconds=10),
            )

            for ts in timestamps:
                if ts in resent:
                    continue

                info = await workflow.execute_activity(
                    check_reactions,
                    [ts, channel_id],
                    schedule_to_close_timeout=timedelta(seconds=10),
                )

                has_checkmark = any(
                    r.get("name") == "white_check_mark"
                    for r in info.get("reactions", [])
                )

                if has_checkmark:
                    await workflow.execute_activity(
                        resend_message,
                        info["text"],
                        schedule_to_close_timeout=timedelta(seconds=10),
                    )

                    resent.append(ts)

                    if len(resent) > 50:
                        resent = resent[-20:]

                workflow.logger.info(f"Checked message {ts}")

            if workflow.now().timestamp() - started_at >= 6 * 60 * 60:
                await workflow.continue_as_new(
                    [channel_id,
                    resent,
                    workflow.now().timestamp(),]
                )

            await workflow.sleep(timedelta(minutes=1))
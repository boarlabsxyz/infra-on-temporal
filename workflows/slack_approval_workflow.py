from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError
from datetime import timedelta
from typing import List, Optional

with workflow.unsafe.imports_passed_through():
    from activities.slack_approval_activities.get_messages import get_messages
    from activities.slack_approval_activities.get_reactions import check_reactions
    from activities.slack_approval_activities.resend_message import resend_message


@workflow.defn
class PollSlackForReactionWorkflow:
    # Slack answers `ratelimited` with Retry-After of up to a minute, so attempts
    # need room to wait it out and back off.
    SLACK_TIMEOUT = timedelta(minutes=5)
    SLACK_RETRY = RetryPolicy(
        maximum_attempts=5,
        initial_interval=timedelta(seconds=5),
        maximum_interval=timedelta(seconds=60),
    )

    @workflow.run
    async def run(self, pollstate):
        """Poll Slack for approved messages and resend them to the news channel."""
        channel_id = pollstate[0]
        resent = pollstate[1]
        started_at = pollstate[2]

        while True:
            # A Slack failure must not kill the monitor: skip this poll and try the next.
            try:
                timestamps = await workflow.execute_activity(
                    get_messages,
                    channel_id,
                    schedule_to_close_timeout=self.SLACK_TIMEOUT,
                    retry_policy=self.SLACK_RETRY,
                )
            except ActivityError as e:
                workflow.logger.warning(f"Fetching Slack messages failed, skipping this poll: {e.cause or e}")
                timestamps = []

            for ts in timestamps:
                if ts in resent:
                    continue

                try:
                    info = await workflow.execute_activity(
                        check_reactions,
                        [ts, channel_id],
                        schedule_to_close_timeout=self.SLACK_TIMEOUT,
                        retry_policy=self.SLACK_RETRY,
                    )
                except ActivityError as e:
                    workflow.logger.warning(f"Checking reactions on {ts} failed, retrying next poll: {e.cause or e}")
                    continue

                has_checkmark = any(
                    r.get("name") == "white_check_mark"
                    for r in info.get("reactions", [])
                )

                if has_checkmark:
                    # Prepare message info with image data if available
                    message_info = {
                        "text": info["text"],
                        "has_image": info.get("has_image", False),
                        "image_data": info.get("image_data")
                    }
                    
                    try:
                        await workflow.execute_activity(
                            resend_message,
                            message_info,
                            schedule_to_close_timeout=self.SLACK_TIMEOUT,
                            retry_policy=self.SLACK_RETRY,
                        )
                    except ActivityError as e:
                        # Not marked as resent, so the next poll tries again.
                        workflow.logger.warning(f"Resending {ts} failed, retrying next poll: {e.cause or e}")
                        continue

                    resent.append(ts)

                    if len(resent) > 50:
                        resent = resent[-20:]

                workflow.logger.info(f"Checked message {ts}")

            if workflow.now().timestamp() - started_at >= 30 * 60:
                await workflow.continue_as_new(
                    [channel_id,
                    resent,
                    workflow.now().timestamp()]
                )

            await workflow.sleep(timedelta(minutes=5))

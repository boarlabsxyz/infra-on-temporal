from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from typing import Dict, Optional

from activities.telegram_to_slack_activities.telegram_get_messeges import fetch_last_message
from activities.telegram_to_slack_activities.claude_translate import get_claude_answer_activity
from activities.telegram_to_slack_activities.send_message_to_slack import send_message_to_slack


@workflow.defn
class TelegramMonitorWorkflow:

    @workflow.run
    async def run(self, pollstate):
        channel_list = pollstate[0]
        last_ids = pollstate[1]
        started_at = pollstate[2]

        while True:
            for channel in channel_list:
                last_saved_id = last_ids.get(channel, 0)

                last_msg = await workflow.execute_activity(
                    fetch_last_message,
                    channel,
                    schedule_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(maximum_attempts=5),
                )

                if not last_msg or (len(last_msg["text"]) == 0 and not last_msg.get("has_image", False)):
                    continue

                msg_id = last_msg["id"]

                if msg_id == last_saved_id:
                    continue

                translated = await workflow.execute_activity(
                    get_claude_answer_activity,
                    last_msg["text"],
                    schedule_to_close_timeout=timedelta(seconds=180),
                    retry_policy=RetryPolicy(maximum_attempts=5),
                )

                await workflow.execute_activity(
                    send_message_to_slack,
                    [translated, channel, last_msg.get("has_image", False), last_msg.get("image_data")],
                    schedule_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(maximum_attempts=5),
                )

                last_ids[channel] = msg_id

                workflow.logger.info(
                    f"Sent new message from {channel}: ID={msg_id}"
                )

            if workflow.now().timestamp() - started_at >= 6 * 60 * 60:
                await workflow.continue_as_new(
                    [channel_list,
                    last_ids,
                    workflow.now().timestamp()],
                )

            await workflow.sleep(timedelta(minutes=1))

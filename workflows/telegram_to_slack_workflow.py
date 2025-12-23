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

                # Fetch last few messages (returns list in chronological order: oldest to newest)
                messages = await workflow.execute_activity(
                    fetch_last_message,
                    channel,
                    schedule_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(maximum_attempts=5),
                )

                if not messages:
                    workflow.logger.info(f"No messages found in channel {channel}")
                    continue

                workflow.logger.info(f"Processing {len(messages)} messages from {channel}")

                # Process messages in chronological order (oldest to newest)
                for last_msg in messages:
                    # Skip empty messages
                    if not last_msg or (len(last_msg["text"]) == 0 and not last_msg.get("has_image", False)):
                        continue

                    msg_id = last_msg["id"]

                    # Skip messages that have already been processed
                    if msg_id <= last_saved_id:
                        continue

                    translated = await workflow.execute_activity(
                        get_claude_answer_activity,
                        last_msg["text"],
                        schedule_to_close_timeout=timedelta(seconds=180),
                        retry_policy=RetryPolicy(maximum_attempts=5),
                    )

                    # If translated is empty, the message was filtered out as inappropriate or off-topic
                    if translated and translated.strip():
                        await workflow.execute_activity(
                            send_message_to_slack,
                            [translated, channel, last_msg.get("has_image", False), last_msg.get("image_data"), msg_id, last_msg["text"]],
                            schedule_to_close_timeout=timedelta(seconds=30),
                            retry_policy=RetryPolicy(maximum_attempts=5),
                        )

                        workflow.logger.info(
                            f"Sent new message from {channel}: ID={msg_id}"
                        )
                    else:
                        workflow.logger.info(
                            f"Message from {channel} (ID={msg_id}) was filtered out as inappropriate or off-topic"
                        )

                    # Update last_ids after processing each message
                    last_ids[channel] = msg_id

            if workflow.now().timestamp() - started_at >= 6 * 60 * 60:
                await workflow.continue_as_new(
                    [channel_list,
                    last_ids,
                    workflow.now().timestamp()],
                )

            await workflow.sleep(timedelta(minutes=1))

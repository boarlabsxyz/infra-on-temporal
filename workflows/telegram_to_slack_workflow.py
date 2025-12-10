from datetime import timedelta
from temporalio import workflow
from activities.telegram_to_slack_activities.telegram_get_messeges import fetch_channel_messages
from activities.telegram_to_slack_activities.claude_translate import get_claude_answer_activity
from activities.telegram_to_slack_activities.send_message_to_slack import send_message_to_slack


@workflow.defn
class TelegramMonitorWorkflow:
    def __init__(self):
        self.last_ids = {}

    @workflow.run
    async def run(self, channel_list: list[str]):
        while True:
            for channel in channel_list:

                last_id = self.last_ids.get(channel, 0)

                new_msgs = await workflow.execute_activity(
                    fetch_channel_messages,
                    [channel, last_id],
                    schedule_to_close_timeout=timedelta(seconds=30),
                )

                if new_msgs:
                    latest = new_msgs[0]["id"]
                    self.last_ids[channel] = latest

                    for msg in new_msgs:
                        if len(msg['text']) == 0:
                            continue

                        translated = await workflow.execute_activity(
                            get_claude_answer_activity,
                            msg["text"],
                            schedule_to_close_timeout=timedelta(seconds=180),
                        )

                        workflow.logger.info(
                            f"Translated by Claude:\n{translated}"
                        )

                        await workflow.execute_activity(
                            send_message_to_slack,
                            translated,
                            schedule_to_close_timeout=timedelta(seconds=30),
                        )

                workflow.logger.info(
                    f"{channel}: {len(new_msgs)} new messages"
                )

            await workflow.sleep(timedelta(minutes=1))

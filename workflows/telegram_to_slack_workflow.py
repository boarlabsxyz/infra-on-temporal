from datetime import timedelta
from temporalio import workflow
from activities.telegram_to_slack_activities.telegram_get_messeges import fetch_last_message
from activities.telegram_to_slack_activities.claude_translate import get_claude_answer_activity
from activities.telegram_to_slack_activities.send_message_to_slack import send_message_to_slack

@workflow.defn
class TelegramMonitorWorkflow:
    def __init__(self):
        self.last_ids = {}   # {channel: id}

    @workflow.run
    async def run(self, channel_list: list[str]):
        while True:
            for channel in channel_list:

                last_saved_id = self.last_ids.get(channel, 0)

                last_msg = await workflow.execute_activity(
                    fetch_last_message,
                    channel,
                    schedule_to_close_timeout=timedelta(seconds=30),
                )

                if not last_msg or len(last_msg["text"]) == 0:
                    continue

                msg_id = last_msg["id"]

                if msg_id == last_saved_id:
                    continue

                translated = await workflow.execute_activity(
                    get_claude_answer_activity,
                    last_msg["text"],
                    schedule_to_close_timeout=timedelta(seconds=180),
                )

                await workflow.execute_activity(
                    send_message_to_slack,
                    [translated, channel],
                    schedule_to_close_timeout=timedelta(seconds=30),
                )

                self.last_ids[channel] = msg_id

                workflow.logger.info(
                    f"Sent new message from {channel}: ID={msg_id}"
                )

            await workflow.sleep(timedelta(minutes=1))

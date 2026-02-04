import pytest

from activities.slack_approval_activities.resend_message import extract_content_only


class TestExtractContentOnly:
    def test_removes_telegram_channel_line(self):
        text = """Telegram Channel: automation_remarks_ua
State of AI in 2026

Lex Fridman released an interesting video about AI."""

        result = extract_content_only(text)

        assert "Telegram Channel" not in result
        assert "automation_remarks_ua" not in result
        assert "State of AI in 2026" in result
        assert "Lex Fridman" in result

    def test_removes_telegram_channel_with_emoji(self):
        text = """📱 *Telegram Channel:* `automation_remarks_ua`
<https://t.me/automation_remarks_ua/123|View original on Telegram>

State of AI in 2026

Lex Fridman released an interesting video about AI."""

        result = extract_content_only(text)

        assert "Telegram Channel" not in result
        assert "View original" not in result
        assert "State of AI in 2026" in result
        assert "Lex Fridman" in result

    def test_removes_view_original_line(self):
        text = """View original on Telegram
This is the actual content."""

        result = extract_content_only(text)

        assert "View original" not in result
        assert "This is the actual content" in result

    def test_removes_approved_message_line(self):
        text = """✅ *Approved Message*

This is the actual content."""

        result = extract_content_only(text)

        assert "Approved Message" not in result
        assert "This is the actual content" in result

    def test_removes_all_metadata_lines(self):
        text = """📱 *Telegram Channel:* `test_channel`
<https://t.me/test/123|View original on Telegram>

State of AI in 2026

Lex Fridman released an interesting video about AI, but very short. Only 4 hours

https://www.youtube.com/watch?v=EV7WhVT270Q"""

        result = extract_content_only(text)

        assert "Telegram Channel" not in result
        assert "View original" not in result
        assert "State of AI in 2026" in result
        assert "Lex Fridman" in result
        assert "youtube.com" in result

    def test_preserves_content_only(self):
        text = """Telegram Channel: automation_remarks_ua
View original on Telegram

State of AI in 2026

Lex Fridman released an interesting video about AI, but very short. Only 4 hours

https://www.youtube.com/watch?v=EV7WhVT270Q"""

        expected = """State of AI in 2026

Lex Fridman released an interesting video about AI, but very short. Only 4 hours

https://www.youtube.com/watch?v=EV7WhVT270Q"""

        result = extract_content_only(text)

        assert result == expected

    def test_handles_empty_text(self):
        assert extract_content_only("") == ""
        assert extract_content_only(None) is None

    def test_handles_text_without_metadata(self):
        text = "Just a normal message without any metadata."
        result = extract_content_only(text)
        assert result == text

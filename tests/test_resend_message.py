import pytest

from activities.slack_approval_activities.resend_message import extract_content_only


class TestExtractContentOnly:
    def test_removes_telegram_channel_line(self):
        """Verify Telegram Channel metadata line is stripped from message text."""
        text = """Telegram Channel: automation_remarks_ua
State of AI in 2026

Lex Fridman released an interesting video about AI."""

        result = extract_content_only(text)

        assert "Telegram Channel" not in result
        assert "automation_remarks_ua" not in result
        assert "State of AI in 2026" in result
        assert "Lex Fridman" in result

    def test_removes_telegram_channel_with_emoji(self):
        """Verify Telegram Channel line with emoji and Slack formatting is stripped."""
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
        """Verify 'View original' link line is stripped from message text."""
        text = """View original on Telegram
This is the actual content."""

        result = extract_content_only(text)

        assert "View original" not in result
        assert "This is the actual content" in result

    def test_removes_approved_message_line(self):
        """Verify 'Approved Message' header line is stripped from message text."""
        text = """✅ *Approved Message*

This is the actual content."""

        result = extract_content_only(text)

        assert "Approved Message" not in result
        assert "This is the actual content" in result

    def test_removes_all_metadata_lines(self):
        """Verify all metadata lines are stripped while preserving content and URLs."""
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
        """Verify output matches expected content after all metadata is removed."""
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
        """Verify empty and None inputs are returned unchanged."""
        assert extract_content_only("") == ""
        assert extract_content_only(None) is None

    def test_handles_text_without_metadata(self):
        """Verify plain text without metadata is returned unchanged."""
        text = "Just a normal message without any metadata."
        result = extract_content_only(text)
        assert result == text

import pytest
from unittest.mock import patch, MagicMock

from activities.telegram_to_slack_activities.claude_translate import (
    get_claude_answer_activity
)

pytestmark = pytest.mark.asyncio


def mock_anthropic_response(text: str):
    """Create a mock Anthropic API response with the given text."""
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=text)]
    return mock_msg


@patch("anthropic.Anthropic")
async def test_invalid_message_is_filtered(mock_anthropic):
    """Verify that messages flagged as INVALID by Claude return an empty string."""
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client

    # Validation call → INVALID
    mock_client.messages.create.return_value = mock_anthropic_response("INVALID")

    result = await get_claude_answer_activity("Buy cheap crypto now!!!")

    assert result == ""


@patch("anthropic.Anthropic")
async def test_valid_message_is_processed(mock_anthropic):
    """Verify that valid messages are translated and returned with Slack formatting."""
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client

    validation_response = mock_anthropic_response("VALID")
    formatted_response = mock_anthropic_response(
       """*Quality Engineering Challenges in 2025 and What to Do About Them in 2026*
New year, same old problems:zany_face:
Over the next 3 days, we'll break down 1 problem at a time.
Quality software is not just about testing. It's the ability to integrate quality into the entire development process, from idea to production. But even in 2026, many teams still face fundamental problems.
:brain: *Challenge 1: Quality is not understanding, just a word*
:point_right: Problem: different people on the team have different ideas about "quality". Because of this, responsibility is blurred, and quality remains on the sidelines.
What to do:
:jigsaw: Define 3-5 key quality attributes for your product (for example, testability, performance, reliability).
:jigsaw: Make responsibility explicit: who decides, who implements, who checks, who monitors.
:jigsaw: Measure what "good" means — establish signals that show when quality is achieved or violated.
:bulb: Mini-experiment: 30 minutes to align on quality with the team — and you're already a step ahead."""
    )

    mock_client.messages.create.side_effect = [
        validation_response,
        formatted_response,
    ]

    result = await get_claude_answer_activity(
        """**Quality Engineering Challenges in 2025 and What to Do About Them in 2026**
New year, same old problems:zany_face:
Over the next 3 days, we'll break down 1 problem at a time.
Quality software is not just about testing. It's the ability to integrate quality into the entire development process, from idea to production. But even in 2026, many teams still face fundamental problems.
:brain: **Challenge 1: Quality is not understanding, just a word**
:point_right: Problem: different people on the team have different ideas about "quality". Because of this, responsibility is blurred, and quality remains on the sidelines.
What to do:
:jigsaw: Define 3-5 key quality attributes for your product (for example, testability, performance, reliability).
:jigsaw: Make responsibility explicit: who decides, who implements, who checks, who monitors.
:jigsaw: Measure what "good" means — establish signals that show when quality is achieved or violated.
:bulb: Mini-experiment: 30 minutes to align on quality with the team — and you're already a step ahead."""
    )

    assert "*Quality Engineering Challenges in 2025" in result
    assert "Challenge 1" in result
    assert ":brain:" in result

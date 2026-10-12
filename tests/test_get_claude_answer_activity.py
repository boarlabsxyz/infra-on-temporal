import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from activities.telegram_to_slack_activities.claude_translate import (
    get_claude_answer_activity
)

pytestmark = pytest.mark.asyncio


def mock_openrouter_response(text: str):
    """Create a mock OpenRouter (OpenAI-compatible) completion with the given text."""
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=text))]
    return mock_completion


def mock_openrouter_client(*responses):
    """Create a mock AsyncOpenAI client returning the given completions in order."""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=list(responses))
    return mock_client


@patch("openai.AsyncOpenAI")
async def test_invalid_message_is_filtered(mock_openai):
    """Verify that messages flagged as INVALID by the LLM return an empty string."""
    # Validation call → INVALID
    mock_openai.return_value = mock_openrouter_client(
        mock_openrouter_response("INVALID")
    )

    result = await get_claude_answer_activity("Buy cheap crypto now!!!")

    assert result == ""


@patch("openai.AsyncOpenAI")
async def test_valid_message_is_processed(mock_openai):
    """Verify that valid messages are translated and returned with Slack formatting."""
    validation_response = mock_openrouter_response("VALID")
    formatted_response = mock_openrouter_response(
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

    mock_openai.return_value = mock_openrouter_client(
        validation_response,
        formatted_response,
    )

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

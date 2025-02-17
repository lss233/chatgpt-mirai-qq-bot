from datetime import datetime
from unittest.mock import MagicMock

import pytest

from framework.im.message import IMMessage, TextMessage
from framework.im.sender import ChatSender
from framework.llm.format.response import Message
from framework.memory.composes import DefaultMemoryComposer, DefaultMemoryDecomposer


@pytest.fixture
def composer():
    return DefaultMemoryComposer()


@pytest.fixture
def decomposer():
    return DefaultMemoryDecomposer()


@pytest.fixture
def group_sender():
    return ChatSender.from_group_chat(
        user_id="user1", group_id="group1", display_name="user1"
    )


@pytest.fixture
def c2c_sender():
    return ChatSender.from_c2c_chat(user_id="user1", display_name="user1")


class TestDefaultMemoryComposer:
    def test_compose_group_message(self, composer, group_sender):
        message = IMMessage(
            sender=group_sender,
            message_elements=[TextMessage(text="test message")],
        )

        entry = composer.compose(group_sender, [message])

        assert f"{group_sender.display_name} 说: {message.content}" in entry.content
        assert isinstance(entry.timestamp, datetime)

    def test_compose_c2c_message(self, composer, c2c_sender):
        message = IMMessage(
            sender=c2c_sender,
            message_elements=[TextMessage(text="test message")],
        )

        entry = composer.compose(c2c_sender, [message])

        assert f"{c2c_sender.display_name} 说: {message.content}" in entry.content
        assert isinstance(entry.timestamp, datetime)

    def test_compose_llm_response(self, composer, c2c_sender):
        chat_message = Message(role="assistant", content="test response")

        entry = composer.compose(c2c_sender, [chat_message])

        assert f"<@LLM> 说: {chat_message.content}" in entry.content
        assert isinstance(entry.timestamp, datetime)


class TestDefaultMemoryDecomposer:
    def test_decompose_mixed_entries(self, decomposer, group_sender, c2c_sender):
        entries = [
            MagicMock(
                sender=group_sender,
                content="group1:user1 说: group message",
                timestamp=datetime.now(),
            ),
            MagicMock(
                sender=c2c_sender,
                content="c2c:user1 说: c2c message",
                timestamp=datetime.now(),
            ),
        ]

        result = decomposer.decompose(entries)

        assert len(result.split("\n")) == 2
        assert "刚刚" in result
        assert "group message" in result
        assert "c2c message" in result

    def test_decompose_empty(self, decomposer):
        result = decomposer.decompose([])
        assert result == decomposer.empty_message

    def test_decompose_max_entries(self, decomposer, c2c_sender):
        # 创建超过10条的记录
        entries = [
            MagicMock(
                sender=c2c_sender, content=f"message {i}", timestamp=datetime.now()
            )
            for i in range(12)
        ]

        result = decomposer.decompose(entries)
        result_lines = result.split("\n")

        # 验证只返回最后10条
        assert len(result_lines) == 10
        assert "message 11" in result_lines[-1]

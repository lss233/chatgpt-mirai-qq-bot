import pytest
from datetime import datetime
from unittest.mock import MagicMock

from framework.llm.format.message import LLMChatMessage
from framework.memory.composes import DefaultMemoryComposer, DefaultMemoryDecomposer
from framework.im.sender import ChatSender, ChatType
from framework.im.message import IMMessage, TextMessage
from framework.llm.format.response import LLMChatResponse, LLMChatResponseContent, Usage, Message

@pytest.fixture
def composer():
    return DefaultMemoryComposer()

@pytest.fixture
def decomposer():
    return DefaultMemoryDecomposer()

@pytest.fixture
def group_sender():
    return ChatSender.from_group_chat(
        user_id="user1",
        group_id="group1"
    )

@pytest.fixture
def c2c_sender():
    return ChatSender.from_c2c_chat(
        user_id="user1"
    )

class TestDefaultMemoryComposer:
    def test_compose_group_message(self, composer, group_sender):
        message = IMMessage(
            sender=group_sender,
            message_elements=[TextMessage(text="test message")],
        )
        
        entry = composer.compose(message)
        
        assert entry.sender == group_sender
        assert entry.content == "test message"
        assert isinstance(entry.timestamp, datetime)
        assert entry.metadata == {"type": "text"}
        
    def test_compose_c2c_message(self, composer, c2c_sender):
        message = IMMessage(
            sender=c2c_sender,
            message_elements=[TextMessage(text="test message")],
        )
        
        entry = composer.compose(message)
        
        assert entry.sender == c2c_sender
        assert entry.content == "test message"
        assert isinstance(entry.timestamp, datetime)
        assert entry.metadata == {"type": "text"}
        
    def test_compose_llm_response(self, composer):
        chat_message = LLMChatMessage(role="assistant", content="test response")
        response = LLMChatResponse(
            choices=[LLMChatResponseContent(
                message=Message(
                    content=chat_message.content,
                    role=chat_message.role
                )
            )],
            usage=Usage(
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30
            )
        )
        
        entry = composer.compose(response)
        
        assert entry.sender.user_id == "assistant"
        assert entry.sender.chat_type == ChatType.C2C
        assert entry.content == "test response"
        assert isinstance(entry.timestamp, datetime)
        assert entry.metadata == {"type": "llm_response"}

class TestDefaultMemoryDecomposer:
    def test_decompose_mixed_entries(self, decomposer, group_sender, c2c_sender):
        entries = [
            MagicMock(
                sender=group_sender,
                content="group message",
                timestamp=datetime(2024, 1, 1, 12, 0)
            ),
            MagicMock(
                sender=c2c_sender,
                content="c2c message",
                timestamp=datetime(2024, 1, 1, 12, 1)
            )
        ]
        
        result = decomposer.decompose(entries)
        
        expected_lines = [
            "[2024-01-01 12:00:00] group1:user1: group message",
            "[2024-01-01 12:01:00] c2c:user1: c2c message"
        ]
        assert result == "\n".join(expected_lines)
        
    def test_decompose_empty(self, decomposer):
        result = decomposer.decompose([])
        assert result == ""
        
    def test_decompose_max_entries(self, decomposer, c2c_sender):
        # 创建超过5条的记录
        entries = [
            MagicMock(
                sender=c2c_sender,
                content=f"message {i}",
                timestamp=datetime(2024, 1, 1, 12, i)
            )
            for i in range(7)
        ]
        
        result = decomposer.decompose(entries)
        result_lines = result.split("\n")
        
        # 验证只返回最后5条
        assert len(result_lines) == 5
        assert "message 6" in result_lines[-1] 
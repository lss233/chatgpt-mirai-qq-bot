import pytest

from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.llm.format.response import LLMChatResponse
from kirara_ai.workflow.implementations.blocks.llm.basic import LLMResponseToText


@pytest.fixture
def container():
    """创建一个依赖容器"""
    return DependencyContainer()


def test_llm_response_to_text():
    """测试 LLM 响应转文本块"""
    # 创建一个模拟的 LLMChatResponse
    chat_response = LLMChatResponse(
        choices=[
            {
                "message": {
                    "content": "这是 AI 的回复",
                    "role": "assistant"
                }
            }
        ],
        model="gpt-3.5-turbo",
        usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    )
    
    # 创建块
    block = LLMResponseToText()
    
    # 执行块
    result = block.execute(response=chat_response)
    
    # 验证结果
    assert "text" in result
    assert result["text"] == "这是 AI 的回复"
    
    # 测试空响应
    empty_response = LLMChatResponse(
        choices=[
            {
                "message": {
                    "content": "",
                    "role": "assistant"
                }
            }
        ],
        model="gpt-3.5-turbo",
        usage={"prompt_tokens": 5, "completion_tokens": 0, "total_tokens": 5}
    )
    
    result = block.execute(response=empty_response)
    assert result["text"] == "" 
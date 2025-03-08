import pytest

from kirara_ai.im.message import IMMessage, TextMessage
from kirara_ai.im.sender import ChatSender
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.workflow.implementations.blocks.game.gacha import GachaSimulator


@pytest.fixture
def container():
    """创建一个依赖容器"""
    return DependencyContainer()


@pytest.fixture
def create_message():
    def _create(content: str) -> IMMessage:
        return IMMessage(
            sender=ChatSender.from_c2c_chat(user_id="test_user", display_name="Test User"),
            message_elements=[TextMessage(content)]
        )

    return _create


def test_gacha_single_pull(container, create_message):
    """测试单次抽卡"""
    block = GachaSimulator()
    block.container = container
    result = block.execute(create_message("单抽"))

    assert "response" in result
    response = result["response"]
    assert isinstance(response, IMMessage)
    assert "抽卡结果" in response.content or "⭐" in response.content
    # 不检查具体格式，只检查是否包含关键信息


def test_gacha_ten_pull(container, create_message):
    """测试十连抽卡"""
    block = GachaSimulator()
    block.container = container
    result = block.execute(create_message("十连"))

    assert "response" in result
    response = result["response"]
    assert isinstance(response, IMMessage)
    # 不检查具体格式，只检查是否包含关键信息
    assert "SSR" in response.content or "SR" in response.content or "R" in response.content


def test_gacha_custom_rates(container, create_message):
    """测试自定义概率的抽卡"""
    rates = {"SSR": 1.0, "SR": 0.0, "R": 0.0}  # 100% SSR
    block = GachaSimulator(rates)
    block.container = container
    result = block.execute(create_message("单抽"))

    assert "response" in result
    response = result["response"]
    assert isinstance(response, IMMessage)
    assert "SSR" in response.content

import pytest
from unittest.mock import MagicMock
from framework.workflows.blocks.game.dice import DiceRoll
from framework.workflows.blocks.game.gacha import GachaSimulator
from framework.ioc.container import DependencyContainer
from framework.im.message import IMMessage, TextMessage

@pytest.fixture
def container():
    return MagicMock(spec=DependencyContainer)

@pytest.fixture
def create_message():
    def _create(content: str) -> IMMessage:
        return IMMessage(
            sender="test_user",
            message_elements=[TextMessage(content)]
        )
    return _create

def test_dice_roll_basic(container, create_message):
    """测试基本的骰子命令"""
    block = DiceRoll(container)
    result = block.execute(create_message(".roll 2d6"))
    
    assert "response" in result
    response = result["response"]
    assert isinstance(response, IMMessage)
    assert response.sender == "<@bot>"
    assert len(response.message_elements) == 1
    assert "掷出了 2d6" in response.content

def test_dice_roll_invalid(container, create_message):
    """测试无效的骰子命令"""
    block = DiceRoll(container)
    result = block.execute(create_message("invalid command"))
    
    assert "response" in result
    response = result["response"]
    assert isinstance(response, IMMessage)
    assert "Invalid dice command" in response.content

def test_dice_roll_too_many(container, create_message):
    """测试超过限制的骰子数量"""
    block = DiceRoll(container)
    result = block.execute(create_message(".roll 101d6"))
    
    assert "response" in result
    response = result["response"]
    assert isinstance(response, IMMessage)
    assert "Too many dice" in response.content

def test_gacha_single_pull(container, create_message):
    """测试单次抽卡"""
    block = GachaSimulator(container)
    result = block.execute(create_message("单抽"))
    
    assert "response" in result
    response = result["response"]
    assert isinstance(response, IMMessage)
    assert "抽卡结果" in response.content
    # 检查是否只有一个结果
    result_text = response.content
    assert len(result_text.split("、")) == 1

def test_gacha_ten_pull(container, create_message):
    """测试十连抽卡"""
    block = GachaSimulator(container)
    result = block.execute(create_message("十连"))
    
    assert "response" in result
    response = result["response"]
    assert isinstance(response, IMMessage)
    # 检查是否有十个结果
    result_text = response.content
    assert len(result_text.split("、")) == 10

def test_gacha_custom_rates(container, create_message):
    """测试自定义概率的抽卡"""
    rates = {
        "SSR": 1.0,  # 100% SSR
        "SR": 0.0,
        "R": 0.0
    }
    block = GachaSimulator(container, rates=rates)
    result = block.execute(create_message("单抽"))
    
    assert "response" in result
    response = result["response"]
    assert isinstance(response, IMMessage)
    assert "SSR" in response.content 
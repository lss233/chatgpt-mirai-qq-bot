import re
from datetime import datetime
from unittest.mock import patch

import pytest

from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.workflow.implementations.blocks.system.basic import (CurrentTimeBlock, TextBlock, TextConcatBlock,
                                                                    TextExtractByRegexBlock, TextReplaceBlock)


@pytest.fixture
def container():
    """创建一个实际的依赖容器"""
    return DependencyContainer()


def test_text_block():
    """测试基础文本块"""
    # 创建一个文本块
    block = TextBlock(text="测试文本")
    
    # 执行块
    result = block.execute()
    
    # 验证结果
    assert "text" in result
    assert result["text"] == "测试文本"


def test_text_concat_block():
    """测试文本拼接块"""
    # 创建一个文本拼接块
    block = TextConcatBlock()
    
    # 执行块
    result = block.execute(text1="Hello, ", text2="World!")
    
    # 验证结果
    assert "text" in result
    assert result["text"] == "Hello, World!"


def test_text_replace_block():
    """测试文本替换块"""
    # 创建一个文本替换块
    block = TextReplaceBlock(variable="{name}")
    
    # 执行块
    result = block.execute(text="Hello, {name}!", new_text="ChatGPT")
    
    # 验证结果
    assert "text" in result
    assert result["text"] == "Hello, ChatGPT!"
    
    # 测试非字符串替换
    result = block.execute(text="Count: {name}", new_text=42)
    assert result["text"] == "Count: 42"


def test_text_extract_by_regex_block():
    """测试正则表达式提取块"""
    # 创建一个正则表达式提取块
    block = TextExtractByRegexBlock(regex=r"用户名：(\w+)")
    
    # 执行块 - 匹配成功
    result = block.execute(text="用户信息 - 用户名：testuser, 年龄：25")
    
    # 验证结果
    assert "text" in result
    assert result["text"] == "testuser"
    
    # 执行块 - 匹配失败
    result = block.execute(text="没有用户名信息")
    assert result["text"] == ""


def test_current_time_block():
    """测试当前时间块"""
    # 创建一个当前时间块
    block = CurrentTimeBlock()
    
    # 使用 patch 来模拟当前时间
    with patch('kirara_ai.workflow.implementations.blocks.system.basic.datetime') as mock_datetime:
        # 设置模拟的当前时间
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        
        # 执行块
        result = block.execute()
        
        # 验证结果
        assert "time" in result
        assert result["time"] == "2023-01-01 12:00:00"
    
    # 不使用 mock，测试实际时间格式
    result = block.execute()
    assert "time" in result
    # 验证时间格式
    time_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
    assert re.match(time_pattern, result["time"]) is not None 
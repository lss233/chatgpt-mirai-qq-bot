import asyncio
import base64
from unittest.mock import MagicMock, patch

import pytest

from kirara_ai.im.message import ImageMessage
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.workflow.implementations.blocks.llm.image import SimpleStableDiffusionWebUI


@pytest.fixture
def container():
    """创建一个带有模拟 requests 的容器"""
    container = DependencyContainer()
    
    # 模拟 event loop
    mock_loop = MagicMock(spec=asyncio.AbstractEventLoop)
    
    # 注册到容器
    container.register(asyncio.AbstractEventLoop, mock_loop)
    
    return container, mock_loop


def test_simple_stable_diffusion_webui(container):
    """测试简单 Stable Diffusion WebUI 块"""
    container, mock_loop = container
    
    # 创建一个简单的 base64 图像数据
    mock_image_data = base64.b64encode(b"mock_image_data").decode("utf-8")
    
    # 模拟 requests.post 的响应
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"images": [mock_image_data]}
    
    # 创建块 - 默认参数
    block = SimpleStableDiffusionWebUI(api_url="http://localhost:7860")
    block.container = container
    
    # 使用 patch 模拟 requests.post
    with patch('requests.post', return_value=mock_response):
        # 执行块
        result = block.execute(prompt="一只可爱的猫", negative_prompt="")
        
        # 验证结果
        assert "image" in result
        assert isinstance(result["image"], ImageMessage)
        
        # 创建块 - 自定义参数
        block = SimpleStableDiffusionWebUI(
            api_url="http://localhost:7860",
            steps=30,
            sampler_index="DPM++ 2M Karras",
            cfg_scale=8.0,
            width=768,
            height=512
        )
        block.container = container
        
        # 执行块
        result = block.execute(prompt="一只可爱的猫", negative_prompt="低质量, 模糊")
        
        # 验证结果
        assert "image" in result 
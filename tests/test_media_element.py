import os

import aiohttp
import pytest

from kirara_ai.im.message import MediaMessage

# 测试资源路径
TEST_RESOURCE_PATH = os.path.join(os.path.dirname(__file__), "resources", "test_image.txt")
TEST_URL = "https://httpbin.org/image/jpeg"  # 一个可用的测试图片URL

# 创建测试用的具体子类
class TestMediaMessage(MediaMessage):
    __test__ = False

    resource_type = "test"
    def to_plain(self):
        return "[TestMedia]"

@pytest.mark.asyncio
async def test_media_element_from_path():
    # 测试从文件路径初始化
    media = TestMediaMessage(path=TEST_RESOURCE_PATH)
    
    # 测试获取数据
    data = await media.get_data()
    assert data is not None
    assert isinstance(data, bytes)
    
    # 测试获取URL (data URL格式)
    url = await media.get_url()
    assert url.startswith("data:")
    assert "base64" in url
    
    # 测试获取路径
    path = await media.get_path()
    assert os.path.exists(path)
    assert os.path.isfile(path)

@pytest.mark.asyncio
async def test_media_element_from_url():
    # 测试从URL初始化
    media = TestMediaMessage(url=TEST_URL)
    
    # 测试获取数据
    data = await media.get_data()
    assert data is not None
    assert isinstance(data, bytes)
    
    # 测试获取原始URL
    url = await media.get_url()
    assert url == TEST_URL
    
    # 测试获取临时文件路径
    path = await media.get_path()
    assert os.path.exists(path)
    assert os.path.isfile(path)

@pytest.mark.asyncio
async def test_media_element_from_data():
    # 首先从文件读取一些测试数据
    with open(TEST_RESOURCE_PATH, "rb") as f:
        test_data = f.read()
    
    # 测试从二进制数据初始化
    media = TestMediaMessage(data=test_data, format="txt")
    
    # 测试获取数据
    data = await media.get_data()
    assert data == test_data
    
    # 测试获取URL (应该是data URL)
    url = await media.get_url()
    assert url.startswith("data:")
    assert "base64" in url
    
    # 测试获取临时文件路径
    path = await media.get_path()
    assert os.path.exists(path)
    assert os.path.isfile(path)

@pytest.mark.asyncio
async def test_media_element_format_detection():
    # 测试格式自动检测
    media = TestMediaMessage(path=TEST_RESOURCE_PATH)
    await media.get_data()  # 触发格式检测
    assert media.format is not None
    assert media.resource_type is not None

@pytest.mark.asyncio
async def test_media_element_errors():
    # 测试错误情况
    with pytest.raises(ValueError):
        TestMediaMessage()  # 没有提供任何参数
        
    with pytest.raises(ValueError):
        TestMediaMessage(data=b"test")  # 提供数据但没有格式
        
    with pytest.raises(aiohttp.ClientError):
        media = TestMediaMessage(url="https://invalid-url-that-does-not-exist.com/image.jpg")
        await media.get_data()  # 无效的URL 
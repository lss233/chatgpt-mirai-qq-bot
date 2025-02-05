# 插件 API 🔌

插件 API 提供了管理插件的功能。插件可以扩展系统的功能，添加新的区块类型、适配器或工作流。

## API 端点

### 获取插件详情

```http
GET /api/plugin/{plugin_name}
```

获取指定插件的详细信息。

**响应示例：**
```json
{
  "plugin": {
    "name": "image-processing",
    "package_name": "chatgpt-mirai-plugin-image",
    "description": "图像处理插件",
    "version": "1.0.0",
    "author": "Plugin Author",
    "is_internal": false,
    "is_enabled": true,
    "metadata": {
      "homepage": "https://github.com/author/plugin",
      "license": "MIT"
    }
  }
}
```

### 更新插件

```http
POST /api/plugin/update/{plugin_name}
```

更新指定的外部插件到最新版本。注意：内部插件不支持更新。

**响应示例：**
```json
{
  "plugin": {
    "name": "image-processing",
    "package_name": "chatgpt-mirai-plugin-image",
    "description": "图像处理插件",
    "version": "1.1.0",  // 更新后的版本
    "author": "Plugin Author",
    "is_internal": false,
    "is_enabled": true,
    "metadata": {
      "homepage": "https://github.com/author/plugin",
      "license": "MIT"
    }
  }
}
```

## 数据模型

### PluginInfo
- `name`: 插件名称
- `package_name`: 包名(外部插件)
- `description`: 插件描述
- `version`: 版本号
- `author`: 作者
- `is_internal`: 是否为内部插件
- `is_enabled`: 是否启用
- `metadata`: 元数据(可选)

## 内置插件

### IM 适配器
- Telegram 适配器
- HTTP Legacy 适配器
- WeCom 适配器

### LLM 后端
- OpenAI 适配器
- Anthropic 适配器
- Google AI 适配器

## 相关代码

- [插件基类](../../../plugin_manager/plugin.py)
- [插件加载器](../../../plugin_manager/plugin_loader.py)
- [插件事件总线](../../../plugin_manager/plugin_event_bus.py)
- [内置插件](../../../../plugins)

## 错误处理

所有 API 端点在发生错误时都会返回适当的 HTTP 状态码和错误信息：

```json
{
  "error": "错误描述信息"
}
```

常见状态码：
- 400: 请求参数错误或插件不支持更新
- 404: 插件不存在
- 500: 服务器内部错误

## 使用示例

### 获取插件信息
```python
import requests

response = requests.get(
    'http://localhost:8080/api/plugin/image-processing',
    headers={'Authorization': f'Bearer {token}'}
)
```

### 更新插件
```python
import requests

response = requests.post(
    'http://localhost:8080/api/plugin/update/image-processing',
    headers={'Authorization': f'Bearer {token}'}
)
```

## 相关文档

- [插件系统概述](../../README.md#插件系统-)
- [插件开发指南](../../../plugin_manager/README.md#插件开发)
- [API 认证](../../README.md#api认证-) 
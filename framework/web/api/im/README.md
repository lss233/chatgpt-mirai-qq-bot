# 即时通讯 API 🗨️

即时通讯 API 提供了管理 IM 后端和适配器的功能。通过这些 API，你可以注册、配置和管理不同的 IM 平台适配器。

## API 端点

### 获取适配器类型

```http
GET/backend-api/api/im/types
```

获取所有可用的 IM 适配器类型。

**响应示例：**
```json
{
  "types": [
    "mirai",
    "telegram",
    "discord"
  ]
}
```

### 获取所有适配器

```http
GET/backend-api/api/im/adapters
```

获取所有已配置的 IM 适配器信息。

**响应示例：**
```json
{
  "adapters": [
    {
      "name": "telegram",
      "adapter": "telegram",
      "config": {
        "token": "your-bot-token",
      },
      "is_running": true
    }

  ]
}
```

### 获取特定适配器

```http
GET/backend-api/api/im/adapters/{adapter_id}
```

获取指定适配器的详细信息。

**响应示例：**
```json
{
  "adapter": {
    "name": "telegram",
    "adapter": "telegram",
    "config": {
      "token": "your-bot-token",
    },
    "is_running": true

  }
}
```

### 创建适配器

```http
POST/backend-api/api/im/adapters
```

注册新的 IM 适配器。

**请求体：**
```json
{
  "name": "telegram",
  "adapter": "telegram",
  "config": {
    "token": "your-bot-token",
  }
}
```


### 更新适配器

```http
PUT/backend-api/api/im/adapters/{adapter_id}
```

更新现有适配器的配置。如果适配器正在运行，会自动重启以应用新配置。

**请求体：**
```json
{
  "name": "telegram",
  "adapter": "telegram",
  "config": {
    "token": "your-bot-token",
  }


}
```

### 删除适配器

```http
DELETE/backend-api/api/im/adapters/{adapter_id}
```

删除指定的适配器。如果适配器正在运行，会先自动停止。

### 启动适配器

```http
POST/backend-api/api/im/adapters/{adapter_id}/start
```

启动指定的适配器。

### 停止适配器

```http
POST/backend-api/api/im/adapters/{adapter_id}/stop
```

停止指定的适配器。

### 获取适配器配置模式

```http
GET/backend-api/api/im/types/{adapter_type}/config-schema
```

获取指定适配器类型的配置字段模式。

**响应示例：**
```json
{
  "schema": {
    "title": "TelegramConfig",
    "type": "object",
    "properties": {
      "token": {
        "title": "Bot Token",
        "type": "string",
        "description": "Telegram Bot Token"
      }
    },
    "required": ["token"]
  }
}
```

## 数据模型

### IMAdapterConfig
- `name`: 适配器名称
- `adapter`: 适配器类型
- `config`: 配置信息(字典)

### IMAdapterStatus
继承自 IMAdapterConfig，额外包含：
- `is_running`: 适配器是否正在运行

### IMAdapterList
- `adapters`: IM 适配器列表

### IMAdapterResponse
- `adapter`: 适配器信息

### IMAdapterTypes
- `types`: 可用的适配器类型列表

### IMAdapterConfigSchema
- `error`: 错误信息(可选)
- `schema`: JSON Schema 格式的配置字段描述

## 适配器类型

适配器由插件提供，见[适配器实现](../../../im/adapters)。

## 相关代码

- [IM 管理器](../../../im/manager.py)
- [IM 注册表](../../../im/im_registry.py)
- [适配器实现](../../../im/adapters)

## 错误处理

所有 API 端点在发生错误时都会返回适当的 HTTP 状态码和错误信息：

```json
{
  "error": "错误描述信息"
}
```

常见状态码：
- 400: 请求参数错误、适配器类型无效或适配器已在运行
- 404: 适配器不存在
- 500: 服务器内部错误

## 使用示例

### 获取适配器类型
```python
import requests

response = requests.get(
    'http://localhost:8080/api/im/types',
    headers={'Authorization': f'Bearer {token}'}
)
```

### 创建新适配器
```python
import requests

adapter_data = {
    "name": "telegram",
    "adapter": "telegram",
    "config": {
        "token": "your-bot-token",
        "webhook_url": "https://example.com/webhook"
    }
}

response = requests.post(
    'http://localhost:8080/api/im/adapters',
    headers={'Authorization': f'Bearer {token}'},
    json=adapter_data
)
```

### 启动适配器
```python
import requests

response = requests.post(
    'http://localhost:8080/api/im/adapters/telegram/start',
    headers={'Authorization': f'Bearer {token}'}
)
```

## 相关文档

- [系统架构](../../README.md#系统架构-)
- [API 认证](../../README.md#api认证-)
- [IM 适配器开发](../../../im/README.md#适配器开发-) 
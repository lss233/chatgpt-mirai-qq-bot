# IM Adapter Management API

本文档描述了 IM 适配器管理的 API 接口。所有接口都需要认证，请在请求头中添加 `Authorization: Bearer <token>` 。

## 获取适配器类型

获取所有可用的 IM 适配器类型。

```
GET /api/im/types
```

### 响应

```json
{
    "types": ["telegram", "http_legacy", "wechat"]
}
```

## 获取适配器列表

获取所有已配置的 IM 适配器。

```
GET /api/im/adapters
```

### 响应

```json
{
    "adapters": [
        {
            "adapter_id": "telegram-bot-1234",
            "adapter_type": "telegram",
            "is_running": true,
            "configs": {
                "token": "your-bot-token"
            }
        }
    ]
}
```

## 获取单个适配器

获取特定适配器的详细信息。

```
GET /api/im/adapters/{adapter_id}
```

### 响应

```json
{
    "adapter": {
        "adapter_id": "telegram-bot-1234",
        "adapter_type": "telegram",
        "is_running": true,
        "configs": {
            "token": "your-bot-token"
        }
    }
}
```

## 创建适配器

创建新的 IM 适配器。

```
POST /api/im/adapters
```

### 请求体

```json
{
    "adapter_id": "telegram-bot-1234",
    "adapter_type": "telegram",
    "configs": {
        "token": "your-bot-token"
    }
}
```

### 响应

```json
{
    "adapter": {
        "adapter_id": "telegram-bot-1234",
        "adapter_type": "telegram",
        "is_running": false,
        "configs": {
            "token": "your-bot-token"
        }
    }
}
```

## 更新适配器

更新现有适配器的配置。

```
PUT /api/im/adapters/{adapter_id}
```

### 请求体

```json
{
    "adapter_id": "telegram-bot-1234",
    "adapter_type": "telegram",
    "configs": {
        "token": "new-bot-token"
    }
}
```

### 响应

```json
{
    "adapter": {
        "adapter_id": "telegram-bot-1234",
        "adapter_type": "telegram",
        "is_running": true,
        "configs": {
            "token": "new-bot-token"
        }
    }
}
```

## 删除适配器

删除指定的适配器。

```
DELETE /api/im/adapters/{adapter_id}
```

### 响应

```json
{
    "message": "Adapter deleted successfully"
}
```

## 启动适配器

启动指定的适配器。

```
POST /api/im/adapters/{adapter_id}/start
```

### 响应

```json
{
    "message": "Adapter started successfully"
}
```

## 停止适配器

停止指定的适配器。

```
POST /api/im/adapters/{adapter_id}/stop
```

### 响应

```json
{
    "message": "Adapter stopped successfully"
}
```

## 错误响应

所有接口在发生错误时都会返回相应的错误信息：

```json
{
    "error": "错误信息"
}
```

常见的错误状态码：
- 400: 请求参数错误
- 401: 未认证或认证失败
- 404: 资源不存在
- 500: 服务器内部错误 
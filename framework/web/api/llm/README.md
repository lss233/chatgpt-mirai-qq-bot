# LLM Backend Management API

本文档描述了 LLM 后端管理的 API 接口。所有接口都需要认证，请在请求头中添加 `Authorization: Bearer <token>` 。

## 获取适配器类型

获取所有可用的 LLM 适配器类型。

```
GET /api/llm/types
```

### 响应

```json
{
    "types": ["openai", "gemini", "anthropic"]
}
```

## 获取后端列表

获取所有已配置的 LLM 后端。

```
GET /api/llm/backends
```

### 响应

```json
{
    "backends": [
        {
            "backend_id": "openai-gpt4",
            "adapter": "openai",
            "enable": true,
            "configs": [
                {
                    "api_key": "your-api-key",
                    "base_url": "https://api.openai.com/v1"
                }
            ],
            "models": ["gpt-4", "gpt-4-turbo"],
            "is_available": true
        }
    ]
}
```

## 获取单个后端

获取特定 LLM 后端的详细信息。

```
GET /api/llm/backends/{backend_id}
```

### 响应

```json
{
    "backend": {
        "backend_id": "openai-gpt4",
        "adapter": "openai",
        "enable": true,
        "configs": [
            {
                "api_key": "your-api-key",
                "base_url": "https://api.openai.com/v1"
            }
        ],
        "models": ["gpt-4", "gpt-4-turbo"],
        "is_available": true
    }
}
```

## 创建后端

创建新的 LLM 后端。

```
POST /api/llm/backends
```

### 请求体

```json
{
    "backend_id": "openai-gpt4",
    "adapter": "openai",
    "enable": true,
    "configs": [
        {
            "api_key": "your-api-key",
            "base_url": "https://api.openai.com/v1"
        }
    ],
    "models": ["gpt-4", "gpt-4-turbo"]
}
```

### 响应

```json
{
    "backend": {
        "backend_id": "openai-gpt4",
        "adapter": "openai",
        "enable": true,
        "configs": [
            {
                "api_key": "your-api-key",
                "base_url": "https://api.openai.com/v1"
            }
        ],
        "models": ["gpt-4", "gpt-4-turbo"],
        "is_available": false
    }
}
```

## 更新后端

更新现有 LLM 后端的配置。

```
PUT /api/llm/backends/{backend_id}
```

### 请求体

```json
{
    "backend_id": "openai-gpt4",
    "adapter": "openai",
    "enable": true,
    "configs": [
        {
            "api_key": "new-api-key",
            "base_url": "https://api.openai.com/v1"
        }
    ],
    "models": ["gpt-4", "gpt-4-turbo"]
}
```

### 响应

```json
{
    "backend": {
        "backend_id": "openai-gpt4",
        "adapter": "openai",
        "enable": true,
        "configs": [
            {
                "api_key": "new-api-key",
                "base_url": "https://api.openai.com/v1"
            }
        ],
        "models": ["gpt-4", "gpt-4-turbo"],
        "is_available": true
    }
}
```

## 删除后端

删除指定的 LLM 后端。

```
DELETE /api/llm/backends/{backend_id}
```

### 响应

```json
{
    "message": "Backend deleted successfully"
}
```

## 启用后端

启用指定的 LLM 后端。

```
POST /api/llm/backends/{backend_id}/enable
```

### 响应

```json
{
    "message": "Backend enabled successfully"
}
```

## 禁用后端

禁用指定的 LLM 后端。

```
POST /api/llm/backends/{backend_id}/disable
```

### 响应

```json
{
    "message": "Backend disabled successfully"
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
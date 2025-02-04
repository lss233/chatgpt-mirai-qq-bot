# Dispatch Rule Management API

本文档描述了调度规则管理的 API 接口。所有接口都需要认证，请在请求头中添加 `Authorization: Bearer <token>` 。

## 获取规则列表

获取所有已配置的调度规则。规则按优先级降序排列。

```
GET /api/dispatch/rules
```

### 响应

```json
{
    "rules": [
        {
            "rule_id": "chat-rule",
            "name": "聊天规则",
            "description": "处理普通聊天消息",
            "pattern": ".*",
            "priority": 0,
            "workflow_id": "chat-workflow",
            "enabled": true,
            "metadata": {
                "created_by": "system"
            },
            "is_active": true
        }
    ]
}
```

## 获取单个规则

获取特定调度规则的详细信息。

```
GET /api/dispatch/rules/{rule_id}
```

### 响应

```json
{
    "rule": {
        "rule_id": "chat-rule",
        "name": "聊天规则",
        "description": "处理普通聊天消息",
        "pattern": ".*",
        "priority": 0,
        "workflow_id": "chat-workflow",
        "enabled": true,
        "metadata": {
            "created_by": "system"
        },
        "is_active": true
    }
}
```

## 创建规则

创建新的调度规则。

```
POST /api/dispatch/rules
```

### 请求体

```json
{
    "rule_id": "chat-rule",
    "name": "聊天规则",
    "description": "处理普通聊天消息",
    "pattern": ".*",
    "priority": 0,
    "workflow_id": "chat-workflow",
    "enabled": true,
    "metadata": {
        "created_by": "system"
    }
}
```

### 响应

```json
{
    "rule": {
        "rule_id": "chat-rule",
        "name": "聊天规则",
        "description": "处理普通聊天消息",
        "pattern": ".*",
        "priority": 0,
        "workflow_id": "chat-workflow",
        "enabled": true,
        "metadata": {
            "created_by": "system"
        },
        "is_active": true
    }
}
```

## 更新规则

更新现有调度规则的配置。

```
PUT /api/dispatch/rules/{rule_id}
```

### 请求体

```json
{
    "rule_id": "chat-rule",
    "name": "聊天规则",
    "description": "处理普通聊天消息",
    "pattern": "^/chat",
    "priority": 1,
    "workflow_id": "chat-workflow",
    "enabled": true,
    "metadata": {
        "created_by": "system",
        "updated_at": "2024-02-04"
    }
}
```

### 响应

```json
{
    "rule": {
        "rule_id": "chat-rule",
        "name": "聊天规则",
        "description": "处理普通聊天消息",
        "pattern": "^/chat",
        "priority": 1,
        "workflow_id": "chat-workflow",
        "enabled": true,
        "metadata": {
            "created_by": "system",
            "updated_at": "2024-02-04"
        },
        "is_active": true
    }
}
```

## 删除规则

删除指定的调度规则。

```
DELETE /api/dispatch/rules/{rule_id}
```

### 响应

```json
{
    "message": "Rule deleted successfully"
}
```

## 启用规则

启用指定的调度规则。

```
POST /api/dispatch/rules/{rule_id}/enable
```

### 响应

```json
{
    "message": "Rule enabled successfully"
}
```

## 禁用规则

禁用指定的调度规则。

```
POST /api/dispatch/rules/{rule_id}/disable
```

### 响应

```json
{
    "message": "Rule disabled successfully"
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
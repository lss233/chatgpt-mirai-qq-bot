# 调度规则 API 📋

调度规则 API 提供了消息处理规则的管理功能。调度规则决定了如何根据消息内容选择合适的工作流进行处理。

## API 端点

### 获取规则列表

```http
GET /api/dispatch/rules
```

获取所有已配置的调度规则。

**响应示例：**
```json
{
  "rules": [
    {
      "rule_id": "chat_normal",
      "name": "普通聊天",
      "description": "普通聊天，使用默认参数",
      "pattern": "/chat",
      "priority": 5,
      "workflow_id": "chat:normal",
      "enabled": true,
      "metadata": {
        "category": "chat",
        "permission": "user",
        "temperature": 0.7
      },
      "is_active": true
    }
  ]
}
```

### 获取特定规则

```http
GET /api/dispatch/rules/{rule_id}
```

获取指定规则的详细信息。

### 创建规则

```http
POST /api/dispatch/rules
```

创建新的调度规则。

**请求体：**
```json
{
  "rule_id": "chat_creative",
  "name": "创意聊天",
  "description": "创意聊天，使用更高的温度参数",
  "type": "keyword",
  "workflow_id": "chat:creative",
  "keywords": ["创意", "发散", "brainstorm"],
  "priority": 5,
  "enabled": true,
  "metadata": {
    "category": "chat",
    "permission": "user",
    "temperature": 0.9
  }
}
```

### 更新规则

```http
PUT /api/dispatch/rules/{rule_id}
```

更新现有规则。

### 删除规则

```http
DELETE /api/dispatch/rules/{rule_id}
```

删除指定规则。

### 启用规则

```http
POST /api/dispatch/rules/{rule_id}/enable
```

启用指定规则。

### 禁用规则

```http
POST /api/dispatch/rules/{rule_id}/disable
```

禁用指定规则。

## 数据模型

### DispatchRuleConfig
- `rule_id`: 规则唯一标识符
- `name`: 规则名称
- `description`: 规则描述
- `type`: 规则类型 (prefix/keyword/regex)
- `workflow_id`: 关联的工作流ID
- `pattern`/`prefix`/`keywords`: 匹配规则(根据类型不同)
- `priority`: 优先级(数字越大优先级越高)
- `enabled`: 是否启用
- `metadata`: 元数据(可选)

### DispatchRuleStatus
继承自 DispatchRuleConfig，额外包含：
- `is_active`: 规则是否处于活动状态

## 规则类型

### 前缀匹配 (prefix)
根据消息前缀进行匹配，例如 "/help"。

### 关键词匹配 (keyword)
检查消息中是否包含指定关键词。

### 正则匹配 (regex)
使用正则表达式进行匹配，提供最灵活的匹配方式。

## 相关代码

- [调度规则定义](../../../workflow/core/dispatch/rule.py)
- [调度规则注册表](../../../workflow/core/dispatch/registry.py)
- [调度器实现](../../../workflow/core/dispatch/dispatcher.py)
- [系统预设规则](../../../../data/dispatch_rules)

## 错误处理

所有 API 端点在发生错误时都会返回适当的 HTTP 状态码和错误信息：

```json
{
  "error": "错误描述信息"
}
```

常见状态码：
- 400: 请求参数错误或规则配置无效
- 404: 规则不存在
- 409: 规则ID已存在
- 500: 服务器内部错误

## 使用示例

### 创建新规则
```python
import requests

rule_data = {
    "rule_id": "chat_creative",
    "name": "创意聊天",
    "description": "创意聊天模式",
    "type": "keyword",
    "workflow_id": "chat:creative",
    "keywords": ["创意", "发散"],
    "priority": 5,
    "enabled": True
}

response = requests.post(
    'http://localhost:8080/api/dispatch/rules',
    headers={'Authorization': f'Bearer {token}'},
    json=rule_data
)
```

### 更新规则优先级
```python
import requests

response = requests.put(
    'http://localhost:8080/api/dispatch/rules/chat_creative',
    headers={'Authorization': f'Bearer {token}'},
    json={"priority": 8}
)
```

## 相关文档

- [工作流系统概述](../../README.md#工作流系统-)
- [调度规则配置指南](../../../workflow/README.md#调度规则配置)
- [API 认证](../../README.md#api认证-) 
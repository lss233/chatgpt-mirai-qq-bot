# 工作流 API 🔄

工作流 API 提供了管理工作流的功能。工作流由多个区块组成，用于处理消息和执行任务。每个工作流都属于一个特定的组。

## API 端点

### 获取所有工作流

```http
GET /api/workflow
```

获取所有已注册的工作流基本信息。

**响应示例：**
```json
{
  "workflows": [
    {
      "group_id": "chat",
      "workflow_id": "normal",
      "name": "普通聊天",
      "description": "处理普通聊天消息的工作流",
      "block_count": 3,
      "metadata": {
        "category": "chat",
        "tags": ["normal", "chat"]
      }
    }
  ]
}
```

### 获取特定工作流

```http
GET /api/workflow/{group_id}/{workflow_id}
```

获取指定工作流的详细信息。

**响应示例：**
```json
{
  "workflow": {
    "group_id": "chat",
    "workflow_id": "normal",
    "name": "普通聊天",
    "description": "处理普通聊天消息的工作流",
    "blocks": [
      {
        "block_id": "input_1",
        "type_name": "MessageInputBlock",
        "name": "消息输入",
        "config": {
          "format": "text"
        },
        "position": {
          "x": 100,
          "y": 100
        }
      },
      {
        "block_id": "llm_1",
        "type_name": "LLMBlock",
        "name": "语言模型",
        "config": {
          "backend": "openai",
          "temperature": 0.7
        },
        "position": {
          "x": 300,
          "y": 100
        }
      },
      {
        "block_id": "output_1",
        "type_name": "MessageOutputBlock",
        "name": "消息输出",
        "config": {
          "format": "text"
        },
        "position": {
          "x": 500,
          "y": 100
        }
      }
    ],
    "wires": [
      {
        "source_block": "input_1",
        "source_output": "message",
        "target_block": "llm_1",
        "target_input": "prompt"
      },
      {
        "source_block": "llm_1",
        "source_output": "response",
        "target_block": "output_1",
        "target_input": "message"
      }
    ],
    "metadata": {
      "category": "chat",
      "tags": ["normal", "chat"]
    }
  }
}
```

### 创建工作流

```http
POST /api/workflow/{group_id}/{workflow_id}
```

创建新的工作流。

**请求体：**
```json
{
  "group_id": "chat",
  "workflow_id": "creative",
  "name": "创意聊天",
  "description": "处理创意聊天的工作流",
  "blocks": [
    {
      "block_id": "input_1",
      "type_name": "MessageInputBlock",
      "name": "消息输入",
      "config": {
        "format": "text"
      },
      "position": {
        "x": 100,
        "y": 100
      }
    },
    {
      "block_id": "prompt_1",
      "type_name": "PromptBlock",
      "name": "提示词处理",
      "config": {
        "template": "请发挥创意回答以下问题：{{input}}"
      },
      "position": {
        "x": 300,
        "y": 100
      }
    },
    {
      "block_id": "llm_1",
      "type_name": "LLMBlock",
      "name": "语言模型",
      "config": {
        "backend": "anthropic",
        "temperature": 0.9
      },
      "position": {
        "x": 500,
        "y": 100
      }
    }
  ],
  "wires": [
    {
      "source_block": "input_1",
      "source_output": "message",
      "target_block": "prompt_1",
      "target_input": "input"
    },
    {
      "source_block": "prompt_1",
      "source_output": "output",
      "target_block": "llm_1",
      "target_input": "prompt"
    }
  ],
  "metadata": {
    "category": "chat",
    "tags": ["creative", "chat"]
  }
}
```

### 更新工作流

```http
PUT /api/workflow/{group_id}/{workflow_id}
```

更新现有工作流。请求体格式与创建工作流相同。

### 删除工作流

```http
DELETE /api/workflow/{group_id}/{workflow_id}
```

删除指定工作流。成功时返回：

```json
{
  "message": "Workflow deleted successfully"
}
```

## 数据模型

### Wire (工作流连线)
- `source_block`: 源区块 ID
- `source_output`: 源区块输出端口
- `target_block`: 目标区块 ID
- `target_input`: 目标区块输入端口

### BlockInstance (区块实例)
- `block_id`: 区块 ID
- `type_name`: 区块类型名称
- `name`: 区块显示名称
- `config`: 区块配置
- `position`: 区块位置
  - `x`: X 坐标
  - `y`: Y 坐标

### WorkflowDefinition (工作流定义)
- `group_id`: 工作流组 ID
- `workflow_id`: 工作流 ID
- `name`: 工作流名称
- `description`: 工作流描述
- `blocks`: 区块列表
- `wires`: 连线列表
- `metadata`: 元数据(可选)

### WorkflowInfo (工作流信息)
- `group_id`: 工作流组 ID
- `workflow_id`: 工作流 ID
- `name`: 工作流名称
- `description`: 工作流描述
- `block_count`: 区块数量
- `metadata`: 元数据(可选)

### WorkflowList (工作流列表)
- `workflows`: 工作流信息列表

### WorkflowResponse (工作流响应)
- `workflow`: 工作流定义

## 区块类型

工作流中可以使用的区块类型包括：

### MessageInputBlock
- 功能：接收输入消息
- 输入：无
- 输出：
  - `message`: 消息内容
- 配置：
  - `format`: 消息格式(text/image/audio)

### MessageOutputBlock
- 功能：输出消息
- 输入：
  - `message`: 消息内容
- 输出：无
- 配置：
  - `format`: 消息格式(text/image/audio)

### LLMBlock
- 功能：调用大语言模型
- 输入：
  - `prompt`: 提示词
- 输出：
  - `response`: 模型响应
- 配置：
  - `backend`: 使用的后端
  - `temperature`: 温度参数

### PromptBlock
- 功能：处理提示词
- 输入：
  - `input`: 输入内容
- 输出：
  - `output`: 处理后的提示词
- 配置：
  - `template`: 提示词模板

## 相关代码

- [工作流注册表](../../../workflow/core/workflow/registry.py)
- [工作流构建器](../../../workflow/core/workflow/builder.py)
- [区块注册表](../../../workflow/core/block/registry.py)
- [系统预设工作流](../../../../data/workflows)

## 错误处理

所有 API 端点在发生错误时都会返回适当的 HTTP 状态码和错误信息：

```json
{
  "error": "错误描述信息"
}
```

常见状态码：
- 400: 请求参数错误、工作流配置无效或工作流已存在
- 404: 工作流不存在
- 500: 服务器内部错误

## 使用示例

### 获取所有工作流
```python
import requests

response = requests.get(
    'http://localhost:8080/api/workflow',
    headers={'Authorization': f'Bearer {token}'}
)
```

### 创建新工作流
```python
import requests

workflow_data = {
    "group_id": "chat",
    "workflow_id": "creative",
    "name": "创意聊天",
    "description": "处理创意聊天的工作流",
    "blocks": [
        {
            "block_id": "input_1",
            "type_name": "MessageInputBlock",
            "name": "消息输入",
            "config": {
                "format": "text"
            },
            "position": {
                "x": 100,
                "y": 100
            }
        },
        {
            "block_id": "llm_1",
            "type_name": "LLMBlock",
            "name": "语言模型",
            "config": {
                "backend": "anthropic",
                "temperature": 0.9
            },
            "position": {
                "x": 300,
                "y": 100
            }
        }
    ],
    "wires": [
        {
            "source_block": "input_1",
            "source_output": "message",
            "target_block": "llm_1",
            "target_input": "prompt"
        }
    ],
    "metadata": {
        "category": "chat",
        "tags": ["creative"]
    }
}

response = requests.post(
    'http://localhost:8080/api/workflow/chat/creative',
    headers={'Authorization': f'Bearer {token}'},
    json=workflow_data
)
```

### 删除工作流
```python
import requests

response = requests.delete(
    'http://localhost:8080/api/workflow/chat/creative',
    headers={'Authorization': f'Bearer {token}'}
)
```

## 相关文档

- [系统架构](../../README.md#系统架构-)
- [API 认证](../../README.md#api认证-)
- [工作流开发](../../../workflow/README.md#工作流开发-) 
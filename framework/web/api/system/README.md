# 系统状态 API

系统状态API提供了对系统运行状态的监控功能。

## API 端点

### 获取系统状态

```http
GET /api/system/status
```

获取系统的当前运行状态，包括运行时间、资源使用情况等信息。

**响应示例：**
```json
{
  "status": {
    "version": "1.0.0",
    "uptime": 3600.5,
    "active_adapters": 2,
    "active_backends": 3,
    "loaded_plugins": 5,
    "workflow_count": 10,
    "memory_usage": {
      "rss": 156.5,
      "vms": 512.3,
      "percent": 2.5
    },
    "cpu_usage": 1.2
  }
}
```

**响应字段说明：**
- `version`: 系统版本号
- `uptime`: 系统运行时间（秒）
- `active_adapters`: 当前活跃的IM适配器数量
- `active_backends`: 当前活跃的LLM后端数量
- `loaded_plugins`: 已加载的插件数量
- `workflow_count`: 已注册的工作流数量
- `memory_usage`: 内存使用情况
  - `rss`: 物理内存使用量（MB）
  - `vms`: 虚拟内存使用量（MB）
  - `percent`: 内存使用百分比
- `cpu_usage`: CPU使用百分比

## 错误处理

所有API端点在发生错误时都会返回适当的HTTP状态码和错误信息：

```json
{
  "error": "错误描述信息"
}
```

常见状态码：
- 401: 未认证或认证失败
- 500: 服务器内部错误 
# 插件 API 🔌

插件 API 提供了管理插件的功能。通过这些 API，你可以安装、卸载、启用、禁用和更新插件。

## API 端点

### 获取所有插件

```http
GET /api/plugin/plugins
```

获取所有已安装的插件列表。

**响应示例：**
```json
{
  "plugins": [
    {
      "name": "图像处理",
      "package_name": "image-processing",
      "description": "提供图像处理功能",
      "version": "1.0.0",
      "author": "开发者",
      "homepage": "https://github.com/example/image-processing",
      "license": "MIT",
      "is_internal": false,
      "is_enabled": true,
      "metadata": {
        "category": "media",
        "tags": ["image", "processing"]
      }
    }
  ]
}
```

### 获取特定插件

```http
GET /api/plugin/plugins/{plugin_name}
```

获取指定插件的详细信息。

**响应示例：**
```json
{
  "plugin": {
    "name": "图像处理",
    "package_name": "image-processing",
    "description": "提供图像处理功能",
    "version": "1.0.0",
    "author": "开发者",
    "homepage": "https://github.com/example/image-processing",
    "license": "MIT",
    "is_internal": false,
    "is_enabled": true,
    "metadata": {
      "category": "media",
      "tags": ["image", "processing"]
    }
  }
}
```

### 安装插件

```http
POST /api/plugin/plugins
```

安装新的插件。

**请求体：**
```json
{
  "package_name": "image-processing",
  "version": "1.0.0"  // 可选，不指定则安装最新版本
}
```

### 卸载插件

```http
DELETE /api/plugin/plugins/{plugin_name}
```

卸载指定的插件。注意：内部插件不能被卸载。

### 启用插件

```http
POST /api/plugin/plugins/{plugin_name}/enable
```

启用指定的插件。

### 禁用插件

```http
POST /api/plugin/plugins/{plugin_name}/disable
```

禁用指定的插件。

### 更新插件

```http
PUT /api/plugin/plugins/{plugin_name}
```

更新插件到最新版本。注意：内部插件不支持更新。

## 数据模型

### PluginInfo
- `name`: 插件名称
- `package_name`: 包名
- `description`: 描述
- `version`: 版本号
- `author`: 作者
- `homepage`: 主页(可选)
- `license`: 许可证(可选)
- `is_internal`: 是否为内部插件
- `is_enabled`: 是否已启用
- `metadata`: 元数据(可选)

### InstallPluginRequest
- `package_name`: 包名
- `version`: 版本号(可选)

### PluginList
- `plugins`: 插件列表

### PluginResponse
- `plugin`: 插件信息

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

- [插件管理器](../../../plugin_manager/plugin_loader.py)
- [插件基类](../../../plugin_manager/plugin.py)
- [系统插件](../../../plugins)

## 错误处理

所有 API 端点在发生错误时都会返回适当的 HTTP 状态码和错误信息：

```json
{
  "error": "错误描述信息"
}
```

常见状态码：
- 400: 请求参数错误、插件已存在或内部插件操作限制
- 404: 插件不存在
- 500: 服务器内部错误

## 使用示例

### 获取所有插件
```python
import requests

response = requests.get(
    'http://localhost:8080/api/plugin/plugins',
    headers={'Authorization': f'Bearer {token}'}
)
```

### 安装新插件
```python
import requests

data = {
    "package_name": "image-processing",
    "version": "1.0.0"
}

response = requests.post(
    'http://localhost:8080/api/plugin/plugins',
    headers={'Authorization': f'Bearer {token}'},
    json=data
)
```

### 启用插件
```python
import requests

response = requests.post(
    'http://localhost:8080/api/plugin/plugins/image-processing/enable',
    headers={'Authorization': f'Bearer {token}'}
)
```

### 更新插件
```python
import requests

response = requests.put(
    'http://localhost:8080/api/plugin/plugins/image-processing',
    headers={'Authorization': f'Bearer {token}'}
)
```

## 相关文档

- [系统架构](../../README.md#系统架构-)
- [API 认证](../../README.md#api认证-)
- [插件开发](../../../plugin_manager/README.md#插件开发-) 
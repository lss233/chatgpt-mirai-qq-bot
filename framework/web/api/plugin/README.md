# 插件管理 API

插件管理API提供了对系统插件的全面管理功能，包括查看、安装、卸载、启用和禁用插件。

## API 端点

### 获取插件列表

```http
GET /api/plugin
```

获取所有已安装的插件列表，包括内部插件和外部插件。

**响应示例：**
```json
{
  "plugins": [
    {
      "name": "TelegramAdapter",
      "package_name": "chatgpt-mirai-telegram-adapter",
      "description": "Telegram adapter for ChatGPT-Mirai",
      "version": "1.0.0",
      "author": "Internal",
      "is_internal": true,
      "is_enabled": true,
      "metadata": null
    }
  ]
}
```

### 获取可用插件列表

```http
GET /api/plugin/available
```

获取所有已安装但未启用的插件列表。

### 获取插件详情

```http
GET /api/plugin/{package_name}
```

获取指定插件的详细信息。

### 安装插件

```http
POST /api/plugin/install
```

安装新插件。

**请求体：**
```json
{
  "package_name": "plugin-package-name",
  "version": "1.0.0"  // 可选
}
```

### 卸载插件

```http
POST /api/plugin/uninstall/{package_name}
```

卸载指定的插件。插件必须处于禁用状态才能卸载。

### 更新插件

```http
POST /api/plugin/update/{package_name}
```

将指定的插件更新到最新版本。

### 启用插件

```http
POST /api/plugin/enable/{package_name}
```

启用指定的插件。

### 禁用插件

```http
POST /api/plugin/disable/{package_name}
```

禁用指定的插件。

## 错误处理

所有API端点在发生错误时都会返回适当的HTTP状态码和错误信息：

```json
{
  "error": "错误描述信息"
}
```

常见状态码：
- 400: 请求参数错误或操作无效
- 404: 插件未找到
- 500: 服务器内部错误

## 注意事项

1. 内部插件无法被禁用或卸载
2. 启用的插件无法直接卸载，必须先禁用
3. 插件的启用/禁用状态会被保存到配置文件中
4. 更新插件前建议先禁用插件 
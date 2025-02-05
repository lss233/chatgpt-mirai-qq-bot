# 认证 API 🔐

认证 API 提供了用户认证和密码管理的功能。系统使用基于 JWT 的认证机制。

## API 端点

### 登录

```http
POST /api/auth/login
```

登录系统并获取访问令牌。首次登录时会设置管理员密码。

**请求体：**
```json
{
  "password": "your-password"
}
```

**响应示例：**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### 修改密码

```http
POST /api/auth/change-password
```

修改管理员密码。需要提供当前密码和新密码。

**请求体：**
```json
{
  "old_password": "current-password",
  "new_password": "new-password"
}
```

**响应示例：**
```json
{
  "message": "Password changed successfully"
}
```

## 数据模型

### LoginRequest
- `password`: 密码

### ChangePasswordRequest
- `old_password`: 当前密码
- `new_password`: 新密码

### TokenResponse
- `access_token`: JWT 访问令牌
- `token_type`: 令牌类型(固定为 "bearer")

## 认证机制

系统使用 JWT (JSON Web Token) 进行认证。所有需要认证的 API 端点都需要在请求头中携带访问令牌：

```http
Authorization: Bearer your-jwt-token
```

令牌特性：
- 默认有效期为 30 分钟
- 使用 HS256 算法签名
- 包含过期时间声明 (exp)

## 相关代码

- [认证路由](routes.py)
- [认证工具](utils.py)
- [数据模型](models.py)
- [认证中间件](middleware.py)

## 错误处理

所有 API 端点在发生错误时都会返回适当的 HTTP 状态码和错误信息：

```json
{
  "error": "错误描述信息"
}
```

常见状态码：
- 400: 请求参数错误
- 401: 密码错误或令牌无效
- 500: 服务器内部错误

## 使用示例

### 登录获取令牌
```python
import requests

response = requests.post(
    'http://localhost:8080/api/auth/login',
    json={'password': 'your-password'}
)
token = response.json()['access_token']
```

### 修改密码
```python
import requests

response = requests.post(
    'http://localhost:8080/api/auth/change-password',
    headers={'Authorization': f'Bearer {token}'},
    json={
        'old_password': 'current-password',
        'new_password': 'new-password'
    }
)
```

### 使用令牌访问其他 API
```python
import requests

response = requests.get(
    'http://localhost:8080/api/system/status',
    headers={'Authorization': f'Bearer {token}'}
)
```

## 安全建议

1. 使用强密码
   - 至少 12 位长度
   - 包含大小写字母、数字和特殊字符
   - 避免使用常见词汇和个人信息

2. 定期更换密码
   - 建议每 90 天更换一次
   - 不要重复使用最近使用过的密码

3. 保护令牌安全
   - 不要在客户端明文存储令牌
   - 令牌过期后及时清理
   - 不要在不安全的通道传输令牌

## 相关文档

- [系统概述](../../README.md#系统架构-)
- [API 认证](../../README.md#api认证-)
- [安全指南](../../README.md#安全建议-) 
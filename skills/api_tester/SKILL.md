---
name: API 接口测试
description: HTTP 接口测试技能，支持发送请求、断言响应、加载 JSON 测试套件文件批量执行，内置模板变量替换，适用于开发联调和回归测试。
allowed-tools: [http_request, read_file]
---

# API 接口测试（API Tester）

## 功能概览

| 工具 | 说明 |
|---|---|
| `send_request` | 发送单个 HTTP 请求并返回状态码、响应体、耗时 |
| `assert_response` | 对响应进行断言（状态码、JSON 字段、响应时间）|
| `run_test_suite` | 加载 JSON 测试套件文件，批量执行所有用例 |
| `set_variable` | 设置模板变量，在 URL / Header / Body 中用 `{{var}}` 引用 |

## 使用示例

```
# 发送请求
send_request("POST", "https://api.example.com/auth/login", 
             json={"username": "test", "password": "123456"})

# 断言响应
assert_response(status=200, json_path="$.token", not_empty=True)

# 设置变量（后续请求可用 {{token}} 引用）
set_variable("token", response.json["token"])

# 带认证头的请求
send_request("GET", "https://api.example.com/users/me",
             headers={"Authorization": "Bearer {{token}}"})

# 批量执行测试套件
run_test_suite("tests/api_suite.json")
```

## 测试套件格式（JSON）

```json
{
  "name": "用户模块回归测试",
  "base_url": "https://api.example.com",
  "variables": {
    "admin_token": "Bearer xxx"
  },
  "cases": [
    {
      "id": "TC-001",
      "name": "登录成功",
      "method": "POST",
      "path": "/auth/login",
      "body": {"username": "admin", "password": "admin123"},
      "asserts": [
        {"type": "status", "expect": 200},
        {"type": "json_path", "path": "$.token", "not_empty": true}
      ]
    },
    {
      "id": "TC-002", 
      "name": "获取用户信息",
      "method": "GET",
      "path": "/users/me",
      "headers": {"Authorization": "{{admin_token}}"},
      "asserts": [
        {"type": "status", "expect": 200},
        {"type": "json_path", "path": "$.id", "not_empty": true},
        {"type": "response_time_ms", "max": 500}
      ]
    }
  ]
}
```

## 输出格式

```
[TEST SUITE] 用户模块回归测试 (2 cases)
  ✅ TC-001  登录成功          200  143ms
  ✅ TC-002  获取用户信息       200  89ms

结果: 2/2 通过  总耗时: 232ms
```

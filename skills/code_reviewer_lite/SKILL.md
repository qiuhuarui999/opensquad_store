---
name: 代码审查助手
description: 轻量代码审查技能，自动检测常见代码坏味道、圈复杂度估算和 TODO/FIXME 追踪，支持 Python 和 TypeScript，无需外部服务。
allowed-tools: [read_file, list_directory]
---

# 代码审查助手（Code Reviewer Lite）

## 功能概览

| 工具 | 说明 |
|---|---|
| `review_file` | 审查单个文件，检测坏味道、复杂度、安全问题 |
| `review_directory` | 批量审查目录下所有支持的文件 |
| `find_todos` | 提取文件或目录中所有 TODO / FIXME / HACK 注释 |
| `estimate_complexity` | 估算函数级圈复杂度（Python / TypeScript）|

## 使用示例

```
# 审查单个文件
review_file("src/auth/login.py")

# 批量审查目录
review_directory("src/", extensions=[".py", ".ts"])

# 找出所有待办项
find_todos("src/")

# 复杂度报告
estimate_complexity("src/core/processor.py")
```

## 检测规则

### Python
- 函数超过 50 行：建议拆分
- 嵌套超过 4 层：建议重构
- 裸 `except:`：必须指定异常类型
- 可变默认参数（`def f(x=[])`）：已知陷阱
- 硬编码密码/密钥字符串：安全警告

### TypeScript
- `any` 类型滥用：建议具体类型
- 未处理的 Promise（无 `await` / `.catch`）
- `console.log` 遗留：建议移除或改用 logger
- 魔法数字：建议提取为命名常量

## 输出格式

```
[REVIEW] src/auth/login.py
  🔴 L45  裸 except 语句，请指定异常类型
  🟡 L89  函数 process_login 共 67 行，建议拆分（阈值 50）
  🟢 L12  TODO: 添加限流逻辑 (by dev-a, 2024-01-15)
  ℹ️  复杂度估算: process_login CC=8（中等，建议 < 10）

总计: 1 个错误，1 个警告，1 个 TODO
```

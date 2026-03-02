---
name: Git 工作流助手
description: 只读 Git 工具集，提供工作区状态查询、差异分析、提交历史浏览、分支管理信息，帮助 agent 在执行任务前充分理解代码库状态。
allowed-tools: [run_command]
---

# Git 工作流助手（Git Helper）

> **只读技能**：所有工具仅读取 Git 信息，不执行任何写操作（不 commit、不 push、不 checkout）。

## 功能概览

| 工具 | 说明 |
|---|---|
| `git_status` | 查看工作区和暂存区状态 |
| `git_diff` | 查看文件差异（工作区 / 暂存区 / 提交间）|
| `git_log` | 浏览提交历史，支持过滤和格式化 |
| `git_branches` | 列出所有本地/远程分支，显示最后提交信息 |
| `git_blame` | 查看文件每行的最后修改记录（作者/时间/提交）|
| `git_show` | 查看指定提交的详细内容 |

## 使用示例

```
# 工作区状态
git_status()

# 查看未暂存的差异
git_diff()

# 查看暂存区差异
git_diff(staged=True)

# 查看两个提交之间的差异
git_diff(from_ref="HEAD~3", to_ref="HEAD")

# 查看最近 10 条提交历史
git_log(limit=10)

# 按作者过滤
git_log(author="dev-a", limit=20)

# 查看某文件的修改历史
git_log(file="src/auth/login.py", limit=10)

# 列出所有分支
git_branches(include_remote=True)

# 查看文件某行的修改来源
git_blame("src/auth/login.py", lines=(40, 60))

# 查看某个提交的内容
git_show("a3f9b2c")
```

## 典型工作流

在开始任务前，建议按以下顺序使用：

1. `git_status()` — 确认工作区是否干净
2. `git_branches()` — 了解当前分支和最新状态
3. `git_log(limit=5)` — 了解最近的变更上下文
4. `git_diff(from_ref="main", to_ref="HEAD")` — 了解当前分支与主干的差异

## 输出示例

```
[GIT STATUS]
分支: feat/user-auth (领先 main 3 个提交)
暂存区:
  M  src/auth/login.py
  A  tests/test_login.py
工作区:
  M  src/auth/middleware.py
未跟踪:
  src/auth/ratelimit.py

[GIT LOG] 最近 3 条
  a3f9b2c  feat: 添加登录限流      dev-a  2 小时前
  7d21e4f  fix: JWT 过期时间修正   dev-b  5 小时前
  c09a812  test: 补充登录单测      dev-a  昨天
```

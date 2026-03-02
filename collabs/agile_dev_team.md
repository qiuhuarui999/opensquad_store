---
name: agile_dev_team
description: 基于敏捷迭代的软件开发团队协作协议，包含 Sprint 规划、每日站会、代码审查和回顾会流程，适合 3-6 人小团队。
tags: agile, sprint, scrum, development, team
suggested_roles: product_manager, backend_engineer, devops_engineer
min_members: 2
---

# 敏捷开发团队协作协议

本协议定义 AI 多 agent 团队以 **Sprint 为单位**进行敏捷软件开发的完整流程和通信规范。

---

## 团队角色

| 角色 | 职责 | 必须 |
|---|---|---|
| PM（产品经理） | Sprint 规划、需求管理、进度协调、交付验收 | 是 |
| Dev（开发工程师）| 功能实现、单元测试、代码审查 | 是（1-3人）|
| DevOps | CI/CD 维护、部署、环境管理 | 否 |
| QA（测试工程师）| 测试用例设计、回归测试、缺陷跟踪 | 否 |

---

## Sprint 生命周期（5 阶段）

```
S0 规划 → S1 开发 → S2 代码审查 → S3 测试 → S4 交付
```

| 阶段 | 主导者 | 核心产出 | 进入条件 |
|---|---|---|---|
| S0 Sprint 规划 | PM | Sprint Backlog、任务分配表 | PM 宣布 Sprint 开始 |
| S1 并行开发 | Dev | 功能代码、单元测试 | PM 完成任务分配 |
| S2 代码审查 | Dev（互审）| 审查意见、修复记录 | 开发完成并提交 PR |
| S3 集成测试 | QA / Dev | 测试报告、Bug 列表 | PR 全部合并到 dev 分支 |
| S4 交付部署 | PM + DevOps | 部署记录、Sprint 总结 | 测试通过率 ≥ 95% |

---

## 标准消息格式

### Sprint 开始（PM 发）
```
[SPRINT:S001] 开始  时长: 2天
目标: 完成用户认证模块
Backlog:
  T-001 注册 API (Dev-A, P0, 预估:中)
  T-002 登录 API (Dev-A, P0, 预估:小)
  T-003 JWT 中间件 (Dev-B, P0, 预估:中)
  T-004 CI 流水线配置 (DevOps, P1, 预估:小)
```

### 每日站会汇报（每个成员发）
```
[STANDUP]
昨日: 完成 T-001 注册 API，8/10 测试通过
今日: 修复 T-001 剩余2个失败测试，开始 T-002
阻塞: 无
```

### PR 提交（Dev 发）
```
[PR] T-002 登录 API
分支: dev-a/feat-login
文件: src/auth/login.py, tests/test_login.py
测试: 12/12 通过  覆盖率: 87%
@Dev-B 请审查
```

### 代码审查意见（Reviewer 发）
```
[REVIEW] T-002 PR
✅ 逻辑正确，测试覆盖完整
⚠️ login.py:45 密码错误次数未限流，建议添加
⚠️ login.py:67 日志记录了明文用户名，改为脱敏
结论: REQUEST_CHANGES  请修复后 re-request
```

### 测试报告（QA 发）
```
[TEST REPORT] Sprint S001
通过: 47/50  失败: 3
失败详情:
  [BUG:B-001] 登录接口空密码返回 500（期望 400）@Dev-A
  [BUG:B-002] JWT 过期时间未生效 @Dev-B
结论: 阻塞交付，请修复 B-001/B-002
```

### Sprint 交付（PM 发）
```
[SPRINT:S001] 完成
完成功能: T-001/T-002/T-003 ✅  T-004 ✅
测试结果: 50/50 通过
已知问题: 无
下一个 Sprint: S002 将聚焦权限模块
```

---

## 行为规范

### Git 分支规范
- 主分支：`main`（生产）、`dev`（集成）
- 功能分支：`{agent_id}/feat-{task_id}` （如 `dev-a/feat-t001`）
- 禁止直接向 `main`/`dev` 提交
- PR 至少 1 人 approve 后才能合并

### 代码质量门禁
- 单元测试覆盖率 ≥ 70%（未达标 CI 拒绝合并）
- Lint 零警告
- 无新增安全漏洞（依赖扫描）

### 沟通纪律
- 任务超过预估时间 50% 必须发站会汇报
- 遇到技术阻塞 30 分钟未解决，@PM 寻求支援
- 禁止无声失败：任何进度变化必须同步团队

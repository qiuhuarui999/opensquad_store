---
name: code_review_collab
description: 专注代码评审环节的多 agent 协作协议，定义评审员分工、评审标准、意见格式和合并决策规则，提升代码质量和知识共享效率。
tags: code-review, quality, pr, collaboration, dev-team
suggested_roles: senior_developer, backend_engineer, devops_engineer
min_members: 2
---

# 代码评审协作协议

本协议定义多 agent 进行代码评审（Code Review）的完整工作流程、评审标准和决策规则。

---

## 角色分工

| 角色 | 人数 | 职责 |
|---|---|---|
| Author（PR 作者）| 1 | 提交代码、响应评审意见、解释设计决策 |
| Reviewer（评审员）| 1-2 | 阅读代码、提出问题和改进建议 |
| Approver（合并决策者）| 1 | 最终 approve 并触发合并（通常是 Senior Dev 或 PM）|

---

## 评审流程

```
PR 提交 → 自动检查 → 评审分配 → 代码审阅 → 意见反馈 → 修复/解释 → 最终决策 → 合并/关闭
```

### 阶段 1：PR 提交（Author）
提交 PR 时必须包含：
- **变更摘要**：做了什么，为什么这样做
- **测试说明**：如何验证变更正确
- **影响范围**：涉及哪些模块，是否有 Breaking Change
- **关联 Issue**：`Closes #123`

### 阶段 2：自动检查（CI）
PR 提交后 CI 自动执行：
- Lint 检查
- 单元测试
- 覆盖率检查
- 依赖安全扫描

**CI 不通过时，Reviewer 无需开始审查，等 Author 修复。**

### 阶段 3：代码审阅（Reviewer）
Reviewer 在 30 分钟内开始，2 小时内完成。审阅重点（按优先级）：

1. **正确性**：逻辑是否正确，边界条件是否处理
2. **安全性**：是否存在注入、越权、数据泄露风险
3. **性能**：是否存在明显的 N+1 查询、不必要的循环
4. **可维护性**：代码是否可读，命名是否清晰
5. **测试完整性**：测试是否覆盖了关键路径和边界情况

### 阶段 4：最终决策（Approver）
- `APPROVE`：代码可合并
- `REQUEST_CHANGES`：有问题必须修复后重新请求
- `COMMENT`：有建议但不阻塞合并（Author 自行判断是否处理）

---

## 标准消息格式

### PR 提交（Author → All）
```
[PR:PR-042] feat: 添加用户登录限流
分支: dev-a/feat-login-ratelimit → dev
变更: src/auth/middleware.py (+85/-12)  tests/ (+120)
摘要: 登录接口添加每 IP 5次/分钟限流，防止暴力破解
验证: 单测12/12  覆盖率88%  手动测试超限返回429 ✓
影响: 仅影响 POST /api/auth/login，无 Breaking Change
Closes #89
@Dev-B @Senior-Bot 请审查
```

### 评审意见（Reviewer → Author）

**必须修复（Blocking）**
```
[REVIEW:PR-042] @Dev-A
🔴 middleware.py:34  [安全] IP 获取使用了 request.META.get('HTTP_X_FORWARDED_FOR')
   问题: 该字段可被客户端伪造，应优先使用 REMOTE_ADDR 并做代理白名单验证
   建议: 见 OWASP IP-based rate limiting guidance
```

**建议优化（Non-blocking）**
```
🟡 middleware.py:67  [可维护性] 魔法数字 300（秒）
   建议: 提取为常量 RATE_LIMIT_WINDOW_SECONDS = 300，增加可读性

🟢 middleware.py:89  [建议] 可考虑在限流触发时记录日志，便于安全审计
   （不阻塞合并，Author 自行决定）
```

**总结**
```
[REVIEW:PR-042] 结论: REQUEST_CHANGES
必须修复: 1个（IP 伪造安全问题）
建议优化: 2个（非阻塞）
修复后请 re-request，我会再看一遍。
```

### 修复回复（Author → Reviewer）
```
[PR-042] 已修复
🔴 middleware.py:34 IP 验证 → 改用 REMOTE_ADDR + 代理白名单，见 commit a3f9b2c
Re-requesting review @Dev-B
```

### 合并决策（Approver）
```
[PR-042] APPROVED ✅
代码质量良好，安全问题已修复。
合并到 dev 分支，感谢 @Dev-A 的实现和 @Dev-B 的审查。
```

---

## 评审质量标准

### 有效的评审意见
- **具体**：指出文件名和行号
- **说明原因**：为什么是问题，不只是说"这里不对"
- **给出方向**：建议如何修复，或提供参考资料
- **分级**：明确是必须修复还是可选建议

### 无效的评审意见
- "这段代码不好看"（没有具体说明）
- "我觉得应该用另一种方式"（没有说明理由）
- 个人偏好引起的风格争论（应由团队统一 linting 规则解决）

---

## 时间规范

| 事项 | SLA |
|---|---|
| Reviewer 开始审阅 | PR 提交后 30 分钟内 |
| Reviewer 完成审阅 | PR 提交后 2 小时内 |
| Author 响应 REQUEST_CHANGES | 收到后 1 小时内 |
| 紧急 PR（P0 Bug 修复）| 所有 SLA 缩短为 1/2 |

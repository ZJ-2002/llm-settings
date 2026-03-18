# Agent Teams 快速启动指南

> 5分钟上手 Agent Teams，包含常见场景的完整示例。

---

## 一、5分钟快速启动

### 最小可行示例

```bash
# 1. 创建团队
TeamCreate(
  team_name="hello-world",
  description="Hello World 示例"
)

# 2. 创建任务
TaskCreate(
  subject="实现 Hello World API",
  description="创建 GET /hello 接口，返回 {message: 'Hello World'}",
  activeForm="正在实现 Hello World API"
)

# 3. 生成开发者成员
Task(
  prompt="你是开发者，负责实现分配的编码任务。完成任务后必须通知 team-lead。",
  subagent_type="general-purpose",
  name="developer",
  team_name="hello-world",
  run_in_background=true
)

# 4. 分配任务并通知
TaskUpdate(taskId="1", owner="developer")
SendMessage(
  type="message",
  recipient="developer",
  content="任务#1 已分配给你，请查看详情并开始工作",
  summary="分配任务#1"
)

# 5. 等待完成通知（不要轮询！）
# ... 成员完成后会自动发送消息给你 ...

# 6. 收到完成通知后关闭团队
SendMessage(
  type="shutdown_request",
  recipient="developer",
  content="感谢完成，现在可以关闭",
  summary="关闭请求"
)
TeamDelete()
```

### 核心要点

1. **创建顺序**：Team → Tasks → Members → Assign → Notify
2. **不要轮询**：等待成员主动通知你
3. **必须通知**：分配任务后要发送消息唤醒成员
4. **记得关闭**：完成后发送 shutdown_request 并 TeamDelete

---

## 二、常见场景完整示例

### 场景1：简单功能开发（2人团队）

**需求**：实现一个工具函数并添加测试

```bash
# 1. 创建团队
TeamCreate(
  team_name="utils-feature",
  description="实现工具函数"
)

# 2. 创建任务
TaskCreate(
  subject="实现 formatDate 函数",
  description="在 src/utils/date.ts 中实现 formatDate(date: Date, format: string): string",
  activeForm="正在实现 formatDate 函数"
)

TaskCreate(
  subject="添加单元测试",
  description="为 formatDate 添加测试用例到 tests/utils/date.test.ts",
  activeForm="正在添加单元测试"
)

# 3. 设置依赖：测试依赖开发完成
TaskUpdate(taskId="2", addBlockedBy=["1"])

# 4. 生成成员
Task(
  prompt="你是开发者，负责实现编码任务。完成后必须通知 team-lead。",
  subagent_type="general-purpose",
  name="developer",
  team_name="utils-feature",
  run_in_background=true
)

Task(
  prompt="你是测试员，负责编写测试。完成后必须通知 team-lead。",
  subagent_type="general-purpose",
  name="tester",
  team_name="utils-feature",
  run_in_background=true
)

# 5. 分配第一个任务
TaskUpdate(taskId="1", owner="developer")
SendMessage(
  type="message",
  recipient="developer",
  content="任务#1 已分配，请实现 formatDate 函数",
  summary="开始开发"
)

# 6. 等待 developer 完成通知...

# 7. developer 完成后，分配测试任务给 tester
TaskUpdate(taskId="2", owner="tester")
SendMessage(
  type="message",
  recipient="tester",
  content="任务#2 已分配，开发已完成，请添加测试",
  summary="开始测试"
)

# 8. 等待 tester 完成通知...

# 9. 全部完成后关闭
SendMessage(type="shutdown_request", recipient="developer", content="完成", summary="关闭")
SendMessage(type="shutdown_request", recipient="tester", content="完成", summary="关闭")
TeamDelete()
```

---

### 场景2：并行开发（3人团队）

**需求**：同时开发前端和后端功能

```bash
# 1. 创建团队
TeamCreate(
  team_name="parallel-dev",
  description="前后端并行开发"
)

# 2. 创建并行任务
TaskCreate(
  subject="实现前端组件",
  description="创建 src/components/UserProfile.tsx，显示用户信息",
  activeForm="正在实现前端组件"
)

TaskCreate(
  subject="实现后端 API",
  description="创建 GET /api/user/:id 接口，返回用户数据",
  activeForm="正在实现后端 API"
)

TaskCreate(
  subject="集成测试",
  description="测试前后端集成是否正常",
  activeForm="正在进行集成测试"
)

# 3. 设置依赖：集成测试依赖前后端
TaskUpdate(taskId="3", addBlockedBy=["1", "2"])

# 4. 生成成员
Task(prompt="前端开发者...", name="frontend", team_name="parallel-dev", subagent_type="general-purpose", run_in_background=true)
Task(prompt="后端开发者...", name="backend", team_name="parallel-dev", subagent_type="general-purpose", run_in_background=true)
Task(prompt="测试员...", name="tester", team_name="parallel-dev", subagent_type="general-purpose", run_in_background=true)

# 5. 并行分配任务
TaskUpdate(taskId="1", owner="frontend")
TaskUpdate(taskId="2", owner="backend")

SendMessage(type="message", recipient="frontend", content="开始任务#1", summary="启动")
SendMessage(type="message", recipient="backend", content="开始任务#2", summary="启动")

# 6. 等待两个完成通知...

# 7. 前后端都完成后，分配集成测试
TaskUpdate(taskId="3", owner="tester")
SendMessage(type="message", recipient="tester", content="前后端已完成，开始集成测试", summary="启动测试")

# 8. 等待测试完成...

# 9. 关闭所有成员
SendMessage(type="shutdown_request", recipient="frontend", content="完成", summary="关闭")
SendMessage(type="shutdown_request", recipient="backend", content="完成", summary="关闭")
SendMessage(type="shutdown_request", recipient="tester", content="完成", summary="关闭")
TeamDelete()
```

---

### 场景3：研究先行（Researcher + Developer）

**需求**：先调研技术方案，再实现

```bash
# 1. 创建团队
TeamCreate(
  team_name="research-first",
  description="研究后开发"
)

# 2. 创建任务
TaskCreate(
  subject="调研认证方案",
  description="研究适合项目的认证方案（JWT/Session/OAuth），给出推荐",
  activeForm="正在调研认证方案"
)

TaskCreate(
  subject="实现认证功能",
  description="根据调研结果实现用户认证",
  activeForm="正在实现认证功能"
)

# 3. 设置依赖
TaskUpdate(taskId="2", addBlockedBy=["1"])

# 4. 生成成员
Task(
  prompt="你是研究员，只负责调研和分析，不写代码。完成后必须通知 team-lead。",
  subagent_type="Explore",
  name="researcher",
  team_name="research-first",
  run_in_background=true
)

Task(
  prompt="你是开发者，负责实现功能。完成后必须通知 team-lead。",
  subagent_type="general-purpose",
  name="developer",
  team_name="research-first",
  run_in_background=true
)

# 5. 开始研究
TaskUpdate(taskId="1", owner="researcher")
SendMessage(type="message", recipient="researcher", content="开始调研认证方案", summary="启动研究")

# 6. 等待研究报告...

# 7. 收到研究报告后，创建新的开发任务描述（基于研究结果）
TaskUpdate(taskId="2", description="基于研究结果：推荐使用 JWT。实现步骤：1. 安装 jsonwebtoken 2. 创建 auth middleware 3. 添加登录接口")
TaskUpdate(taskId="2", owner="developer")
SendMessage(type="message", recipient="developer", content="研究已完成，开始实现认证功能", summary="启动开发")

# 8. 等待开发完成...

# 9. 关闭
SendMessage(type="shutdown_request", recipient="researcher", content="完成", summary="关闭")
SendMessage(type="shutdown_request", recipient="developer", content="完成", summary="关闭")
TeamDelete()
```

---

## 三、常见错误和解决方案

### 错误1：成员一直空闲

**症状**：创建了成员但没有收到任何消息

**原因**：分配任务后没有发送通知消息

**解决**：
```bash
# 错误：只分配任务
TaskUpdate(taskId="1", owner="developer")

# 正确：分配后必须通知
TaskUpdate(taskId="1", owner="developer")
SendMessage(type="message", recipient="developer", content="任务已分配", summary="通知")
```

---

### 错误2：任务被阻塞无法开始

**症状**：成员报告任务状态是 blocked

**原因**：依赖的前置任务未完成

**解决**：
```bash
# 检查依赖
TaskGet(taskId="3")
# 看到 blockedBy: ["1", "2"]

# 确保前置任务完成
TaskUpdate(taskId="1", status="completed")
TaskUpdate(taskId="2", status="completed")

# 然后成员才能认领任务3
```

---

### 错误3：Leader 轮询导致成本飙升

**症状**：成本异常高

**原因**：Leader 反复调用 TaskList 检查状态

**解决**：
```bash
# 错误：轮询
while not done:
  TaskList()  # 不要这样做！

# 正确：等待消息
# 成员完成后会自动发送消息给你
# 你只需要响应收到的消息
```

---

### 错误4：成员完成后没有通知

**症状**：任务显示 completed 但 Leader 不知道

**原因**：成员忘记发送完成消息

**解决**：在成员的 prompt 中明确要求
```bash
Task(
  prompt="你是开发者。重要：完成任务后必须立即发送 SendMessage 通知 team-lead，包含修改的文件和变更摘要。",
  ...
)
```

---

### 错误5：使用 broadcast 通知单个人

**症状**：成本是预期的 N 倍

**原因**：broadcast 会发给所有成员

**解决**：
```bash
# 错误
SendMessage(type="broadcast", content="...", summary="...")  # 发给所有人

# 正确
SendMessage(type="message", recipient="developer", content="...", summary="...")  # 只发给一个人
```

---

### 错误6：忘记关闭团队

**症状**：会话结束后成员仍在运行

**原因**：没有发送 shutdown_request

**解决**：
```bash
# 必须的关闭流程
SendMessage(type="shutdown_request", recipient="developer", content="完成", summary="关闭")
SendMessage(type="shutdown_request", recipient="tester", content="完成", summary="关闭")
# 等待 shutdown_response...
TeamDelete()
```

---

## 四、下一步学习路径

### 入门后建议阅读

1. **protocol.md** - 深入理解通信协议
2. **workflow.md** - 学习更复杂的工作流模式
3. **role.md** - 了解不同角色的职责分工

### 进阶主题

- **并行开发优化** - 如何最大化并行效率
- **成本控制** - 如何估算和控制成本
- **错误恢复** - 任务失败后如何处理

### 调试技巧

- 使用 `TaskList()` 查看所有任务状态
- 使用 `TaskGet(taskId)` 查看任务详情
- 查看 `references/troubleshooting.md` 获取更多帮助

---

## 五、快速参考卡

### Leader 必做清单

- [ ] TeamCreate 创建团队
- [ ] TaskCreate 创建所有任务
- [ ] TaskUpdate 设置依赖
- [ ] Task 生成成员
- [ ] TaskUpdate 分配任务
- [ ] SendMessage 通知成员
- [ ] 等待消息（不轮询）
- [ ] SendMessage shutdown_request
- [ ] TeamDelete 清理

### 消息类型速查

| 类型 | 用途 | 频率 |
|------|------|------|
| `message` | 私聊通知 | 90% |
| `shutdown_request` | 关闭成员 | 结束时 |
| `shutdown_response` | 响应关闭 | 自动 |
| `broadcast` | 全员通知 | 极少用 |

### subagent_type 速查

| 类型 | 能力 | 适用角色 |
|------|------|----------|
| `general-purpose` | 读写执行 | 开发者、测试员 |
| `Explore` | 只读 | 研究员、审查员 |
| `Plan` | 只读 | 架构师 |
| `Bash` | 仅执行 | 运维 |

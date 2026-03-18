# Agent Teams 反模式案例库

> 本文档收集了使用 Agent Teams 时的常见错误做法，帮助你避免踩坑。

---

## 目录

- [一、反模式总览](#一反模式总览)
- [二、团队组织反模式](#二团队组织反模式)
- [三、任务管理反模式](#三任务管理反模式)
- [四、通信协议反模式](#四通信协议反模式)
- [五、角色使用反模式](#五角色使用反模式)
- [六、工具调用反模式](#六工具调用反模式)
- [七、性能优化反模式](#七性能优化反模式)

---

## 一、反模式总览

| 类别 | 反模式数量 | 影响程度 |
|------|-----------|----------|
| 团队组织 | 5 | 高 |
| 任务管理 | 6 | 高 |
| 通信协议 | 8 | 中 |
| 角色使用 | 4 | 中 |
| 工具调用 | 1 | 高 |
| 性能优化 | 5 | 低 |

---

## 二、团队组织反模式

### ❌ 反模式 #1：过早优化 Team 规模

**错误做法**：
```bash
# 任务还没分析清楚，就生成 5 个成员
TeamCreate(team_name="project-x")
Task(...) # developer
Task(...) # tester
Task(...) # reviewer
Task(...) # architect
Task(...) # researcher
# 大部分成员会空闲等待
```

**问题**：
- 资源浪费（空闲成员消耗 API 调用）
- 成本增加（每个成员都有基础开销）
- 管理复杂度上升

**正确做法**：
```bash
# 先分析任务，再按需生成
TeamCreate(team_name="project-x")
TaskCreate(subject="分析需求", ...) → Task#1

# 先只生成 researcher
Task(prompt="...", name="researcher", ...)
TaskUpdate(taskId="1", owner="researcher")

# 等待研究结果后，再决定需要哪些角色
```

**经验法则**：
- 从最小可行团队开始（2 人）
- 根据任务复杂度逐步增加
- 避免提前生成会空闲的成员

---

### ❌ 反模式 #2：忽略成员空闲状态

**错误认知**：
```
成员 idle = 出问题了 ❌
```

**正确认知**：
```
成员 idle = 正常等待，发送消息即可唤醒 ✅
```

**错误做法**：
```bash
# 看到 idle 就慌了，开始轮询
while True:
    TaskList()  # 每隔一会儿检查
    sleep(5)
```

**正确做法**：
```bash
# 直接发送消息，成员会被唤醒
SendMessage(type="message", recipient="developer", content="新任务已分配")
# 等待响应
```

**关键点**：
- idle 是正常状态，不是错误
- 发送消息会自动唤醒成员
- 不要轮询，等待消息即可

---

### ❌ 反模式 #3：过度依赖 broadcast

**问题**：90% 的情况应该用 message，但新手容易滥用 broadcast。

**错误做法**：
```bash
# 只需要通知一个人却用广播
SendMessage(type="broadcast", content="developer，你的任务完成了吗？")
```

**成本对比**：
```
message: 1 次调用
broadcast: 1 × N 次调用（N = 成员数）
```

**决策规则**：
```
真的需要通知所有人吗？
  ├─ 是 → 真的是所有人吗？
  │   ├─ 是（紧急/重大） → broadcast ✅
  │   └─ 否 → message（发给相关的人） ✅
  └─ 否 → message ✅
```

**何时使用 broadcast**：
- ✅ 紧急阻塞（影响所有人的严重问题）
- ✅ 重大方向变更（需求大幅调整）
- ✅ 全员收尾通知（项目完成）

**何时 NOT 使用 broadcast**：
- ❌ 回复某个成员的消息
- ❌ 分配任务（只相关一个人）
- ❌ 日常进度询问

---

## 三、任务管理反模式

### ❌ 反模式 #4：任务粒度过大

**错误做法**：
```json
{
  "subject": "实现完整的用户认证模块",
  "description": "实现注册、登录、密码重置、邮箱验证、权限管理..."
}
```

**问题**：
- 单个会话难以完成
- 失败后难以定位问题
- 无法并行处理

**正确做法**：
```json
// 拆分为多个小任务
[
  {
    "subject": "实现用户注册 API",
    "description": "POST /api/register，接收 email+password，bcrypt 加密，返回 JWT"
  },
  {
    "subject": "实现用户登录 API",
    "description": "POST /api/login，验证凭证，返回 JWT"
  },
  {
    "subject": "实现密码重置 API",
    "description": "POST /api/reset-password，发送重置邮件..."
  }
]
```

**任务粒度原则**：
- ✅ 单次会话可完成（< 30 分钟）
- ✅ 验收标准明确
- ✅ 可以独立测试

---

### ❌ 反模式 #5：忽略依赖关系

**错误做法**：
```bash
# 同时分配开发和测试任务
TaskUpdate(taskId="1", owner="developer")  # 开发
TaskUpdate(taskId="2", owner="tester")      # 测试（但开发还没完成！）
```

**问题**：
- tester 会立即失败
- 浪费资源和时间
- 需要重新测试

**正确做法**：
```bash
# 设置依赖关系
TaskUpdate(taskId="2", addBlockedBy=["1"])

# 测试任务会被自动阻塞
# 只有开发完成后，tester 才能开始
```

**依赖设置原则**：
- ✅ 明确前置任务
- ✅ 使用 addBlockedBy 自动阻塞
- ✅ Leader 在前置任务完成后再通知

---

### ❌ 反模式 #6：循环依赖

**错误做法**：
```
Task#1 依赖 Task#2
Task#2 依赖 Task#3
Task#3 依赖 Task#1  ❌ 循环！
```

**问题**：
- 所有任务都无法开始
- 系统会检测并报错
- 需要重新设计任务

**正确做法**：
```
# 重新设计，打破循环
Task#1 (无依赖)
Task#2 依赖 Task#1
Task#3 依赖 Task#2
```

**检测方法**：
```bash
# 使用诊断工具
python3 ~/.claude/mcp-servers/agent-teams-mcp/diagnose.py diagnose <team_name>
```

---

## 四、通信协议反模式

### ❌ 反模式 #7：Leader 轮询成员状态

**错误做法**：
```bash
# Leader 不停地检查任务状态
while True:
    TaskList()
    sleep(5)
    TaskList()
    sleep(5)
```

**问题**：
- 浪费 API 调用
- 增加成本
- 消息会自动送达，不需要轮询

**正确做法**：
```bash
# 分配任务后等待消息
SendMessage(type="message", recipient="developer", content="开始任务#1")

# 不要轮询，等待 developer 的完成通知
# 消息会自动送达
```

**关键认知**：
- ✅ 消息会自动送达
- ✅ 成员完成后会发送消息
- ❌ 不需要主动检查状态

---

### ❌ 反模式 #8：成员沉默完成

**错误做法**：
```bash
# Developer 完成任务后不通知 Leader
TaskUpdate(taskId="1", status="completed")
# 沉默等待...
```

**问题**：
- Leader 不知道任务已完成
- 后续任务无法分配
- 项目停滞

**正确做法**：
```bash
# 完成后立即通知 Leader
TaskUpdate(taskId="1", status="completed")
SendMessage(
    type="message",
    recipient="team-lead",
    content="任务#1已完成。修改文件：\n- src/api/auth.ts\n- src/models/user.ts",
    summary="任务#1完成"
)
```

**必须通知的场景**：
- ✅ 任务完成
- ✅ 遇到问题
- ✅ 需要澄清需求
- ✅ 发现依赖未满足

---

### ❌ 反模式 #9：消息缺少关键信息

**错误做法**：
```bash
SendMessage(content="任务完成了", summary="完成")  # ❌ 缺少详细信息
```

**问题**：
- Leader 不知道具体完成了什么
- 难以评估质量
- 后续任务无法准确分配

**正确做法**：
```bash
SendMessage(
    content="""
任务#1 '实现用户注册API' 已完成。

修改的文件：
- src/api/auth.ts:30-55 (新增 register 函数)
- src/models/user.ts:10-25 (新增 createUser 方法)
- src/routes/auth.ts:15 (新增 POST /register 路由)

测试结果：
- 单元测试：5/5 通过
- 覆盖率：87%

注意事项：
- 需要配置 JWT_SECRET 环境变量
- bcrypt 已添加到 package.json
""",
    summary="任务#1完成-修改3个文件"
)
```

**必须包含的信息**：
- ✅ 任务 ID 和标题
- ✅ 修改的文件列表（含行号）
- ✅ 测试结果（如适用）
- ✅ 需要注意的事项

---

## 五、角色使用反模式

### ❌ 反模式 #10：Leader 亲自写代码

**错误做法**：
```bash
# Leader 等不及了，自己开始写代码
Edit(file_path="src/app.ts", ...)
```

**问题**：
- 违反职责分离
- Leader 应该编排，不是实现
- 打乱协作流程

**正确做法**：
```bash
# Leader 发消息催促或重新分配
SendMessage(
    type="message",
    recipient="developer",
    content="任务#1进展如何？如有阻塞请告知。",
    summary="询问任务进度"
)
```

**Leader 的职责**：
- ✅ 创建任务、设置依赖
- ✅ 分配工作、响应消息
- ✅ 解决阻塞、协调资源
- ❌ 亲自实现代码

---

### ❌ 反模式 #11：错误的角色类型

**错误做法**：
```bash
# 需要写代码却用 Explore 类型
Task(prompt="...", subagent_type="Explore", name="developer")  # ❌
```

**问题**：
- Explore 类型没有写权限
- 任务会失败
- 需要重新生成成员

**正确做法**：
```bash
# 根据任务需求选择正确的类型
Task(prompt="...", subagent_type="general-purpose", name="developer")  # ✅
```

**角色类型选择**：
| 任务类型 | subagent_type | 原因 |
|----------|---------------|------|
| 开发、测试 | `general-purpose` | 需要读写执行 |
| 代码审查 | `Explore` | 只读即可 |
| 架构设计 | `Plan` | 只读即可 |
| 运维操作 | `Bash` | 仅命令执行 |

---

## 六、工具调用反模式

### ❌ 反模式 #14：陷入自我修正循环

**错误症状**：
```
● 我需要使用正确的工具调用格式，尝试使用正确的工具调用语法。
● 我需要使用正确的工具调用格式，尝试使用正确的参数格式。
● 我需要使用正确的工具调用格式，尝试使用正确的工具名称。
● 我需要使用正确的工具调用格式，尝试使用正确的任务 ID。
```

或：

```
● 我需要使用正确的语法。
  <parameter=
● 我需要使用正确的语法。
  <parameter=
```

**问题**：
- 模型在工具调用失败后不断输出自我反思文本
- 持续消耗 token 但不解决问题
- 阻止任务进展
- 可能导致资源耗尽

**正确做法**：
```
如果工具调用连续失败 2 次：
1. 停止自我修正
2. SendMessage 通知 Leader
3. 在消息中包含：
   - 失败的工具和参数
   - 错误消息
   - 已尝试的修复方式
   - 建议的解决方案

示例：
SendMessage(
  type="message",
  recipient="team-lead",
  content="工具调用失败: TaskUpdate\n\n使用的参数: {\"taskId\": \"1\", \"status\": \"completed\"}\n错误: Invalid task ID\n\n已尝试: \n1. 检查 TaskList 确认任务存在\n2. 使用正确的 taskId 格式\n\n需要协助检查任务状态。",
  summary="工具调用失败-TaskUpdate"
)
```

**预防措施**：
- 在 Prompt 中明确设置"最多尝试 2 次自我修正"
- 超过限制立即向 Leader 报告
- 不要输出"我需要使用正确的..."这类自我反思文本
- 不要输出未完成的工具调用（如 "<parameter="）

**检测方法**：
```bash
# 查看最近的输出
tail -20 ~/.claude/teams/{team-name}/.state/session-log.md

# 统计重复模式
tail -100 ~/.claude/teams/{team-name}/.state/session-log.md | grep -c "我需要使用正确的"
```

**解决步骤**：
1. 立即终止陷入循环的成员（使用 TaskStop）
2. 分析失败原因（任务描述、参数要求、编码问题）
3. 重新生成成员并改进 Prompt（添加更清晰的工具调用示例）
4. 从检查点恢复或重新分配任务

---

## 七、性能优化反模式

### ❌ 反模式 #12：频繁的状态更新

**错误做法**：
```bash
# 每完成一个小步骤就更新状态
TaskUpdate(taskId="1", status="in_progress")
# 写了一行代码
TaskUpdate(taskId="1", description="完成50%")
# 又写了一行
TaskUpdate(taskId="1", description="完成60%")
# ...
```

**问题**：
- 大量 API 调用
- 增加成本
- 没有实际价值

**正确做法**：
```bash
# 只在关键节点更新状态
TaskUpdate(taskId="1", status="in_progress")  # 开始
# ... 完成所有工作 ...
TaskUpdate(taskId="1", status="completed")    # 完成
SendMessage(...)  # 通知 Leader
```

**更新频率原则**：
- ✅ 开始时：pending → in_progress
- ✅ 完成时：in_progress → completed
- ❌ 中间过程：避免频繁更新

---

### ❌ 反模式 #13：消息过于频繁

**错误做法**：
```bash
# 每个小问题都发消息
SendMessage(content="文件 A 写完了")
SendMessage(content="文件 B 写完了")
SendMessage(content="文件 C 写完了")
SendMessage(content="文件 D 写完了")
# 4 次调用 = 4 × 通信开销
```

**问题**：
- 通信开销大
- Leader 收到大量消息
- 难以管理

**正确做法**：
```bash
# 批量发送
SendMessage(content="完成了 4 个文件：\n- 文件 A\n- 文件 B\n- 文件 C\n- 文件 D")
# 1 次调用 = 1 × 通信开销
```

**优化原则**：
- ✅ 合并相关消息
- ✅ 批量报告进展
- ❌ 频繁发送小消息

---

## 七、总结

### 反模式检查清单

使用前检查：
- [ ] 团队规模是否最小化？
- [ ] 任务粒度是否合适？
- [ ] 依赖关系是否正确？
- [ ] 角色类型是否匹配？
- [ ] 通信类型是否合适？

使用中检查：
- [ ] 是否在轮询成员状态？
- [ ] 成员完成是否通知了 Leader？
- [ ] 消息是否包含足够信息？
- [ ] Leader 是否在亲自写代码？

完成后检查：
- [ ] 是否有空闲成员未关闭？
- [ ] 是否有未清理的资源？
- [ ] 是否总结了经验教训？

### 性能优化建议

| 反模式 | 优化方案 | 预期节省 |
|--------|----------|----------|
| 过大团队 | 从 2 人开始 | 30-50% |
| 频繁轮询 | 等待消息 | 20-40% |
| 滥用 broadcast | 用 message | 25% × N |
| 频繁更新 | 批量更新 | 15-25% |
| 小消息频繁 | 合并消息 | 20% |
| 自我修正循环 | 添加循环防护 | 避免 token 耗尽 |

---

## 八、相关资源

- [troubleshooting.md](./troubleshooting.md) - 故障排查指南
- [protocol.md](./protocol.md) - 通信协议详解
- [workflow.md](./workflow.md) - 标准工作流
- [performance.md](./performance.md) - 性能优化

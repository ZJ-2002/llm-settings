# 协作协议：通信规则与流程控制

> 本文档定义了 Agent Teams 中成员之间的通信协议。所有成员必须严格遵守这些规则，以确保协作有序进行。

---

## 快速查找：我该用什么通信方式？

| 你的身份 | 你要做什么 | 使用工具 | 示例章节 |
|----------|-----------|----------|----------|
| Leader | 分配任务 | `SendMessage(type="message")` | 见 2.1 |
| Leader | 紧急通知全员 | `SendMessage(type="broadcast")` | 见 3.1 |
| Leader | 关闭成员 | `SendMessage(type="shutdown_request")` | 见 9.1 |
| 成员 | 报告完成 | `SendMessage(type="message", recipient="team-lead")` + `create_artifact_tool` | 见 2.1, 12 |
| 成员 | 报告问题 | `SendMessage(type="message", recipient="team-lead")` | 见 2.1 |
| 成员 | 响应关闭 | `SendMessage(type="shutdown_response")` | 见 9.2 |
| 成员 | 确认收到任务 | `db_add_task_ack_tool` | 见 13 |

---

## 一、通信方式选择决策树

```
需要通信
  │
  ├─ 你是谁？
  │   ├─ Leader：
  │   │   ├─ 需要通知所有人？ → ⚠️ 再想想，真的需要通知所有人吗？
  │   │   │   ├─ 是（紧急阻塞/方向变更） → broadcast
  │   │   │   └─ 不是 → message（发给相关的人）
  │   │   ├─ 分配任务？ → message（发给负责人）
  │   │   ├─ 回复某人？ → message（发给那个人）
  │   │   └─ 请求关闭？ → shutdown_request
  │   │
  │   └─ Teammate：
  │       ├─ 汇报任务结果？ → message（发给 team-lead）+ artifact（详细报告）
  │       ├─ 遇到问题求助？ → message（发给 team-lead）
  │       ├─ 响应关闭请求？ → shutdown_response
  │       └─ 需要和其他成员沟通？ → message（发给那个人，同时抄送 team-lead）
```

---

## 二、什么时候使用私聊（message）

### 适用场景（覆盖 90% 的情况）

| 场景 | 发送者 | 接收者 | 示例 |
|------|--------|--------|------|
| 分配任务 | Leader | 具体成员 | "请开始任务#1" |
| 任务完成通知 | 成员 | Leader | "任务#1已完成，详见 artifact" |
| 报告问题 | 成员 | Leader | "遇到依赖缺失问题" |
| 回复成员消息 | Leader | 那个成员 | "收到，已创建修复任务" |
| 审查反馈 | Reviewer | Leader | "代码审查完成，详见 artifact" |
| 测试结果 | Tester | Leader | "5个测试通过，1个失败" |
| 请求澄清 | 成员 | Leader | "任务描述中的X不太清楚" |

### 私聊消息模板

**Leader → Developer（分配任务）**：
```json
{
  "type": "message",
  "recipient": "developer",
  "content": "任务 #1 '实现用户注册API' 已分配给你。请用 TaskGet(taskId='1') 查看详细需求。完成后通知我。",
  "summary": "分配任务#1给developer"
}
```

**Developer → Leader（任务完成）**：
```json
{
  "type": "message",
  "recipient": "team-lead",
  "content": "任务 #1 '实现用户注册API' 已完成。\n修改的文件：\n- src/api/auth.ts (新增 register 函数)\n- src/models/user.ts (新增 createUser 方法)\n- src/routes/auth.ts (新增 POST /register 路由)\n请查看并分配下一个任务。",
  "summary": "任务#1开发完成"
}
```

**Tester → Leader（测试失败）**：
```json
{
  "type": "message",
  "recipient": "team-lead",
  "content": "任务 #3 测试结果：\n- 通过：4个\n- 失败：1个\n失败详情：test_register_duplicate_email - 期望返回 409 但实际返回 500\n错误位置：src/api/auth.ts:45\n建议：注册接口缺少重复邮箱的错误处理。\n任务保持 in_progress 状态，等待 bug 修复后重新测试。",
  "summary": "测试失败-发现1个bug"
}
```

**Reviewer → Leader（使用 Artifact）**：
```json
{
  "type": "message",
  "recipient": "team-lead",
  "content": "任务 #5 代码审查完成。详细报告已生成：.teams/artifacts/review_report/task_5_review.md\n\n关键问题：1个阻塞问题（密码未加密）\n建议：参考报告中的修复建议。",
  "summary": "审查完成-有1个阻塞问题"
}
```

---

## 三、什么时候使用广播（broadcast）

### 仅在以下情况使用

1. **紧急阻塞**：发现影响所有人的严重问题
2. **重大方向变更**：需求大幅调整
3. **全员收尾通知**：项目完成

**绝不使用广播的场景**：
- ❌ 回复某个成员的消息
- ❌ 分配任务（只相关一个人）
- ❌ 日常进度询问
- ❌ 只影响部分成员的信息

---

## 四、什么时候带文件链接

### 规则：涉及具体代码变更时，必须包含文件路径

**必须包含文件路径的场景**：
| 场景 | 格式要求 |
|------|----------|
| 开发完成通知 | 列出所有修改的文件路径 |
| 测试失败报告 | 包含错误发生的文件路径:行号 |
| 审查反馈 | 每个问题标注文件路径:行号 |
| Bug 报告 | 包含 bug 所在的文件路径:行号 |
| 研究结果 | 使用 artifact，在消息中发送 artifact 路径 |

---

## 五、消息时机协议

### 5.1 成员必须发送消息的时机

| 事件 | 发给谁 | 内容要求 | MCP 工具 |
|------|--------|----------|----------|
| 收到任务 | team-lead | "已收到任务#X，理解需求" | `db_add_task_ack_tool` |
| 任务开始 | team-lead | "已开始任务#X" | `db_add_task_ack_tool` |
| 任务完成 | team-lead | 结果摘要 + 修改的文件列表 | `SendMessage` |
| Explore 产出报告 | team-lead | 摘要 + artifact 路径 | `create_artifact_tool` + `SendMessage` |
| 遇到问题 | team-lead | 问题描述 + 影响范围 | `SendMessage` |
| 发现依赖未满足 | team-lead | 哪个前置任务未完成 | `SendMessage` |
| 需要澄清需求 | team-lead | 具体不明确的点 | `SendMessage` |
| 发现安全问题 | team-lead | [严重] 标注 + 详情 | `SendMessage` |

### 5.2 不需要发送消息的情况

- ❌ Leader 不需要确认收到成员的消息（处理完直接行动即可）
- ❌ 成员不需要在空闲时主动报告空闲状态（系统自动发送 idle 通知）
- ❌ 不需要发送 "收到" "好的" 等无信息量的确认消息（使用 ACK 机制）

---

## 六、等待协议

### 6.1 Leader 的等待规则

```
重要：消息会自动送达，不需要轮询！

Leader 在以下时刻应该等待（不做任何操作）：
- 成员正在执行任务时 → 等待完成通知
- 发送 shutdown_request 后 → 等待 shutdown_response

Leader 在收到消息后应该立即响应：
- 成员报告完成 → 检查 TaskList，分配下一个任务
- 成员报告问题 → 创建修复任务或提供指导
- 成员请求澄清 → 给出明确答复
```

---

## 七、Idle 状态处理协议

### 重要概念：成员空闲（idle）是正常的

```
关于 idle 状态的关键认识：
1. 成员每次 turn 结束后都会自动进入 idle 状态——这是正常的
2. idle 并不意味着成员完成了所有工作或不可用
3. 向 idle 成员发送消息会唤醒他们
4. 不要把 idle 当做错误或问题
```

---

## 八、错误处理与升级协议

### 8.1 成员遇到错误时

**优先级 1：自行解决**
- 编译错误、语法错误 → 自行修复
- 缺少依赖 → 自行安装

**优先级 2：通知 Leader**
- 需求不明确 → SendMessage 请求澄清
- 依赖未满足 → SendMessage 报告阻塞
- 外部服务不可用 → SendMessage 报告问题

**优先级 3：升级**
- 发现安全漏洞 → SendMessage 标注 [严重]
- 架构设计缺陷 → SendMessage 建议重新评估

### 8.2 自适应重试策略

**使用 MCP 工具获取重试建议**：
```python
record_error_tool(
    team_name="my-team",
    error_content="npm install 失败：权限不足",
    context="任务#3 - 安装依赖"
)
```

| 错误类型 | 重试次数 | 处理方式 |
|---------|---------|---------|
| 工具格式错误 | 2 次 | 立即求助 |
| 参数格式错误 | 2 次 | 提供示例后重试 |
| Bash 执行错误 | 4 次 | 尝试替代命令 |
| 业务逻辑错误 | 5 次 | 深度分析后重试 |

---

## 九、Shutdown（关闭）协议

### 正确的关闭流程

```
Step 1: 确认所有任务完成
  TaskList() → 检查是否所有任务都是 completed

Step 2: 逐个发送关闭请求
  SendMessage(type="shutdown_request", recipient="developer", content="所有任务完成")

Step 3: 等待关闭响应
  每个成员应该回复 shutdown_response(approve=true)

Step 4: 确认所有成员关闭后
  TeamDelete()

Step 5: 向用户报告结果
```

---

## 十、反模式（绝对不要这样做）

### ❌ 反模式 1：Leader 轮询
### ❌ 反模式 2：成员沉默完成
### ❌ 反模式 3：Leader 直接干活
### ❌ 反模式 4：无视依赖直接开始
### ❌ 反模式 5：滥用广播
### ❌ 反模式 6：不带文件信息的完成通知

---

## 十一、工具调用错误处理协议

### 11.1 错误分类

| 错误类型 | 症状 | 处理方式 |
|----------|--------|---------|
| 参数缺失 | 工具提示缺少必填参数 | 检查并补全参数 |
| 参数类型错误 | 工具提示类型不匹配 | 转换为正确类型 |
| taskId 无效 | 提示任务不存在 | 使用 TaskList 获取正确 ID |
| recipient 无效 | 提示成员不存在 | 检查 team config 中的成员列表 |

### 11.2 自适应重试

**原则**：使用 `record_error_tool` 获取重试建议，而非固定 2 次

```
尝试调用工具
  ├─ 成功 → 继续
  ├─ 失败 → 调用 record_error_tool 获取建议
  │         ├─ can_retry=true → 按建议重试
  │         └─ can_retry=false → 向 Leader 报告
  └─ 超过建议重试次数 → 停止！向 Leader SendMessage 报告
```

---

## 十二、成果交付物（Artifacts）协议

> Explore 类型角色必须使用 Artifacts 产出详细报告，保持 Leader 上下文整洁

### 12.1 何时使用 Artifacts

| 场景 | 创建者 | Artifact 类型 |
|------|--------|--------------|
| 代码架构调研 | Researcher | `research_note` |
| 代码审查报告 | Reviewer | `review_report` |
| 性能分析结果 | Researcher | `analysis_result` |
| 技术方案设计 | Researcher | `design_doc` |
| 调试日志 | 任何角色 | `log_file` |
| 临时数据 | 任何角色 | `temp_data` |

### 12.2 Artifacts 使用流程

```python
# Step 1: Explore 角色创建详细成果
create_artifact_tool(
    team_name="my-team",
    creator="researcher-1",
    creator_role="researcher",
    artifact_type="research_note",
    title="API 设计方案调研",
    content="# 调研结果...",  # 详细内容
    visibility="leader_only",  # 减少 Leader 上下文负担
    summary="REST vs GraphQL 对比分析，推荐 REST",
    tags='["api", "design"]'
)

# Step 2: 发送精简消息通知 Leader
SendMessage(
    type="message",
    recipient="team-lead",
    content="调研任务#1完成。报告已生成：artifacts/my-team/research_note/api_design.md",
    summary="调研完成-API设计方案"
)
```

### 12.3 可见性级别

| 级别 | 说明 | 适用场景 |
|------|------|----------|
| `public` | 所有成员可读 | 设计文档、接口规范 |
| `team` | 团队成员可读 | 测试报告、会议记录 |
| `leader_only` | 仅 Leader（推荐） | 详细调研笔记、审查报告 |
| `private` | 仅创建者 | 个人草稿（不推荐） |

### 12.4 Leader 读取 Artifacts

```python
# 获取成果列表
list_artifacts_tool(team_name="my-team", limit=10)

# 获取特定成果详情
get_artifact_tool(artifact_id="abc123")

# 获取成果目录路径
get_artifacts_dir_tool(team_name="my-team")
```

---

## 十三、ACK 确认机制

> 轻量级任务接收确认，减少 Leader 的"消息是否送达"焦虑

### 13.1 ACK 类型

| 类型 | 含义 | 使用时机 |
|------|------|----------|
| `received` | 已收到任务通知 | 收到任务分配通知后 |
| `understood` | 理解任务需求 | 阅读任务详情后 |
| `started` | 已开始执行任务 | 准备开始工作时 |

### 13.2 ACK 使用示例

```python
# 成员收到任务分配后，立即发送 ACK
db_add_task_ack_tool(
    task_id="task-1",
    member_name="developer-1",
    ack_type="understood",
    message="理解任务：实现用户登录功能，预计需要2小时"
)
```

### 13.3 Leader 查看 ACK

```python
# 获取任务的所有确认
task = db_get_task("task-1")
acks = task.get("acks", [])

for ack in acks:
    print(f"{ack['member_name']}: {ack['ack_type']} - {ack['message']}")
```

### 13.4 ACK vs SendMessage

| 对比 | ACK | SendMessage |
|------|-----|-------------|
| 用途 | 轻量级确认 | 详细报告和问题 |
| 内容长度 | 简短（< 100 字） | 可较长 |
| 频率 | 每个任务 1-3 次 | 按需 |
| 存储位置 | SQLite | 会话日志 |

---

## 十四、内存感知协议

### 关键概念

**Memory Guardian**：一个独立的 Rust 守护进程，持续监控系统内存状态并维护"许可池"

### Leader 必须使用的 MCP 工具

| 工具名 | 用途 | 调用时机 |
|--------|------|----------|
| `get_permit_status_tool()` | 读取许可池状态 | 创建成员前、遇到性能问题时 |
| `reserve_permit_tool()` | 预留资源 | 创建高内存消耗成员前 |

### 内存阈值与许可数对应表

| 内存使用率 | 最大许可数 | 行动建议 | 状态 emoji |
|-----------|-----------|----------|----------|
| >90% | 0（禁止创建） | emergency_serial | 🚨 |
| 80-90% | 2 | reduce_parallelism | ⚠️ |
| 70-80% | 3 | cautions | ⏳ |
| ≤70% | 4 | normal | ✅ |

---

## 十五、完整示例工作流

### 场景：带内存感知和 Artifacts 的团队开发

```
Step 1: Leader 启动
  - Memory Guardian 自动启动
  - Leader 检查系统状态（get_permit_status_tool）

Step 2: Team 创建
  - db_create_team_tool(team_name="feature-x", ...)
  - 保存初始检查点（save_team_checkpoint_tool）

Step 3: 任务规划
  - db_create_task_tool(...) 创建多个任务
  - db_add_dependency_tool(...) 设置依赖关系
  - db_create_trigger_tool(...) 设置自动流转

Step 4: 成员创建（带内存检查）
  - get_permit_status_tool() → available_permits = 2
  - reserve_permit_tool(task_type="development") 预留资源
  - Task(...) 创建 Developer

Step 5: 任务执行
  - Developer 完成开发任务
  - 触发器自动通知 tester
  - Tester 使用 create_artifact_tool 创建测试报告
  - Tester 发送精简消息通知 Leader

Step 6: 团队完成
  - 所有任务完成
  - save_team_checkpoint_tool(...) 保存最终状态
  - 发送 shutdown_request 给所有成员
  - TeamDelete() 清理团队
```

---

## 快速参考

| 我需要... | 相关章节 | MCP 工具 |
|---------|---------|----------|
| 创建成员前检查内存 | 十四 | get_permit_status_tool |
| 查看团队状态 | 一、十 | diagnose_team_status_tool |
| 查看性能指标 | - | get_team_performance_tool |
| 保存进度检查点 | - | save_team_checkpoint_tool |
| 启动/停止守护进程 | - | start_guardian_tool / stop_guardian_tool |
| 查看守护进程状态 | - | get_guardian_status_tool |
| 创建详细报告 | 十二 | create_artifact_tool |
| 发送任务确认 | 十三 | db_add_task_ack_tool |
| 设置自动流转 | - | db_create_trigger_tool |
| 获取可执行任务 | - | db_get_ready_tasks_tool |
